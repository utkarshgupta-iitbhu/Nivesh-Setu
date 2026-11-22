"""Core deterministic FastAPI endpoints: health, market snapshot, order preview/validation,
stateless notification alert evaluation, and 21-day behavioural scorecard.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.market.alerts import AlertSpec, evaluate_alerts
from app.market.catalog import COMPANY_BY_CODE, SEASON_DAYS
from app.market.portfolio import (
    OrderError,
    OrderRequest,
    apply_order,
    preview_order_consequence,
    replay_orders,
)
from app.market.simulator import build_market, snapshot_for_day
from app.schemas import (
    AlertEvaluateRequest,
    OrderPayload,
    OrderPreviewRequest,
    OrderValidateRequest,
    ScoreReportRequest,
)
from app.scoring.habits import OrderBehaviourMeta, score_behaviour

router = APIRouter(prefix="/api", tags=["Core Simulator"])


def _to_order_req(o: OrderPayload) -> OrderRequest:
    return OrderRequest(
        day=o.day,
        code=o.code,
        side=o.side,
        qty=o.qty,
        mtf=o.mtf,
        reason_tag=o.reason_tag,
        reason_text=o.reason_text,
        think_ms=o.think_ms,
    )


def _to_behaviour_meta(o: OrderPayload) -> OrderBehaviourMeta:
    return OrderBehaviourMeta(
        opened_fundamentals=o.meta.opened_fundamentals,
        read_news=o.meta.read_news,
        viewed_chart=o.meta.viewed_chart,
        watched_before=o.meta.watched_before,
        gate_score=o.meta.gate_score,
        gate_verdict=o.meta.gate_verdict,
        gate_flags=tuple(o.meta.gate_flags),
    )


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "product": "NiveshSetu",
        "version": "2.0.0",
        "season_days": SEASON_DAYS,
        "ai_enabled": settings.ai_enabled,
        "ai_provider": "sarvam" if settings.ai_enabled else "offline_fallback",
    }


@router.get("/market")
def get_market_snapshot(
    mode: str = Query(default="guided", pattern="^(guided|practice)$"),
    seed: int = Query(default=42, ge=1, le=999_999),
    day: int = Query(default=1, ge=0, le=SEASON_DAYS),
) -> dict:
    market = build_market(mode=mode, seed=seed)  # type: ignore[arg-type]
    return snapshot_for_day(market, day=day)


@router.post("/order/preview")
def preview_order(req: OrderPreviewRequest) -> dict:
    if req.code not in COMPANY_BY_CODE:
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_STOCK", "message": f"Unknown stock: {req.code}"})
    market = build_market(mode=req.mode, seed=req.seed)
    try:
        state = replay_orders(market, req.starting_cash, [_to_order_req(o) for o in req.orders], as_of_day=req.day)
    except OrderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "en": exc.message_en, "hi": exc.message_hi})
    return preview_order_consequence(state, market, code=req.code, qty=req.qty, day=req.day, mtf=req.mtf)


@router.post("/order/validate")
def validate_and_apply_order(req: OrderValidateRequest) -> dict:
    market = build_market(mode=req.mode, seed=req.seed)
    try:
        state = replay_orders(
            market,
            req.starting_cash,
            [_to_order_req(o) for o in req.existing_orders],
            as_of_day=req.new_order.day,
        )
        executed = apply_order(state, market, _to_order_req(req.new_order))
    except OrderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "en": exc.message_en, "hi": exc.message_hi})

    equity = state.equity_value(market, state.day)
    return {
        "ok": True,
        "executed": {
            "day": executed.day,
            "code": executed.code,
            "side": executed.side,
            "qty": executed.qty,
            "price": executed.price,
            "value": executed.value,
            "mtf": executed.mtf,
            "realized_pnl": executed.realized_pnl,
        },
        "portfolio": {
            "starting_cash": state.starting_cash,
            "cash": state.cash,
            "equity": equity,
            "total_return_pct": round(((equity - state.starting_cash) / max(1.0, state.starting_cash)) * 100.0, 2),
            "total_interest_paid": state.total_interest_paid,
            "total_borrowed": state.total_borrowed(),
            "margin_calls": state.margin_calls,
            "holdings": {
                code: {
                    "qty": h.qty,
                    "avg_cost": h.avg_cost,
                    "own_margin": h.own_margin,
                    "borrowed": h.borrowed,
                }
                for code, h in state.holdings.items()
            },
        },
    }


@router.post("/alerts/evaluate")
def eval_alerts(req: AlertEvaluateRequest) -> dict:
    market = build_market(mode=req.mode, seed=req.seed)
    specs = [
        AlertSpec(id=a.id, code=a.code, rule=a.rule, threshold=a.threshold)
        for a in req.alerts
    ]
    return {"day": req.day, "triggered": evaluate_alerts(market, specs, req.day)}


@router.post("/report/score")
def compute_score_report(req: ScoreReportRequest) -> dict:
    market = build_market(mode=req.mode, seed=req.seed)
    ordered = sorted(req.orders, key=lambda o: o.day)
    try:
        state = replay_orders(market, req.starting_cash, [_to_order_req(o) for o in ordered], as_of_day=req.as_of_day)
    except OrderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "en": exc.message_en, "hi": exc.message_hi})
    metas = [_to_behaviour_meta(o) for o in ordered if o.day <= req.as_of_day]
    return score_behaviour(state, market, order_meta=metas, stated_crash_reaction=req.stated_crash_reaction)
