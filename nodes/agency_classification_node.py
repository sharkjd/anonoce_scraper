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

    for idx, company_name in enumerate(unique_companies, start=1):
        print(f"[Scraper]   [{idx}/{total}] {company_name!r}", flush=True)
        decision = await classify_company(
            company_name=company_name,
            hint_text="Job ads from annonce.cz (Czech classifieds).",
            gemini_model=state["gemini_model"],
        )
        decisions[company_name] = decision.status
        if decision.status == "uncertain" and decision.reason:
            state["warnings"] = [
                *state.get("warnings", []),
                f"Uncertain agency classification for '{company_name}': {decision.reason}",
            ]

    state["company_classification"] = decisions
    print("[Scraper] Klasifikace firem hotová.", flush=True)
    return state
