from dataclasses import dataclass

from sqlalchemy.orm import Session

from api.db.models import MarketSnapshot, Recommendation


@dataclass
class ValidationSummary:
    total: int
    wins: int
    losses: int
    win_rate: float
    avg_confidence: float



def run_paper_validation(db: Session, limit: int = 200) -> ValidationSummary:
    rows = (
        db.query(Recommendation, MarketSnapshot)
        .join(MarketSnapshot, MarketSnapshot.symbol == Recommendation.symbol)
        .order_by(Recommendation.created_at_utc.desc())
        .limit(limit)
        .all()
    )

    wins = 0
    losses = 0
    total_conf = 0.0

    for rec, snap in rows:
        total_conf += rec.confidence
        direction_up = snap.last_price >= snap.baseline_price
        if rec.recommendation == "buy_candidate" and direction_up:
            wins += 1
        elif rec.recommendation == "sell_candidate" and not direction_up:
            wins += 1
        elif rec.recommendation == "hold":
            wins += 1
        else:
            losses += 1

    total = len(rows)
    win_rate = 0.0 if total == 0 else round((wins / total) * 100, 2)
    avg_conf = 0.0 if total == 0 else round(total_conf / total, 2)
    return ValidationSummary(total=total, wins=wins, losses=losses, win_rate=win_rate, avg_confidence=avg_conf)
