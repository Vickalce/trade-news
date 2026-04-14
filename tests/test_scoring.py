from api.schemas import EventScoreInput
from api.services.scoring import (
    compute_final_score,
    compute_reaction_score,
    compute_relevance_score,
)



def test_relevance_score_security_is_higher():
    security = compute_relevance_score("earnings", "security")
    macro = compute_relevance_score("earnings", "macro")
    assert security > macro



def test_reaction_score_bounds():
    score = compute_reaction_score(last_price=110, baseline_price=100, volume=200000, baseline_volume=100000)
    assert 0 <= score <= 100



def test_final_score_formula():
    score_input = EventScoreInput(
        relevance_score=80,
        reaction_score=70,
        historical_similarity_score=60,
        source_quality_score=90,
        impact_horizon="short",
        scope_type="security",
    )
    final_score = compute_final_score(score_input)
    assert final_score == 73.5
