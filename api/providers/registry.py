from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from api.core.config import settings

ProviderKind = Literal["news", "market_data", "execution"]
ProviderAuthType = Literal["none", "api_key", "oauth2", "custom"]


@dataclass(frozen=True)
class ProviderCapabilities:
    auth_type: ProviderAuthType = "none"
    supports_news: bool = False
    supports_market_data: bool = False
    supports_execution: bool = False
    supports_live: bool = True
    supports_paper: bool = False
    notes: str = ""


@dataclass(frozen=True)
class ProviderDefinition:
    key: str
    kind: ProviderKind
    display_name: str
    description: str
    factory: Callable[[], Any]
    capabilities: ProviderCapabilities
    config_keys: tuple[str, ...] = ()


class ProviderRegistry:
    def __init__(self, kind: ProviderKind):
        self.kind = kind
        self._providers: dict[str, ProviderDefinition] = {}

    def register(self, definition: ProviderDefinition) -> ProviderDefinition:
        if definition.kind != self.kind:
            raise ValueError(f"Cannot register {definition.kind} provider in {self.kind} registry")
        self._providers[definition.key.lower()] = definition
        return definition

    def get_definition(self, key: str) -> ProviderDefinition:
        definition = self._providers.get(key.lower())
        if definition is None:
            available = ", ".join(sorted(self._providers)) or "none"
            raise ValueError(f"Unknown {self.kind} provider '{key}'. Available: {available}")
        return definition

    def create(self, key: str) -> Any:
        return self.get_definition(key).factory()

    def list_definitions(self) -> list[ProviderDefinition]:
        return [self._providers[key] for key in sorted(self._providers)]


NEWS_PROVIDER_REGISTRY = ProviderRegistry("news")
MARKET_DATA_PROVIDER_REGISTRY = ProviderRegistry("market_data")
EXECUTION_PROVIDER_REGISTRY = ProviderRegistry("execution")


def is_provider_configured(definition: ProviderDefinition) -> bool:
    if not definition.config_keys:
        return True
    return all(bool(getattr(settings, key, "")) for key in definition.config_keys)


def serialize_provider_definition(definition: ProviderDefinition, selected_key: str | None = None) -> dict[str, Any]:
    capabilities = definition.capabilities
    return {
        "key": definition.key,
        "kind": definition.kind,
        "display_name": definition.display_name,
        "description": definition.description,
        "selected": definition.key.lower() == (selected_key or "").lower(),
        "configured": is_provider_configured(definition),
        "config_keys": list(definition.config_keys),
        "capabilities": {
            "auth_type": capabilities.auth_type,
            "supports_news": capabilities.supports_news,
            "supports_market_data": capabilities.supports_market_data,
            "supports_execution": capabilities.supports_execution,
            "supports_live": capabilities.supports_live,
            "supports_paper": capabilities.supports_paper,
            "notes": capabilities.notes,
        },
    }
