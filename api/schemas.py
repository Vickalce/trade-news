from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NormalizedNewsEvent(BaseModel):
    event_time_utc: datetime
    source: str = Field(max_length=100)
    headline: str = Field(max_length=500)
    body: str | None = None
    url: str | None = Field(default=None, max_length=1000)
    language: str = Field(default="en", max_length=16)
    category: str | None = Field(default=None, max_length=64)
    dedupe_hash: str = Field(max_length=64)


class ExtractedEntity(BaseModel):
    entity_type: Literal["company", "ticker", "country", "commodity", "sector"]
    entity_value: str = Field(max_length=255)
    confidence: float = Field(ge=0.0, le=1.0)


class ReactionFeatures(BaseModel):
    symbol: str = Field(max_length=16)
    last_price: float
    volume: float
    volatility_proxy: float
    baseline_price: float
    baseline_volume: float


class EventScoreInput(BaseModel):
    relevance_score: float = Field(ge=0, le=100)
    reaction_score: float = Field(ge=0, le=100)
    historical_similarity_score: float = Field(ge=0, le=100)
    source_quality_score: float = Field(ge=0, le=100)
    impact_horizon: Literal["short", "medium", "long"]
    scope_type: Literal["security", "sector", "macro"]


class PipelineResult(BaseModel):
    event_id: int
    symbol: str
    final_score: float
    recommendation: Literal["buy_candidate", "sell_candidate", "hold"]
    confidence: float
    rationale: str
    priority: Literal["low", "medium", "high"]


class ExecutionPreviewRequest(BaseModel):
    recommendation_id: int
    account_id: str
    price_hint: float = Field(default=100.0, gt=0)


class ExecutionSubmitRequest(BaseModel):
    recommendation_id: int
    account_id: str
    price_hint: float = Field(default=100.0, gt=0)
    confirm_token: str


class ExecutionOrder(BaseModel):
    account_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: int = Field(ge=1)
    order_type: Literal["MARKET"] = "MARKET"
    time_in_force: Literal["DAY"] = "DAY"


class ExecutionResult(BaseModel):
    status: str
    provider: str
    mode: Literal["dry-run", "live"]
    order_id: str
    detail: str
