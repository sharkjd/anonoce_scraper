import asyncio

try:
    from dotenv import load_dotenv  # type: ignore[import-untyped]

    load_dotenv()
except ImportError:
    pass

from graph_builder import build_graph
from langsmith_setup import graph_run_config, log_tracing_status
from state import ScraperState


async def run() -> ScraperState:
    log_tracing_status()
    print("[Scraper] Spouštím graf (Annonce.cz) …", flush=True)
    app = build_graph()
    state: ScraperState = {}
    final_state = await app.ainvoke(state, graph_run_config())
    print("[Scraper] Graf dokončen.", flush=True)
    return final_state


if __name__ == "__main__":
    result_state = asyncio.run(run())
    print(f"Listings discovered: {len(result_state.get('listing_items', []))}")
    print(f"Details extracted: {len(result_state.get('valid_details', []))}")
    print(f"CSV output: {result_state.get('output_csv_path')}")
    if result_state.get("warnings"):
        print(f"Warnings: {len(result_state['warnings'])}")
        for warning in result_state["warnings"]:
            print(f" - {warning}")
