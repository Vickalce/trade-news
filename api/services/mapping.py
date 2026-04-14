from api.schemas import ExtractedEntity

SECTOR_TO_PROXY = {
    "technology": "XLK",
    "energy": "XLE",
    "financials": "XLF",
    "healthcare": "XLV",
}


class MappingResult:
    def __init__(self, symbols: list[str], sector_proxies: list[str]):
        self.symbols = symbols
        self.sector_proxies = sector_proxies



def map_entities_to_symbols(entities: list[ExtractedEntity]) -> MappingResult:
    symbols = sorted({entity.entity_value for entity in entities if entity.entity_type == "ticker"})
    sectors = {entity.entity_value for entity in entities if entity.entity_type == "sector"}
    sector_proxies = sorted({SECTOR_TO_PROXY[s] for s in sectors if s in SECTOR_TO_PROXY})

    if not symbols and sector_proxies:
        symbols = sector_proxies.copy()

    return MappingResult(symbols=symbols, sector_proxies=sector_proxies)
