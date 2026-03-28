import asyncio
import sys
import traceback

try:
    from dotenv import load_dotenv  # type: ignore[import-untyped]

    load_dotenv()
except ImportError:
    pass

from graph_builder import build_graph
from langsmith_setup import graph_run_config, log_tracing_status
from run_report import append_line, append_section, close_writer, init_for_run
from state import ScraperState


def _append_links_summary(state: ScraperState) -> None:
    listings = state.get("listing_items") or []
    classification = state.get("company_classification") or {}
    raw = state.get("raw_details") or []
    valid = state.get("valid_details") or []
    raw_urls = {
        r.get("detail_url") for r in raw if isinstance(r, dict) and r.get("detail_url")
    }
    valid_urls = {
        j.detail_url for j in valid if getattr(j, "detail_url", None)
    }

    append_section("Inzeráty — odkazy a souhrnný stav (po deduplikaci)")
    for item in listings:
        url = item.detail_url
        company = item.company
        cat = classification.get(company, "uncertain")
        if cat == "agency":
            status = "skipped_agency"
        elif url not in raw_urls:
            status = "crawl_failed_or_not_attempted"
        elif url not in valid_urls:
            status = "validation_failed"
        else:
            status = "ok_exported"
        append_line(f"{status}\t{url}\t{company!r}\tclassification={cat}")


def _write_run_epilogue(state: ScraperState | None) -> None:
    if state is None:
        append_section("Souhrn")
        append_line("Stav grafu není k dispozici (běh nedokončen nebo chyba před návratem stavu).")
        return

    append_section("Souhrn po dokončení grafu")
    append_line(f"run_log_path: {state.get('run_log_path', '')}")
    append_line(f"Počet listing_items: {len(state.get('listing_items', []))}")
    append_line(f"Počet raw_details: {len(state.get('raw_details', []))}")
    append_line(f"Počet valid_details: {len(state.get('valid_details', []))}")
    append_line(f"output_csv_path: {state.get('output_csv_path', '')}")

    _append_links_summary(state)

    warnings = state.get("warnings") or []
    append_section(f"Warnings (kompletní výpis, {len(warnings)} položek)")
    if not warnings:
        append_line("(žádná)")
    else:
        for w in warnings:
            append_line(w)

    errors = state.get("errors") or []
    append_section(f"Errors (kompletní výpis, {len(errors)} položek)")
    if not errors:
        append_line("(žádné)")
    else:
        for e in errors:
            append_line(e)


async def run() -> ScraperState:
    log_tracing_status()
    log_path = init_for_run()
    print(f"[Scraper] Run log: {log_path}", flush=True)
    append_line(f"Python: {sys.version}")
    append_line(f"Executable: {sys.executable}")
    append_line()

    print("[Scraper] Spouštím graf (Annonce.cz) …", flush=True)
    app = build_graph()
    initial: ScraperState = {"run_log_path": str(log_path)}
    final_state: ScraperState | None = None
    try:
        final_state = await app.ainvoke(initial, graph_run_config())
        print("[Scraper] Graf dokončen.", flush=True)
    except Exception:
        append_section("Výjimka během ainvoke (graf)")
        append_line(traceback.format_exc())
        raise
    finally:
        try:
            _write_run_epilogue(final_state)
        except Exception:
            append_line("Epilog: zápis do run logu selhal:")
            append_line(traceback.format_exc())
        close_writer()

    assert final_state is not None
    return final_state


if __name__ == "__main__":
    result_state = asyncio.run(run())
    print(f"Listings discovered: {len(result_state.get('listing_items', []))}")
    print(f"Details extracted: {len(result_state.get('valid_details', []))}")
    print(f"CSV output: {result_state.get('output_csv_path')}")
    print(f"Run log: {result_state.get('run_log_path')}")
    if result_state.get("warnings"):
        print(f"Warnings: {len(result_state['warnings'])}")
        for warning in result_state["warnings"]:
            print(f" - {warning}")
