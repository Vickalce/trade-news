from fastapi import APIRouter, Depends

from api.core.config import settings
from api.providers.registry import (
    EXECUTION_PROVIDER_REGISTRY,
    MARKET_DATA_PROVIDER_REGISTRY,
    NEWS_PROVIDER_REGISTRY,
    serialize_provider_definition,
)
from api.security import secure_endpoint

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def list_supported_providers(_: None = Depends(secure_endpoint)):
    return {
        "selected": {
            "news": settings.news_provider,
            "market_data": settings.market_data_provider,
            "execution": settings.broker_provider,
        },
        "providers": {
            "news": [
                serialize_provider_definition(definition, settings.news_provider)
                for definition in NEWS_PROVIDER_REGISTRY.list_definitions()
            ],
            "market_data": [
                serialize_provider_definition(definition, settings.market_data_provider)
                for definition in MARKET_DATA_PROVIDER_REGISTRY.list_definitions()
            ],
            "execution": [
                serialize_provider_definition(definition, settings.broker_provider)
                for definition in EXECUTION_PROVIDER_REGISTRY.list_definitions()
            ],
        },
    }