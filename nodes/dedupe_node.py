from state import ScraperState
from utils import dedupe_listing_items


async def dedupe_listings_node(state: ScraperState) -> ScraperState:
    before = state.get("listing_items", [])
    n_before = len(before)
    print(f"[Scraper] Deduplikace: vstup {n_before} položek …", flush=True)
    state["listing_items"] = dedupe_listing_items(before)
    n_after = len(state["listing_items"])
    print(f"[Scraper] Deduplikace: po sloučení duplicit {n_after} položek.", flush=True)
    return state
