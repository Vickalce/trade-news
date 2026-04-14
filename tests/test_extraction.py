from api.services.extraction import extract_entities



def test_extracts_company_and_ticker():
    entities = extract_entities("Apple earnings beat expectations")
    payload = {(e.entity_type, e.entity_value) for e in entities}
    assert ("company", "Apple") in payload
    assert ("ticker", "AAPL") in payload



def test_extracts_sector_and_commodity():
    entities = extract_entities("Oil prices jump as energy stocks rally")
    payload = {(e.entity_type, e.entity_value) for e in entities}
    assert ("sector", "energy") in payload
    assert ("commodity", "oil") in payload
