"""Guardrailed Sarvam AI & Voice FastAPI endpoints with rate limiting and upload size caps."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.ai.fallback import (
    evaluate_reasoning_deterministic,
    fallback_coach_note,
    fallback_report_narrative,
)
from app.ai.prompts import (
    build_ask_prompt,
    build_coach_prompt,
    build_reasoning_prompt,
    build_report_prompt,
)
from app.ai.safety import (
    advice_refusal_message,
    is_advice_request,
    validate_json_output,
    validate_text_output,
)
from app.ai.sarvam import (
    SarvamError,
    chat_completion,
    synthesize_speech,
    think_json_validated,
    transcribe_speech,
)
from app.market.catalog import COMPANY_BY_CODE
from app.market.portfolio import OrderError, preview_order_consequence, replay_orders
from app.market.simulator import build_market
from app.routes.core import _to_behaviour_meta, _to_order_req
from app.schemas import OrderPayload, ScoreReportRequest, bounded_list
from app.scoring.habits import score_behaviour
from app.security import MAX_AUDIO_UPLOAD_BYTES, enforce_ai_rate_limit

router = APIRouter(
    prefix="/api",
    tags=["Sarvam AI & Voice"],
    dependencies=[Depends(enforce_ai_rate_limit)],
)


class ReasonRequest(BaseModel):
    mode: Literal["guided", "practice"] = "guided"
    seed: int = Field(default=42, ge=1, le=999_999)
    day: int = Field(..., ge=1, le=21)
    lang: Literal["en", "hi"] = "en"
    starting_cash: float = Field(default=100_000.0, gt=0, le=10_000_000)
    orders: list[OrderPayload] = bounded_list(200)
    code: str = Field(..., min_length=2, max_length=16)
    qty: int = Field(..., gt=0, le=100_000)
    mtf: bool = False
    reason_tag: str = Field(default="other", max_length=32)
    reason_text: str = Field(default="", max_length=500)
    opened_fundamentals: bool = False
    read_news: bool = False


class CoachRequest(BaseModel):
    mode: Literal["guided", "practice"] = "guided"
    seed: int = Field(default=42, ge=1, le=999_999)
    day: int = Field(..., ge=1, le=21)
    lang: Literal["en", "hi"] = "en"
    starting_cash: float = Field(default=100_000.0, gt=0, le=10_000_000)
    orders: list[OrderPayload] = bounded_list(200)
    event_type: str = Field(default="welcome", max_length=32)


class AskRequest(BaseModel):
    lang: Literal["en", "hi"] = "en"
    question: str = Field(..., min_length=2, max_length=300)


class ReportNarrativeRequest(ScoreReportRequest):
    lang: Literal["en", "hi"] = "en"


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    lang: Literal["en", "hi"] = "hi"


@router.post("/ai/reason")
async def check_order_reasoning(req: ReasonRequest) -> dict:
    if req.code not in COMPANY_BY_CODE:
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_STOCK", "message": f"Unknown stock: {req.code}"})

    if is_advice_request(req.reason_text):
        return {"blocked_as_advice": True, **advice_refusal_message(req.lang)}

    market = build_market(mode=req.mode, seed=req.seed)
    try:
        state = replay_orders(market, req.starting_cash, [_to_order_req(o) for o in req.orders], as_of_day=req.day)
    except OrderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "en": exc.message_en, "hi": exc.message_hi})

    preview = preview_order_consequence(state, market, code=req.code, qty=req.qty, day=req.day, mtf=req.mtf)
    base = evaluate_reasoning_deterministic(
        reason_text=req.reason_text,
        reason_tag=req.reason_tag,
        preview=preview,
        opened_fundamentals=req.opened_fundamentals,
        read_news=req.read_news,
        lang=req.lang,
    )

    company = COMPANY_BY_CODE[req.code]
    facts_text = (
        f"Company: {company.name}. Price: ₹{preview['price']}. Qty: {req.qty}. "
        f"Order Value: ₹{preview['order_value']}. Portfolio Weight: {preview['post_trade_weight_pct']}%. "
        f"5-day change: {preview['change_5d_pct']}%. 2-sigma 5d drop: {preview['two_sigma_5d_drop_pct']}% "
        f"(₹{preview['loss_on_2sigma_rupees']}). Debt: {company.fundamentals.debt_level}. "
        f"Profit trend: {company.fundamentals.profit_trend}. Sales 3y: {company.fundamentals.sales_3y_cr}. "
        f"Red flags: {', '.join(preview['risk_warnings']) or 'none'}."
    )

    sys_p, user_p = build_reasoning_prompt(
        lang=req.lang,
        stock_name=company.name,
        reason_text=req.reason_text or req.reason_tag,
        facts_text=facts_text,
        base_verdict=base["verdict"],
    )

    try:
        ai_obj = await think_json_validated(
            sys_p,
            user_p,
            validator=lambda o: validate_json_output(
                o,
                facts_text,
                required_keys=("question", "what_is_right", "what_is_missing", "next_time_tip"),
            ),
        )
        return {
            **base,
            "question": ai_obj["question"],
            "what_is_right": ai_obj["what_is_right"],
            "what_is_missing": ai_obj["what_is_missing"],
            "next_time_tip": ai_obj["next_time_tip"],
            "preview": preview,
            "source": "sarvam",
        }
    except SarvamError as exc:
        return {**base, "preview": preview, "source": "offline_fallback", "fallback_reason": exc.reason}


@router.post("/ai/coach")
async def get_coach_note(req: CoachRequest) -> dict:
    market = build_market(mode=req.mode, seed=req.seed)
    try:
        state = replay_orders(market, req.starting_cash, [_to_order_req(o) for o in req.orders], as_of_day=req.day)
    except OrderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "en": exc.message_en, "hi": exc.message_hi})

    eq = state.equity_value(market, req.day)
    facts_text = (
        f"Day: {req.day} of 21. Starting cash: ₹{state.starting_cash}. Current equity: ₹{eq}. "
        f"Free cash: ₹{state.cash}. Borrowed MTF: ₹{state.total_borrowed()}. "
        f"Margin calls: {state.margin_calls}. Max single-stock weight: {round(state.max_single_stock_weight * 100, 1)}%."
    )

    sys_p, user_p = build_coach_prompt(lang=req.lang, event_type=req.event_type, facts_text=facts_text)
    try:
        ai_obj = await think_json_validated(
            sys_p,
            user_p,
            validator=lambda o: validate_json_output(
                o,
                facts_text,
                required_keys=("title", "note", "question"),
                coach_mode=True,
            ),
        )
        return {**ai_obj, "source": "sarvam"}
    except SarvamError as exc:
        return {**fallback_coach_note(req.event_type, req.lang), "fallback_reason": exc.reason}


@router.post("/ai/ask")
async def ask_concept(req: AskRequest) -> dict:
    if is_advice_request(req.question):
        return advice_refusal_message(req.lang)

    sys_p, user_p = build_ask_prompt(lang=req.lang, question=req.question)
    try:
        raw = await chat_completion(sys_p, user_p, max_tokens=260, temperature=0.2)
        err = validate_text_output(raw, facts_text="", max_len=900)
        if err:
            raise SarvamError(f"validation:{err}", f"Ask answer rejected: {err}")
        return {"text": raw, "source": "sarvam"}
    except SarvamError as exc:
        offline_text = (
            "यह एक निवेश शिक्षा प्रश्न है। अभी AI फ़ॉलबैक मोड में है — कृपया कंपनी के फ़ंडामेंटल्स ⓘ देखें।"
            if req.lang == "hi"
            else "AI is currently in fallback mode. Check the Fundamentals ⓘ tooltips inside the simulator for plain-language explanations."
        )
        return {"text": offline_text, "source": "offline_fallback", "fallback_reason": exc.reason}


@router.post("/ai/report")
async def generate_full_report(req: ReportNarrativeRequest) -> dict:
    market = build_market(mode=req.mode, seed=req.seed)
    ordered = sorted(req.orders, key=lambda o: o.day)
    try:
        state = replay_orders(market, req.starting_cash, [_to_order_req(o) for o in ordered], as_of_day=req.as_of_day)
    except OrderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "en": exc.message_en, "hi": exc.message_hi})

    metas = [_to_behaviour_meta(o) for o in ordered if o.day <= req.as_of_day]
    scorecard = score_behaviour(state, market, order_meta=metas, stated_crash_reaction=req.stated_crash_reaction)

    facts_text = (
        f"Resilience Score: {scorecard['resilience_score']}/100. "
        f"Starting cash: ₹{scorecard['portfolio_summary']['starting_cash']}. "
        f"Final equity: ₹{scorecard['portfolio_summary']['final_equity']}. "
        f"Return: {scorecard['portfolio_summary']['total_return_pct']}%. "
        + " ".join(f"{h['id']}: {h['score']}/100 ({h['value']})." for h in scorecard["habits"])
    )

    sys_p, user_p = build_report_prompt(lang=req.lang, scorecard=scorecard, facts_text=facts_text)
    try:
        narrative = await think_json_validated(
            sys_p,
            user_p,
            validator=lambda o: validate_json_output(
                o,
                facts_text,
                required_keys=("headline", "summary", "rules"),
                coach_mode=True,
            ),
        )
        narrative["source"] = "sarvam"
    except SarvamError as exc:
        narrative = {**fallback_report_narrative(scorecard, req.lang), "fallback_reason": exc.reason}

    return {"scorecard": scorecard, "narrative": narrative}


@router.post("/voice/tts")
async def voice_tts(req: TTSRequest) -> dict:
    return await synthesize_speech(req.text, lang=req.lang)


@router.post("/voice/stt")
async def voice_stt(
    file: UploadFile = File(...),
    lang: Literal["en", "hi"] = Form(default="hi"),
) -> dict:
    # Read at most MAX_AUDIO_UPLOAD_BYTES + 1 to prevent unbounded memory consumption
    audio_bytes = await file.read(MAX_AUDIO_UPLOAD_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "AUDIO_TOO_LARGE",
                "en": "Voice recording exceeds the 4 MB limit.",
                "hi": "वॉइस रिकॉर्डिंग 4 MB सीमा से बड़ी है।",
            },
        )
    return await transcribe_speech(audio_bytes, filename=file.filename or "voice.webm", lang=lang)
