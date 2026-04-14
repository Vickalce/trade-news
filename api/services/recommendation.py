from api.services.scoring import compute_priority



def build_recommendation(final_score: float, last_price: float, baseline_price: float) -> tuple[str, float, str, str, str]:
    trend = "positive" if last_price > baseline_price else "negative"

    if final_score >= 70 and trend == "positive":
        action = "buy_candidate"
    elif final_score >= 70 and trend == "negative":
        action = "sell_candidate"
    else:
        action = "hold"

    confidence = round(min(99.0, max(1.0, final_score)), 2)
    priority = compute_priority(final_score)
    rationale = (
        f"Final score {final_score} with {trend} immediate price reaction. "
        f"Priority is {priority} and action is {action}."
    )
    invalidation = "Invalidate if price trend reverses and score drops below 40."
    return action, confidence, rationale, invalidation, priority
