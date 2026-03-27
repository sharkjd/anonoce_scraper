import asyncio
import csv
import json
import os
import re
from pathlib import Path
from typing import Literal

import google.generativeai as genai
from langsmith import traceable
from pydantic import BaseModel, Field, ValidationError

AgencyStatus = Literal["agency", "direct_employer", "uncertain"]
BlueCollarLabel = Literal["Blue collars", "Vyřazeno"]


KNOWN_AGENCIES = {
    "manpower",
    "grafton",
    "randstad",
    "adecco",
    "hays",
    "axial",
    "michael page",
    "reed",
    "job leader",
    "trenkwalder",
    "people partner",
    "hofmann",
    "proplusco",
    "right indicada",
    "future recruitment",
}


class ListingItem(BaseModel):
    source_site: Literal["anonce"] = "anonce"
    title: str = ""
    company: str = ""
    detail_url: str
    ad_date: str = ""


class JobDetail(BaseModel):
    source_site: Literal["anonce"] = "anonce"
    listing_url: str
    detail_url: str
    ad_date: str = ""
    city: str = ""
    company: str = ""
    position: str = ""
    short_description: str = ""
    keywords: list[str] = Field(default_factory=list)
    email: str = ""
    phone: str = ""
    agency_status: AgencyStatus = "uncertain"
    blue_collar_label: BlueCollarLabel = "Vyřazeno"


class AgencyDecision(BaseModel):
    status: AgencyStatus
    reason: str = ""


_BLUE_COLLAR_ALLOWED: dict[str, BlueCollarLabel] = {
    "blue collars": "Blue collars",
    "vyřazeno": "Vyřazeno",
}


def normalize_company_name(company_name: str) -> str:
    normalized = re.sub(r"\s+", " ", company_name or "").strip().lower()
    normalized = normalized.replace("a.s.", "as").replace("s.r.o.", "sro")
    return normalized


def is_known_agency(company_name: str) -> bool:
    normalized = normalize_company_name(company_name)
    return any(agency in normalized for agency in KNOWN_AGENCIES)


def _extract_json_from_response(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


def _normalize_blue_collar_response(raw_text: str) -> BlueCollarLabel | None:
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:text|markdown)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    cleaned = cleaned.strip().strip('"').strip("'")
    normalized = re.sub(r"\s+", " ", cleaned).strip().lower()
    return _BLUE_COLLAR_ALLOWED.get(normalized)


def _build_blue_collar_prompt(position: str, short_description: str, keywords: list[str], company: str) -> str:
    # Strict prompt so the model returns only one of two exact labels.
    return f"""
You are a strict job classifier.

Decide if the role is blue-collar (manual/trade/manufacturing/operations), for example:
bricklayer, locksmith, driver, CNC operator, factory worker, warehouse/manual labor.

Return exactly one value and nothing else:
Blue collars
Vyřazeno

Rules:
- Return "Blue collars" only when the role is clearly blue-collar.
- Return "Vyřazeno" for office/admin/management/IT/sales/HR/finance/legal/marketing and all unclear cases.
- Do not output markdown, punctuation, JSON, explanation, or extra text.

Input:
Position: {position or "N/A"}
Company: {company or "N/A"}
Description: {short_description or "N/A"}
Keywords: {", ".join(keywords or []) or "N/A"}
""".strip()


def _gemini_blue_collar_sync(
    *,
    position: str,
    short_description: str,
    keywords: list[str],
    company: str,
    gemini_model: str = "gemini-2.5-flash",
) -> tuple[BlueCollarLabel, str | None]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Vyřazeno", "Missing GEMINI_API_KEY, blue-collar classification defaulted to Vyřazeno."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(gemini_model)
    prompt = _build_blue_collar_prompt(position, short_description, keywords, company)

    try:
        response = model.generate_content(prompt)
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        return "Vyřazeno", f"Blue-collar Gemini error: {exc}"

    label = _normalize_blue_collar_response(getattr(response, "text", ""))
    if label is None:
        raw_preview = (getattr(response, "text", "") or "").strip().replace("\n", " ")
        raw_preview = raw_preview[:120] if raw_preview else "<empty>"
        return "Vyřazeno", (
            "Blue-collar classification returned unexpected value, defaulted to Vyřazeno: "
            f"{raw_preview}"
        )
    return label, None


@traceable(name="classify_blue_collar_job", run_type="chain")
async def classify_blue_collar_job(
    *,
    position: str,
    short_description: str,
    keywords: list[str],
    company: str,
    gemini_model: str = "gemini-2.5-flash",
) -> tuple[BlueCollarLabel, str | None]:
    return await asyncio.to_thread(
        _gemini_blue_collar_sync,
        position=position,
        short_description=short_description,
        keywords=keywords,
        company=company,
        gemini_model=gemini_model,
    )


def _gemini_classify_sync(company_name: str, hint_text: str, gemini_model: str) -> AgencyDecision:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return AgencyDecision(
            status="uncertain",
            reason="Missing GEMINI_API_KEY, classification skipped.",
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(gemini_model)
    prompt = f"""
You are a strict HR data classifier.
Classify if a company is a recruitment agency or a direct employer.

Return only valid JSON:
{{
  "status": "agency | direct_employer | uncertain",
  "reason": "short reason"
}}

Rules:
- Use "agency" only when strongly indicated.
- Use "direct_employer" when the company clearly looks like an end employer.
- Use "uncertain" when evidence is insufficient.

Company name: {company_name}
Context snippet: {hint_text or "N/A"}
""".strip()

    try:
        response = model.generate_content(prompt)
        payload = _extract_json_from_response(getattr(response, "text", ""))
        return AgencyDecision(**payload)
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        return AgencyDecision(status="uncertain", reason=f"Gemini error: {exc}")


@traceable(name="classify_company", run_type="chain")
async def classify_company(company_name: str, hint_text: str, gemini_model: str) -> AgencyDecision:
    if is_known_agency(company_name):
        return AgencyDecision(status="agency", reason="Matched known agency list.")
    return await asyncio.to_thread(_gemini_classify_sync, company_name, hint_text, gemini_model)


def dedupe_listing_items(items: list[ListingItem]) -> list[ListingItem]:
    seen: set[str] = set()
    deduped: list[ListingItem] = []
    for item in items:
        key = item.detail_url.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def parse_and_validate_details(raw_details: list[dict]) -> tuple[list[JobDetail], list[str]]:
    valid: list[JobDetail] = []
    warnings: list[str] = []
    for entry in raw_details:
        try:
            job = JobDetail(**entry)
            valid.append(job)
        except ValidationError as exc:
            warnings.append(f"Validation failed for {entry.get('detail_url', 'unknown')}: {exc}")
    return valid, warnings


def export_details_to_csv(records: list[JobDetail], output_path: str = "annonce_export.csv") -> Path:
    path = Path(output_path)
    fieldnames = [
        "Datum přidání",
        "Pozice",
        "Kategorie",
        "Popis",
        "Město",
        "Klíčová slova",
        "Telefon",
        "Odkaz",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            d = record.model_dump()
            row = {
                "Datum přidání": d.get("ad_date", ""),
                "Pozice": d.get("position", ""),
                "Kategorie": d.get("blue_collar_label", "Vyřazeno"),
                "Popis": d.get("short_description", ""),
                "Město": d.get("city", ""),
                "Klíčová slova": ", ".join(d.get("keywords") or []),
                "Telefon": d.get("phone", ""),
                "Odkaz": d.get("detail_url", ""),
            }
            writer.writerow(row)
    return path
