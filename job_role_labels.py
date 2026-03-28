import re

# Použití v enumu i jako výchozí hodnota, když výstup LLM nejde namapovat.
JOB_ROLE_OTHER = "Jiné"

JOB_ROLE_LABELS: tuple[str, ...] = (
    "CNC operátor",
    "CNC seřizovač",
    "CNC programátor",
    "Operátor výroby",
    "Montážní dělník",
    "Operátor lisů/strojů",
    "Kontrola kvality",
    "Elektrikář",
    "Elektrotechnik",
    "Svářeč",
    "Skladník/manipulant",
    "Picker",
    "Expedient",
    "Dispečer",
    "Řidič",
    "Mechanik",
    "Zámečník",
    "Údržbář",
    "Nástrojář",
    "Lakýrník",
    "Vedoucí směny",
    "Mistr",
    "Teamleader/parťák",
    "Administrativa",
    "Obchodní zástupce",
    "Nákup",
    "Event specialista",
    "Instalatér a topenář",
    "Elektromechanik",
    "Dělník ve stavebnictví",
    "Pokladač",
    "Obkladač",
    JOB_ROLE_OTHER,
)

_LABEL_BY_NORMALIZED: dict[str, str] = {
    re.sub(r"\s+", " ", label.strip()).lower(): label for label in JOB_ROLE_LABELS
}


def normalize_job_role_label(raw: object) -> str:
    """Map LLM output to the canonical Czech label; empty string if unknown."""
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    if text.startswith("```"):
        text = re.sub(r"^```(?:text|markdown|json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    text = text.strip().strip('"').strip("'")
    text = re.sub(r"\s+", " ", text).strip()
    if text in JOB_ROLE_LABELS:
        return text
    key = text.lower()
    return _LABEL_BY_NORMALIZED.get(key, "")
