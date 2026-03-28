from run_report import append_line, append_section
from state import ScraperState
from utils import classify_company


async def agency_classification_node(state: ScraperState) -> ScraperState:
    unique_companies = sorted(
        {item.company for item in state.get("listing_items", []) if item.company.strip()}
    )
    decisions: dict[str, str] = dict(state.get("company_classification", {}))
    total = len(unique_companies)
    print(
        f"[Scraper] Klasifikace firem (Gemini): {total} unikátních názvů …",
        flush=True,
    )

    append_section("Klasifikace firem (agentura vs. přímý zaměstnavatel)")
    append_line(
        "Serper se v tomto projektu nepoužívá. Zdroj rozhodnutí: "
        "known_agencies (heuristický seznam), gemini (LLM), error (chyba / chybí klíč); "
        "hodnota serper je rezervovaná pro budoucí rozšíření."
    )

    summary: dict[str, int] = {"agency": 0, "direct_employer": 0, "uncertain": 0}
    by_source: dict[str, int] = {}

    for idx, company_name in enumerate(unique_companies, start=1):
        print(f"[Scraper]   [{idx}/{total}] {company_name!r}", flush=True)
        decision = await classify_company(
            company_name=company_name,
            hint_text="Job ads from annonce.cz (Czech classifieds).",
            gemini_model=state["gemini_model"],
        )
        decisions[company_name] = decision.status
        summary[decision.status] = summary.get(decision.status, 0) + 1
        by_source[decision.source] = by_source.get(decision.source, 0) + 1
        reason_one_line = (decision.reason or "").replace("\n", " ").strip()
        append_line(
            f"{company_name}\tstatus={decision.status}\tsource={decision.source}\treason={reason_one_line}"
        )
        if decision.status == "uncertain" and decision.reason:
            state["warnings"] = [
                *state.get("warnings", []),
                f"Uncertain agency classification for '{company_name}': {decision.reason}",
            ]

    state["company_classification"] = decisions
    append_line(f"Souhrn statusů: {summary}")
    append_line(f"Souhrn zdrojů rozhodnutí: {by_source}")
    print("[Scraper] Klasifikace firem hotová.", flush=True)
    return state
