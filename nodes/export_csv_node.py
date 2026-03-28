import traceback

from run_report import append_line, append_section
from state import ScraperState
from utils import export_details_to_csv


async def export_csv_node(state: ScraperState) -> ScraperState:
    out = state.get("output_csv_path", "annonce_export.csv")
    n = len(state.get("valid_details", []))
    print(f"[Scraper] Export CSV: {n} řádků → {out!r} …", flush=True)
    append_section("Export CSV")
    append_line(f"Cílový soubor: {out}, počet řádků k zápisu: {n}")
    try:
        csv_path = export_details_to_csv(
            records=state.get("valid_details", []),
            output_path=out,
        )
        state["output_csv_path"] = str(csv_path)
        append_line(f"Výsledek: OK — uloženo do {csv_path}")
        print(f"[Scraper] Export uložen: {csv_path}", flush=True)
    except Exception as exc:  # pragma: no cover - I/O dependent
        msg = f"Export CSV selhal: {exc}"
        append_line(f"Výsledek: CHYBA — {msg}")
        append_line(traceback.format_exc())
        state["errors"] = [*state.get("errors", []), msg]
        print(f"[Scraper] {msg}", flush=True)
    return state
