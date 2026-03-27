import asyncio
import json
import random
from typing import Any, Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen

from crawl4ai import (
    AsyncWebCrawler,
    CacheMode,
    CrawlerRunConfig,
    LLMConfig,
    LLMExtractionStrategy,
)

from annonce_listing import parse_anonce_listing_html
from utils import ListingItem


COOKIE_JS = """
(() => {
  const selectors = [
    'button#onetrust-accept-btn-handler',
    'button[aria-label*="Accept"]',
    'button[aria-label*="Souhlas"]',
    'button:has-text("Přijmout")',
    'button:has-text("Souhlasím")',
    'button:has-text("Accept all")',
    'button:has-text("Rozumím")'
  ];
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) { el.click(); return true; }
  }
  return false;
})();
""".strip()


DEFAULT_WAIT_PROFILES: tuple[str, ...] = ("networkidle", "domcontentloaded", "load")


def _build_listing_url(base_url: str, page_number: int) -> str:
    if "{page}" in base_url:
        return base_url.format(page=page_number)
    if page_number == 1:
        return base_url
    delimiter = "&" if "?" in base_url else "?"
    return f"{base_url}{delimiter}page={page_number}"


def _crawl_result_html(result: Any) -> str:
    for attr in ("html", "cleaned_html", "fit_html"):
        raw = getattr(result, attr, None)
        if isinstance(raw, str) and raw.strip():
            return raw
    return ""


def _safe_run_config(**kwargs: Any) -> CrawlerRunConfig:
    candidate_configs: list[dict[str, Any]] = [
        kwargs,
        {k: v for k, v in kwargs.items() if k != "js_code"},
        {k: v for k, v in kwargs.items() if k not in {"js_code", "wait_until"}},
        {"cache_mode": kwargs.get("cache_mode", CacheMode.BYPASS)},
    ]
    for config_kwargs in candidate_configs:
        try:
            return CrawlerRunConfig(**config_kwargs)
        except TypeError:
            continue
    return CrawlerRunConfig(cache_mode=CacheMode.BYPASS)


def _normalized_wait_profiles(wait_profiles: Sequence[str] | None) -> list[str]:
    if not wait_profiles:
        return list(DEFAULT_WAIT_PROFILES)

    allowed = {"networkidle", "domcontentloaded", "load", "commit"}
    cleaned: list[str] = []
    for mode in wait_profiles:
        value = str(mode).strip().lower()
        if not value or value not in allowed or value in cleaned:
            continue
        cleaned.append(value)
    return cleaned or list(DEFAULT_WAIT_PROFILES)


async def _crawl_with_navigation_fallback(
    crawler: AsyncWebCrawler,
    *,
    url: str,
    wait_profiles: Sequence[str] | None,
    retries_per_profile: int,
    initial_page_timeout_ms: int,
    timeout_step_ms: int,
    config_kwargs: dict[str, Any],
) -> tuple[Any | None, dict[str, Any]]:
    """
    Try multiple wait modes and retries for pages that never reach `networkidle`.
    """
    profiles = _normalized_wait_profiles(wait_profiles)
    attempts: list[dict[str, Any]] = []
    retries = max(retries_per_profile, 0)
    timeout_base = max(initial_page_timeout_ms, 1000)
    timeout_step = max(timeout_step_ms, 0)
    backoff_idx = 0

    for mode_index, wait_until in enumerate(profiles):
        for retry_index in range(retries + 1):
            timeout_ms = timeout_base + (mode_index * timeout_step) + (retry_index * timeout_step)
            attempt_meta = {
                "wait_until": wait_until,
                "retry": retry_index + 1,
                "timeout_ms": timeout_ms,
            }
            config = _safe_run_config(
                **config_kwargs,
                wait_until=wait_until,
                page_timeout=timeout_ms,
            )
            try:
                result = await crawler.arun(url=url, config=config)
                result_success = bool(getattr(result, "success", False)) if result is not None else False
                if result_success:
                    return result, {
                        "ok": True,
                        "attempts": attempts,
                        "chosen_mode": wait_until,
                        "chosen_retry": retry_index + 1,
                        "chosen_timeout_ms": timeout_ms,
                    }

                error_message = str(getattr(result, "error_message", "") or "").strip()
                attempt_meta["error"] = error_message or "crawler returned success=False"
                attempts.append(attempt_meta)
                backoff_idx += 1
                await asyncio.sleep(min(0.35 * backoff_idx, 1.5))
            except Exception as exc:  # pragma: no cover - runtime dependent
                attempt_meta["error"] = str(exc)
                attempts.append(attempt_meta)
                backoff_idx += 1
                await asyncio.sleep(min(0.35 * backoff_idx, 1.5))

    return None, {"ok": False, "attempts": attempts}


