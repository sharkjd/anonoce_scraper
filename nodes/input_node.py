import os

from .console_prompts import prompt_max_pages
from state import DEFAULT_ANNONCE_LISTING_URL, ScraperState


async def input_node(state: ScraperState) -> ScraperState:
    if "max_pages" in state:
        max_pages = int(state["max_pages"])
    else:
        env_default = max(1, int(os.getenv("MAX_PAGES", "2")))
        max_pages = prompt_max_pages(env_default)
    concurrency = int(state.get("concurrency", int(os.getenv("CONCURRENCY", "4"))))
    navigation_wait_profiles_value = state.get(
        "navigation_wait_profiles",
        os.getenv("NAVIGATION_WAIT_PROFILES", "networkidle,domcontentloaded,load"),
    )
    if isinstance(navigation_wait_profiles_value, list):
        navigation_wait_profiles = [
            str(chunk).strip().lower() for chunk in navigation_wait_profiles_value if str(chunk).strip()
        ]
    else:
        navigation_wait_profiles = [
            chunk.strip().lower()
            for chunk in str(navigation_wait_profiles_value).split(",")
            if chunk.strip()
        ]
    listing_base = state.get("listing_base_url", os.getenv("LISTING_BASE_URL", DEFAULT_ANNONCE_LISTING_URL))
    default_csv = os.getenv("OUTPUT_CSV_PATH", "annonce_export.csv")
    print(
        f"[Scraper] Vstup: max_pages={max_pages}, concurrency={concurrency}, "
        f"listing_url={listing_base}",
        flush=True,
    )

    return {
        "listing_base_url": listing_base,
        "max_pages": max_pages,
        "concurrency": concurrency,
        "request_delay_sec": float(
            state.get("request_delay_sec", float(os.getenv("REQUEST_DELAY_SEC", "0.8")))
        ),
        "min_page_delay_sec": float(
            state.get("min_page_delay_sec", float(os.getenv("MIN_PAGE_DELAY_SEC", "2.0")))
        ),
        "max_page_delay_sec": float(
            state.get("max_page_delay_sec", float(os.getenv("MAX_PAGE_DELAY_SEC", "5.0")))
        ),
        "min_detail_delay_sec": float(
            state.get("min_detail_delay_sec", float(os.getenv("MIN_DETAIL_DELAY_SEC", "2.0")))
        ),
        "max_detail_delay_sec": float(
            state.get("max_detail_delay_sec", float(os.getenv("MAX_DETAIL_DELAY_SEC", "6.0")))
        ),
        "detail_batch_size": int(
            state.get("detail_batch_size", int(os.getenv("DETAIL_BATCH_SIZE", "2")))
        ),
        "gemini_model": str(state.get("gemini_model", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))),
        "navigation_wait_profiles": navigation_wait_profiles,
        "listing_navigation_retries": int(
            state.get(
                "listing_navigation_retries",
                int(os.getenv("LISTING_NAVIGATION_RETRIES", "1")),
            )
        ),
        "detail_navigation_retries": int(
            state.get(
                "detail_navigation_retries",
                int(os.getenv("DETAIL_NAVIGATION_RETRIES", "1")),
            )
        ),
        "listing_page_timeout_ms": int(
            state.get(
                "listing_page_timeout_ms",
                int(os.getenv("LISTING_PAGE_TIMEOUT_MS", "60000")),
            )
        ),
        "detail_page_timeout_ms": int(
            state.get(
                "detail_page_timeout_ms",
                int(os.getenv("DETAIL_PAGE_TIMEOUT_MS", "70000")),
            )
        ),
        "navigation_timeout_step_ms": int(
            state.get(
                "navigation_timeout_step_ms",
                int(os.getenv("NAVIGATION_TIMEOUT_STEP_MS", "10000")),
            )
        ),
        "max_consecutive_empty_pages": int(
            state.get(
                "max_consecutive_empty_pages",
                int(os.getenv("MAX_CONSECUTIVE_EMPTY_PAGES", "3")),
            )
        ),
        "listing_items": [],
        "company_classification": {},
        "raw_details": [],
        "valid_details": [],
        "errors": list(state.get("errors", [])),
        "warnings": list(state.get("warnings", [])),
        "output_csv_path": state.get("output_csv_path", default_csv),
    }
