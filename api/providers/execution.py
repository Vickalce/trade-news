from typing import Protocol
from uuid import uuid4

import httpx

from api.core.config import settings
from api.providers.registry import EXECUTION_PROVIDER_REGISTRY, ProviderCapabilities, ProviderDefinition
from api.schemas import ExecutionOrder, ExecutionResult
from api.services.schwab_oauth import get_valid_access_token


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
        access_token = get_valid_access_token()

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
            "Authorization": f"Bearer {access_token}",
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


class AlpacaBrokerAdapter:
    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY are required for Alpaca execution")

        endpoint = f"{settings.alpaca_base_url}/orders"
        payload = {
            "symbol": order.symbol,
            "qty": str(order.quantity),
            "side": order.side.lower(),
            "type": order.order_type.lower(),
            "time_in_force": order.time_in_force.lower(),
        }
        headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=10) as client:
            response = client.post(endpoint, json=payload, headers=headers)

        if response.status_code not in (200, 201):
            raise ValueError(f"Alpaca order failed with status {response.status_code}: {response.text[:400]}")

        response_json = response.json() if response.text else {}
        order_id = str(response_json.get("id") or f"alpaca-{uuid4()}")
        return ExecutionResult(
            status="accepted",
            provider="alpaca",
            mode="live",
            order_id=order_id,
            detail=f"Submitted {order.side} {order.quantity} {order.symbol} to Alpaca",
        )



EXECUTION_PROVIDER_REGISTRY.register(
    ProviderDefinition(
        key="paper",
        kind="execution",
        display_name="Paper Broker",
        description="Simulated execution provider for dry runs and operator validation.",
        factory=PaperBrokerAdapter,
        capabilities=ProviderCapabilities(
            auth_type="none",
            supports_execution=True,
            supports_paper=True,
            supports_live=False,
            notes="No broker connectivity; safe default for testing.",
        ),
    )
)

EXECUTION_PROVIDER_REGISTRY.register(
    ProviderDefinition(
        key="schwab",
        kind="execution",
        display_name="Charles Schwab",
        description="Live order submission to a Schwab brokerage account.",
        factory=SchwabBrokerAdapter,
        capabilities=ProviderCapabilities(
            auth_type="oauth2",
            supports_execution=True,
            supports_live=True,
            supports_paper=False,
            notes="OAuth-based live execution adapter.",
        ),
        config_keys=("schwab_client_id", "schwab_client_secret", "schwab_redirect_uri"),
    )
)

EXECUTION_PROVIDER_REGISTRY.register(
    ProviderDefinition(
        key="alpaca",
        kind="execution",
        display_name="Alpaca",
        description="Live order submission to an Alpaca trading account.",
        factory=AlpacaBrokerAdapter,
        capabilities=ProviderCapabilities(
            auth_type="api_key",
            supports_execution=True,
            supports_live=True,
            supports_paper=True,
            notes="Use Alpaca paper or live base URL depending on environment.",
        ),
        config_keys=("alpaca_api_key", "alpaca_secret_key"),
    )
)


def get_broker_adapter() -> BrokerExecutionAdapter:
    return EXECUTION_PROVIDER_REGISTRY.create(settings.broker_provider)
