from extractors import deep_crawl_details
from state import ScraperState


async def deep_crawl_details_node(state: ScraperState) -> ScraperState:
    all_listings = state.get("listing_items", [])
    allowed_listings = [
        item
        for item in all_listings
        if state.get("company_classification", {}).get(item.company, "uncertain") != "agency"
    ]
    skipped = len(all_listings) - len(allowed_listings)
    print(
        f"[Scraper] Detailní crawl: {len(allowed_listings)} inzerátů "
        f"(přeskočeno jako agentura: {skipped}), concurrency={state['concurrency']} …",
        flush=True,
    )

    details, warnings = await deep_crawl_details(
        listings=allowed_listings,
        listing_url=state["listing_base_url"],
        company_classification=state.get("company_classification", {}),
        gemini_model=state["gemini_model"],
        concurrency=state["concurrency"],
        request_delay_sec=state["request_delay_sec"],
        navigation_wait_profiles=state.get("navigation_wait_profiles"),
        detail_navigation_retries=state.get("detail_navigation_retries", 1),
        detail_page_timeout_ms=state.get("detail_page_timeout_ms", 70000),
        navigation_timeout_step_ms=state.get("navigation_timeout_step_ms", 10000),
        min_detail_delay_sec=state.get("min_detail_delay_sec", 2.0),
        max_detail_delay_sec=state.get("max_detail_delay_sec", 6.0),
        batch_size=state.get("detail_batch_size", 2),
    )
    state["raw_details"] = details
    state["warnings"] = [*state.get("warnings", []), *warnings]
    print(
        f"[Scraper] Detailní crawl hotový: {len(details)} surových záznamů, "
        f"nových varování: {len(warnings)}.",
        flush=True,
    )
    return state
