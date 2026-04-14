from typing import Protocol
from uuid import uuid4

import httpx

from api.core.config import settings
from api.schemas import ExecutionOrder, ExecutionResult


class BrokerExecutionAdapter(Protocol):
    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        ...


class PaperBrokerAdapter:
    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        return ExecutionResult(
            status="accepted",
            provider="paper",
            mode="dry-run",
            order_id=f"paper-{uuid4()}",
            detail=f"Simulated {order.side} {order.quantity} {order.symbol}",
        )


class SchwabBrokerAdapter:
    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        if not settings.schwab_access_token:
            raise ValueError("SCHWAB_ACCESS_TOKEN is required for live Schwab order submission")

        endpoint = f"{settings.schwab_base_url}/accounts/{order.account_id}/orders"
        payload = {
            "orderType": order.order_type,
            "session": "NORMAL",
            "duration": order.time_in_force,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": order.side,
                    "quantity": order.quantity,
                    "instrument": {"symbol": order.symbol, "assetType": "EQUITY"},
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.schwab_access_token}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=10) as client:
            response = client.post(endpoint, json=payload, headers=headers)

        if response.status_code not in (200, 201):
            raise ValueError(f"Schwab order failed with status {response.status_code}: {response.text[:400]}")

        order_id = response.headers.get("Location", f"schwab-{uuid4()}")
        return ExecutionResult(
            status="accepted",
            provider="schwab",
            mode="live",
            order_id=order_id,
            detail=f"Submitted {order.side} {order.quantity} {order.symbol} to Schwab",
        )



def get_broker_adapter() -> BrokerExecutionAdapter:
    if settings.broker_provider.lower() == "schwab":
        return SchwabBrokerAdapter()
    return PaperBrokerAdapter()
