from sqlalchemy.orm import Session

from api.core.config import settings
from api.db.models import Recommendation
from api.providers.execution import get_broker_adapter
from api.schemas import ExecutionOrder, ExecutionResult



def _map_recommendation_to_side(recommendation: str) -> str:
    if recommendation == "buy_candidate":
        return "BUY"
    if recommendation == "sell_candidate":
        return "SELL"
    raise ValueError("Hold recommendations cannot be executed")



def build_order_from_recommendation(
    recommendation_row: Recommendation,
    account_id: str,
    price_hint: float,
) -> ExecutionOrder:
    side = _map_recommendation_to_side(recommendation_row.recommendation)
    max_notional = max(1.0, settings.order_max_notional_usd)
    quantity = max(1, int(max_notional // price_hint))

    return ExecutionOrder(
        account_id=account_id,
        symbol=recommendation_row.symbol,
        side=side,
        quantity=quantity,
    )



def get_recommendation_or_raise(db: Session, recommendation_id: int) -> Recommendation:
    row = db.query(Recommendation).filter(Recommendation.id == recommendation_id).one_or_none()
    if row is None:
        raise ValueError(f"Recommendation {recommendation_id} not found")
    return row



def submit_order(order: ExecutionOrder) -> ExecutionResult:
    adapter = get_broker_adapter()

    if settings.broker_kill_switch_enabled:
        return ExecutionResult(
            status="blocked",
            provider=settings.broker_provider,
            mode="dry-run" if settings.broker_dry_run else "live",
            order_id="blocked-by-kill-switch",
            detail="Broker kill switch is enabled. Disable BROKER_KILL_SWITCH_ENABLED to submit orders.",
        )

    if settings.broker_dry_run:
        # Force paper adapter response even when another provider is configured.
        return ExecutionResult(
            status="accepted",
            provider="paper",
            mode="dry-run",
            order_id="dry-run-only",
            detail=f"Dry-run: {order.side} {order.quantity} {order.symbol}",
        )

    return adapter.submit_order(order)
