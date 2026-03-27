import asyncio

from state import ScraperState
from utils import JobDetail, classify_blue_collar_job


async def blue_collar_classification_node(state: ScraperState) -> ScraperState:
    records: list[JobDetail] = state.get("valid_details", [])
    if not records:
        print("[Scraper] Blue-collar klasifikace: 0 záznamů, přeskakuji.", flush=True)
        return state

    concurrency = max(int(state.get("concurrency", 4)), 1)
    semaphore = asyncio.Semaphore(concurrency)
    print(
        f"[Scraper] Blue-collar klasifikace: {len(records)} záznamů, concurrency={concurrency} …",
        flush=True,
    )

    async def _classify_one(index: int, record: JobDetail) -> tuple[int, str, str | None, str]:
        async with semaphore:
            label, warning = await classify_blue_collar_job(
                position=record.position,
                short_description=record.short_description,
                keywords=record.keywords,
                company=record.company,
                gemini_model="gemini-2.5-flash",
            )
            return index, label, warning, record.detail_url

    tasks = [_classify_one(index, record) for index, record in enumerate(records)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    new_warnings: list[str] = []
    for index, label, warning, detail_url in results:
        records[index].blue_collar_label = label
        if warning:
            new_warnings.append(f"{detail_url}: {warning}")

    if new_warnings:
        state["warnings"] = [*state.get("warnings", []), *new_warnings]
    state["valid_details"] = records
    print(
        f"[Scraper] Blue-collar klasifikace hotová: {len(records)} záznamů, "
        f"nových varování: {len(new_warnings)}.",
        flush=True,
    )
    return state
