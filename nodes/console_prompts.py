"""Interaktivní dotazy v konzoli pro konfiguraci scraperu."""


def prompt_max_pages(default: int) -> int:
    """
    Zeptá se na počet stránek výpisu (page=1 … page=N na Annonce.cz).

    Prázdný vstup nebo EOF použije ``default``. Neplatné hodnoty zopakuje dotaz.
    """
    hint = f" [Enter = {default}]" if default >= 1 else ""
    prompt = f"Kolik stránek výpisu z Annonce.cz zpracovat?{hint}: "
    while True:
        try:
            raw = input(prompt).strip()
        except EOFError:
            return max(1, default)
        if not raw:
            return max(1, default)
        try:
            n = int(raw)
        except ValueError:
            print("Zadejte celé číslo.", flush=True)
            continue
        if n < 1:
            print("Minimálně 1 stránka.", flush=True)
            continue
        return n
