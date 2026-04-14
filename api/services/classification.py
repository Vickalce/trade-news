from collections.abc import Iterable


CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "earnings": {"earnings", "guidance", "eps", "quarter", "revenue"},
    "macro": {"fed", "cpi", "inflation", "jobs", "unemployment", "rates", "treasury"},
    "geopolitical": {"sanction", "tariff", "war", "conflict", "tension", "summit"},
    "commodity": {"oil", "gas", "gold", "copper", "wti", "brent", "commodity"},
}


def classify_category(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "other"


def classify_scope(entity_types: Iterable[str], category: str) -> str:
    types = set(entity_types)
    if "ticker" in types or "company" in types:
        return "security"
    if "sector" in types or category == "commodity":
        return "sector"
    return "macro"
