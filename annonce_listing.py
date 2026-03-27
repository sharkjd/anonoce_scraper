"""HTML parsing for Annonce.cz category listing (e.g. Hledám práci)."""

import html as html_module
import re
from urllib.parse import urljoin

from utils import ListingItem

# Listing cards use: <h2><a href="/inzerat/....html" class="clickable">Title</a></h2>
_ANNONCE_LISTING_H2_RE = re.compile(
    r'<h2>\s*<a\s+href="(/inzerat/[^"]+\.html)"\s+class="clickable"[^>]*>(.*?)</a>\s*</h2>',
    re.IGNORECASE | re.DOTALL,
)
_ANNONCE_LISTING_LINK_RE = re.compile(
    r'<a[^>]+href="(/inzerat/[^"]+\.html)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
# Datum u karty: <div class="ad-date">27. 3. 2026</div> (hned za nadpisem inzerátu)
_AD_DATE_AFTER_POS_RE = re.compile(
    r'<div\s+class="ad-date"[^>]*>\s*(.*?)\s*</div>',
    re.IGNORECASE | re.DOTALL,
)


def _extract_ad_date_after(html: str, start_pos: int) -> str:
    """Vezme první ``ad-date`` v následujícím úseku karty (max. ~4 kB za odkazem)."""
    limit = min(start_pos + 4096, len(html))
    chunk = html[start_pos:limit]
    m = _AD_DATE_AFTER_POS_RE.search(chunk)
    if not m:
        return ""
    inner = re.sub(r"<[^>]+>", "", m.group(1))
    return html_module.unescape(inner).strip()


def parse_anonce_listing_html(html: str, page_url: str) -> list[ListingItem]:
    """
    Extract listing cards from a category page.

    Matches the server HTML where each ad title link is ``h2 > a.clickable`` with
    ``href`` under ``/inzerat/``.
    """
    if not html or not html.strip():
        return []

    seen_urls: set[str] = set()
    out: list[ListingItem] = []

    match_iter = _ANNONCE_LISTING_H2_RE.finditer(html)
    rows: list[tuple[str, str, int]] = []
    for m in match_iter:
        rows.append((m.group(1), m.group(2), m.end()))
    # Fallback for minor template changes where title is no longer h2 > a.clickable.
    if not rows:
        for m in _ANNONCE_LISTING_LINK_RE.finditer(html):
            rows.append((m.group(1), m.group(2), m.end()))

    for href, title_raw, end_pos in rows:
        absolute = urljoin(page_url, href)
        if absolute in seen_urls:
            continue
        seen_urls.add(absolute)

        title = html_module.unescape(re.sub(r"<[^>]+>", "", title_raw)).strip()
        title = re.sub(r"\s+", " ", title)
        if len(title) < 3:
            continue

        ad_date = _extract_ad_date_after(html, end_pos)

        out.append(
            ListingItem(
                source_site="anonce",
                title=title,
                company="",
                detail_url=absolute,
                ad_date=ad_date,
            )
        )

    return out