async def _fetch_listing_html_http(url: str, timeout_ms: int) -> str:
    """
    HTTP fallback for listing pages when browser navigation is blocked.
    """
    timeout_sec = max(timeout_ms / 1000.0, 10.0)

    def _fetch_sync() -> str:
        request = Request(
            url=url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
            },
        )
        with urlopen(request, timeout=timeout_sec) as response:  # noqa: S310
            payload = response.read()
        return payload.decode("utf-8", errors="replace")

    try:
        return await asyncio.to_thread(_fetch_sync)
    except (URLError, TimeoutError):
        return ""


def _detail_extraction_strategy(gemini_model: str) -> LLMExtractionStrategy:
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider=f"gemini/{gemini_model}",
            api_token="env:GEMINI_API_KEY",
        ),
        extraction_type="schema",
        schema={
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "company": {"type": "string"},
                "position": {"type": "string"},
                "short_description": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
            "required": ["position"],
        },
        instruction=(
            "Extract Czech job detail information. "
            "Fields: city, company, position, short_description, keywords, email, phone. "
            "Use an empty string for missing scalar fields and empty list for keywords."
        ),
    )


def _parse_extracted_json(raw_payload: str) -> Any:
    if not raw_payload:
        return None
    text = raw_payload.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return json.loads(text)


async def discover_anonce_listings(
    base_url: str,
    max_pages: int,
    request_delay_sec: float,
    navigation_wait_profiles: Sequence[str] | None,
    listing_navigation_retries: int,
    listing_page_timeout_ms: int,
    navigation_timeout_step_ms: int,
) -> tuple[list[ListingItem], list[str]]:
    """Fetch Annonce category listing pages and parse HTML (no LLM on listing)."""
    listings: list[ListingItem] = []
    warnings: list[str] = []

    config_kwargs = {
        "cache_mode": CacheMode.BYPASS,
        "js_code": COOKIE_JS,
    }

    async with AsyncWebCrawler() as crawler:
        for page in range(1, max_pages + 1):
            page_url = _build_listing_url(base_url, page)
            try:
                # Listing pages are mostly static HTML, so try direct HTTP first.
                html = await _fetch_listing_html_http(page_url, listing_page_timeout_ms)
                if not html.strip():
                    result, nav_meta = await _crawl_with_navigation_fallback(
                        crawler=crawler,
                        url=page_url,
                        wait_profiles=navigation_wait_profiles,
                        retries_per_profile=listing_navigation_retries,
                        initial_page_timeout_ms=listing_page_timeout_ms,
                        timeout_step_ms=navigation_timeout_step_ms,
                        config_kwargs=config_kwargs,
                    )
                    if result is None:
                        attempts = nav_meta.get("attempts", [])
                        last_attempt = attempts[-1] if attempts else {}
                        raise RuntimeError(
                            "navigation failed"
                            f" after {len(attempts)} attempts"
                            f" (mode={last_attempt.get('wait_until', 'n/a')},"
                            f" retry={last_attempt.get('retry', 'n/a')},"
                            f" timeout_ms={last_attempt.get('timeout_ms', 'n/a')}):"
                            f" {last_attempt.get('error', 'unknown error')}"
                        )
                    if nav_meta.get("chosen_mode") != "networkidle":
                        warnings.append(
                            "anonce: listing crawl switched wait mode on page "
                            f"{page} to {nav_meta.get('chosen_mode')} (retry "
                            f"{nav_meta.get('chosen_retry')}, timeout "
                            f"{nav_meta.get('chosen_timeout_ms')} ms)."
                        )
                    html = _crawl_result_html(result)

                page_items = parse_anonce_listing_html(html, page_url)
                if not page_items and page > 1:
                    warnings.append(f"anonce: no listings on page {page}, stopping pagination.")
                    break
                if not page_items and page == 1:
                    warnings.append(
                        "anonce: page 1 returned no parseable listings (empty HTML or layout change?)."
                    )
                listings.extend(page_items)
            except Exception as exc:  # pragma: no cover - runtime dependent
                warnings.append(f"anonce: listing crawl failed on page {page}: {exc}")
            await asyncio.sleep(max(request_delay_sec, 0.0))

    return listings, warnings


