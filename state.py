from typing import Any, TypedDict

from utils import ListingItem

DEFAULT_ANNONCE_LISTING_URL = (
    "https://www.annonce.cz/hledam-praci-chci-vydelat$18.html?page={page}"
)


class ScraperState(TypedDict, total=False):
    listing_base_url: str
    max_pages: int
    concurrency: int
    request_delay_sec: float
    min_page_delay_sec: float
    max_page_delay_sec: float
    min_detail_delay_sec: float
    max_detail_delay_sec: float
    detail_batch_size: int
    gemini_model: str
    navigation_wait_profiles: list[str]
    listing_navigation_retries: int
    detail_navigation_retries: int
    listing_page_timeout_ms: int
    detail_page_timeout_ms: int
    navigation_timeout_step_ms: int
    max_consecutive_empty_pages: int
    listing_items: list[ListingItem]
    company_classification: dict[str, str]
    raw_details: list[dict[str, Any]]
    valid_details: list[Any]
    errors: list[str]
    warnings: list[str]
    output_csv_path: str
