from api.schemas import EventScoreInput

SOURCE_QUALITY = {
    "reuters": 90.0,
    "marketwatch": 75.0,
    "cnbc": 78.0,
}



def compute_relevance_score(category: str, scope_type: str) -> float:
    base = {
        "earnings": 82,
        "macro": 70,
        "geopolitical": 74,
        "commodity": 68,
        "other": 55,
    }.get(category, 55)

    scope_weight = {"security": 1.1, "sector": 1.0, "macro": 0.9}.get(scope_type, 1.0)
    return float(max(0, min(100, round(base * scope_weight, 2))))



def compute_reaction_score(last_price: float, baseline_price: float, volume: float, baseline_volume: float) -> float:
    if baseline_price <= 0 or baseline_volume <= 0:
        return 50.0

    price_move = abs((last_price - baseline_price) / baseline_price)
    volume_spike = volume / baseline_volume
    score = 40 + (price_move * 300) + (volume_spike * 12)
    return float(max(0, min(100, round(score, 2))))



def compute_historical_similarity(category: str, entity_count: int) -> float:
    category_base = {
        "earnings": 72.0,
        "macro": 65.0,
        "geopolitical": 60.0,
        "commodity": 62.0,
        "other": 50.0,
    }.get(category, 50.0)
    density_bonus = min(20.0, entity_count * 4.0)
    return float(max(0, min(100, round(category_base + density_bonus, 2))))



def compute_source_quality(source: str) -> float:
    lowered = source.lower()
    for needle, score in SOURCE_QUALITY.items():
        if needle in lowered:
            return score
    return 60.0



def compute_final_score(score_input: EventScoreInput) -> float:
    final_score = (
        0.35 * score_input.relevance_score
        + 0.35 * score_input.reaction_score
        + 0.20 * score_input.historical_similarity_score
        + 0.10 * score_input.source_quality_score
    )
    return float(round(max(0, min(100, final_score)), 2))



def compute_priority(final_score: float) -> str:
    if final_score >= 70:
        return "high"
    if final_score >= 40:
        return "medium"
    return "low"
