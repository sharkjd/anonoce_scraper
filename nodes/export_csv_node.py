from state import ScraperState
from utils import export_details_to_csv


async def export_csv_node(state: ScraperState) -> ScraperState:
    out = state.get("output_csv_path", "annonce_export.csv")
    n = len(state.get("valid_details", []))
    print(f"[Scraper] Export CSV: {n} řádků → {out!r} …", flush=True)
    csv_path = export_details_to_csv(
        records=state.get("valid_details", []),
        output_path=out,
    )
    state["output_csv_path"] = str(csv_path)
    print(f"[Scraper] Export uložen: {csv_path}", flush=True)
    return state
