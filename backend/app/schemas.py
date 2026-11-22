"""Pydantic request/response schemas for FastAPI endpoints with strict input bounds."""

from __future__ import annotations

from typing import Literal
import pydantic as _pydantic
from pydantic import BaseModel, Field


def bounded_list(max_n: int):
    kw = {"max_items": max_n} if _pydantic.__version__.startswith("1.") else {"max_length": max_n}
    return Field(default_factory=list, **kw)



class OrderMetaPayload(BaseModel):
    opened_fundamentals: bool = False
    read_news: bool = False
    viewed_chart: bool = False
    watched_before: bool = False
    gate_score: float | None = Field(default=None, ge=0, le=100)
    gate_verdict: Literal["sound", "mixed", "weak"] | None = None
    gate_flags: list[str] = bounded_list(10)


class OrderPayload(BaseModel):
    day: int = Field(..., ge=1, le=21)
    code: str = Field(..., min_length=2, max_length=16)
    side: Literal["buy", "sell"]
    qty: int = Field(..., gt=0, le=100_000)
    mtf: bool = False
    reason_tag: str = Field(default="other", max_length=32)
    reason_text: str = Field(default="", max_length=500)
    think_ms: int = Field(default=0, ge=0, le=3_600_000)
    meta: OrderMetaPayload = Field(default_factory=OrderMetaPayload)


class OrderPreviewRequest(BaseModel):
    mode: Literal["guided", "practice"] = "guided"
    seed: int = Field(default=42, ge=1, le=999_999)
    day: int = Field(..., ge=1, le=21)
    starting_cash: float = Field(default=100_000.0, gt=0, le=10_000_000)
    orders: list[OrderPayload] = bounded_list(200)
    code: str = Field(..., min_length=2, max_length=16)
    qty: int = Field(..., gt=0, le=100_000)
    mtf: bool = False


class OrderValidateRequest(BaseModel):
    mode: Literal["guided", "practice"] = "guided"
    seed: int = Field(default=42, ge=1, le=999_999)
    starting_cash: float = Field(default=100_000.0, gt=0, le=10_000_000)
    existing_orders: list[OrderPayload] = bounded_list(200)
    new_order: OrderPayload


class AlertPayload(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=2, max_length=16)
    rule: Literal[
        "price_above",
        "price_below",
        "day_change_pct_above",
        "day_change_pct_below",
        "volume_spike_2x",
        "cross_sma20",
    ]
    threshold: float = Field(default=0.0, ge=0, le=1_000_000)


class AlertEvaluateRequest(BaseModel):
    mode: Literal["guided", "practice"] = "guided"
    seed: int = Field(default=42, ge=1, le=999_999)
    day: int = Field(..., ge=1, le=21)
    alerts: list[AlertPayload] = bounded_list(50)


class ScoreReportRequest(BaseModel):
    mode: Literal["guided", "practice"] = "guided"
    seed: int = Field(default=42, ge=1, le=999_999)
    as_of_day: int = Field(default=21, ge=1, le=21)
    starting_cash: float = Field(default=100_000.0, gt=0, le=10_000_000)
    orders: list[OrderPayload] = bounded_list(200)
    stated_crash_reaction: str | None = Field(default=None, max_length=32)