async def extract_job_detail(
    crawler: AsyncWebCrawler,
    listing: ListingItem,
    listing_url: str,
    agency_status: str,
    gemini_model: str,
    request_delay_sec: float,
    semaphore: asyncio.Semaphore,
    navigation_wait_profiles: Sequence[str] | None = None,
    detail_navigation_retries: int = 1,
    detail_page_timeout_ms: int = 70000,
    navigation_timeout_step_ms: int = 10000,
) -> tuple[dict[str, Any] | None, str | None]:
    strategy = _detail_extraction_strategy(gemini_model)
    config_kwargs = {
        "extraction_strategy": strategy,
        "cache_mode": CacheMode.BYPASS,
        "js_code": COOKIE_JS,
    }

    async with semaphore:
        await asyncio.sleep(max(request_delay_sec + random.uniform(0.0, 0.35), 0.0))
        result, nav_meta = await _crawl_with_navigation_fallback(
            crawler=crawler,
            url=listing.detail_url,
            wait_profiles=navigation_wait_profiles,
            retries_per_profile=detail_navigation_retries,
            initial_page_timeout_ms=detail_page_timeout_ms,
            timeout_step_ms=navigation_timeout_step_ms,
            config_kwargs=config_kwargs,
        )
        if result is None:
            attempts = nav_meta.get("attempts", [])
            last_attempt = attempts[-1] if attempts else {}
            return (
                None,
                "Detail crawl failed for "
                f"{listing.detail_url}: mode={last_attempt.get('wait_until', 'n/a')}, "
                f"retry={last_attempt.get('retry', 'n/a')}, "
                f"timeout_ms={last_attempt.get('timeout_ms', 'n/a')}, "
                f"error={last_attempt.get('error', 'unknown error')}",
            )

        payload = _parse_extracted_json(result.extracted_content) or {}
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict):
            payload = {}

        payload["source_site"] = "anonce"
        payload["listing_url"] = listing_url
        payload["detail_url"] = listing.detail_url
        payload["ad_date"] = listing.ad_date or ""
        payload["position"] = payload.get("position") or listing.title
        payload["company"] = payload.get("company") or listing.company
        payload["agency_status"] = agency_status
        payload["keywords"] = payload.get("keywords") or []
        return payload, None


async def deep_crawl_details(
    listings: list[ListingItem],
    listing_url: str,
    company_classification: dict[str, str],
    gemini_model: str,
    concurrency: int,
    request_delay_sec: float,
    navigation_wait_profiles: Sequence[str] | None = None,
    detail_navigation_retries: int = 1,
    detail_page_timeout_ms: int = 70000,
    navigation_timeout_step_ms: int = 10000,
) -> tuple[list[dict[str, Any]], list[str]]:
    semaphore = asyncio.Semaphore(max(concurrency, 1))
    warnings: list[str] = []

    async with AsyncWebCrawler() as crawler:
        tasks = [
            extract_job_detail(
                crawler=crawler,
                listing=listing,
                listing_url=listing_url,
                agency_status=company_classification.get(listing.company, "uncertain"),
                gemini_model=gemini_model,
                request_delay_sec=request_delay_sec,
                semaphore=semaphore,
                navigation_wait_profiles=navigation_wait_profiles,
                detail_navigation_retries=detail_navigation_retries,
                detail_page_timeout_ms=detail_page_timeout_ms,
                navigation_timeout_step_ms=navigation_timeout_step_ms,
            )
            for listing in listings
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    details: list[dict[str, Any]] = []
    for payload, warning in results:
        if payload:
            details.append(payload)
        if warning:
            warnings.append(warning)
    return details, warnings
