from state import ScraperState
from utils import parse_and_validate_details


async def validate_and_normalize_node(state: ScraperState) -> ScraperState:
    raw = state.get("raw_details", [])
    print(f"[Scraper] Validace a normalizace: {len(raw)} surových záznamů …", flush=True)
    valid_details, validation_warnings = parse_and_validate_details(raw)
    state["valid_details"] = valid_details
    state["warnings"] = [*state.get("warnings", []), *validation_warnings]
    print(
        f"[Scraper] Validace hotová: {len(valid_details)} platných, "
        f"varování z validace: {len(validation_warnings)}.",
        flush=True,
    )
    return state
