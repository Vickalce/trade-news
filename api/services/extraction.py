import re

from api.schemas import ExtractedEntity

TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")

COMPANY_MAP = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "amazon": "AMZN",
    "meta": "META",
    "google": "GOOGL",
}

SECTOR_KEYWORDS = {
    "technology": {"semiconductor", "software", "cloud", "ai", "chip"},
    "energy": {"oil", "gas", "energy", "refinery"},
    "financials": {"bank", "credit", "lender", "treasury"},
    "healthcare": {"drug", "biotech", "fda", "pharma"},
}

COUNTRY_KEYWORDS = {"us", "china", "japan", "europe", "uk", "canada"}
COMMODITY_KEYWORDS = {"oil", "gas", "gold", "silver", "copper", "wheat"}


def extract_entities(headline: str, body: str | None = None) -> list[ExtractedEntity]:
    text = f"{headline} {body or ''}".strip()
    lowered = text.lower()
    entities: list[ExtractedEntity] = []

    for company, ticker in COMPANY_MAP.items():
        if company in lowered:
            entities.append(ExtractedEntity(entity_type="company", entity_value=company.title(), confidence=0.95))
            entities.append(ExtractedEntity(entity_type="ticker", entity_value=ticker, confidence=0.97))

    for token in TICKER_PATTERN.findall(text):
        if token in COMPANY_MAP.values():
            entities.append(ExtractedEntity(entity_type="ticker", entity_value=token, confidence=0.85))

    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            entities.append(ExtractedEntity(entity_type="sector", entity_value=sector, confidence=0.8))

    for country in COUNTRY_KEYWORDS:
        if re.search(rf"\b{re.escape(country)}\b", lowered):
            entities.append(ExtractedEntity(entity_type="country", entity_value=country.upper(), confidence=0.75))

    for commodity in COMMODITY_KEYWORDS:
        if re.search(rf"\b{re.escape(commodity)}\b", lowered):
            entities.append(ExtractedEntity(entity_type="commodity", entity_value=commodity, confidence=0.78))

    deduped: dict[tuple[str, str], ExtractedEntity] = {}
    for item in entities:
        key = (item.entity_type, item.entity_value)
        existing = deduped.get(key)
        if existing is None or item.confidence > existing.confidence:
            deduped[key] = item

    return list(deduped.values())
