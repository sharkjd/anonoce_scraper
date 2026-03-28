from run_report import append_line, append_section
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
    append_section("Validace a normalizace (Pydantic JobDetail)")
    append_line(
        f"Surových záznamů: {len(raw)}, platných po validaci: {len(valid_details)}, "
        f"varování z validace: {len(validation_warnings)}"
    )
    for w in validation_warnings:
        append_line(w)
    return state
