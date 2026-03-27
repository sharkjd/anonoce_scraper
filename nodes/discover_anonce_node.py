from extractors import discover_anonce_listings
from state import ScraperState


async def discover_anonce_node(state: ScraperState) -> ScraperState:
    print(
        f"[Scraper] Annonce.cz: stahuji výpisy (max {state['max_pages']} str., "
        f"delay {state['request_delay_sec']} s) …",
        flush=True,
    )
    listings, warnings = await discover_anonce_listings(
        base_url=state["listing_base_url"],
        max_pages=state["max_pages"],
        request_delay_sec=state["request_delay_sec"],
        navigation_wait_profiles=state.get("navigation_wait_profiles"),
        listing_navigation_retries=state.get("listing_navigation_retries", 1),
        listing_page_timeout_ms=state.get("listing_page_timeout_ms", 60000),
        navigation_timeout_step_ms=state.get("navigation_timeout_step_ms", 10000),
    )
    state["listing_items"] = listings
    state["warnings"] = [*state.get("warnings", []), *warnings]
    print(
        f"[Scraper] Annonce.cz: nalezeno {len(listings)} inzerátů, nových varování: {len(warnings)}.",
        flush=True,
    )
    return state
