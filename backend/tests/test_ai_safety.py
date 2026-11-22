"""Unit tests for the 3-layer SEBI-compliant safety guardrail and offline fallbacks."""

from app.ai.fallback import evaluate_reasoning_deterministic, fallback_coach_note
from app.ai.safety import (
    is_advice_request,
    looks_like_advice,
    looks_like_directive,
    numbers_grounded,
    validate_json_output,
)
from app.market.portfolio import PortfolioState, preview_order_consequence
from app.market.simulator import build_market


def test_layer1_blocks_english_and_hindi_stock_tip_requests():
    assert is_advice_request("Should I buy Rocket Infra today?") is True
    assert is_advice_request("Give me a multibagger stock to buy") is True
    assert is_advice_request("कौन सा शेयर खरीदूँ अभी?") is True
    assert is_advice_request("क्या मुझे यह शेयर बेचना चाहिए?") is True

    # Educational questions MUST pass Layer 1
    assert is_advice_request("What is a lower circuit?") is False
    assert is_advice_request("P/E अनुपात क्या होता है?") is False


def test_layer3_rejects_advice_and_directives():
    assert looks_like_advice("You should buy Gangotri Foods right now.") is True
    assert looks_like_advice("यह अच्छा शेयर है, अभी खरीद लो।") is True
    assert looks_like_advice("This company has low debt and steady 3-year sales.") is False

    # Coach mode allows quoting a friend's tip while still blocking direct commands
    assert looks_like_directive('Your friend said "buy it now", which created FOMO.') is False
    assert looks_like_directive("You should sell this stock today.") is True


def test_layer3_number_grounding_handles_latin_and_devanagari():
    facts = "Price: ₹38.50. Order Value: ₹3,850. 5-day change: 42.5%. Portfolio Weight: 28%."

    # Grounded numbers (and small counting numbers <= 12) pass
    assert numbers_grounded("At ₹38.50 this is 28% of your money after a 42.5% run in 5 days.", facts) is True
    assert numbers_grounded("₹३८.५० पर यह 28% हिस्सा है।", facts) is True

    # Hallucinated target price or invented percentage fails immediately
    assert numbers_grounded("This stock can reach ₹95 soon.", facts) is False
    assert numbers_grounded("You will make 75% profit.", facts) is False


def test_validate_json_output_catches_hallucinated_number_in_nested_field():
    facts = "Order Value: ₹10,000. 2-sigma drop: 18% (₹1,800)."
    good = {
        "question": "Are you okay losing ₹1,800 if it drops 18%?",
        "what_is_right": "You paused to think.",
        "what_is_missing": "Debt was not checked.",
        "next_time_tip": "Check Fundamentals first.",
    }
    bad = {**good, "next_time_tip": "Wait until it rises 65% next month."}

    assert validate_json_output(good, facts, required_keys=("question", "what_is_right", "what_is_missing", "next_time_tip")) is None
    assert validate_json_output(bad, facts, required_keys=("question", "what_is_right", "what_is_missing", "next_time_tip")) == "ungrounded_number"


def test_offline_reasoning_gate_scores_tip_weak_and_fundamentals_sound():
    m = build_market(mode="guided")
    state = PortfolioState(starting_cash=100_000.0, cash=100_000.0, day=5)

    tip_preview = preview_order_consequence(state, m, code="ROCKINFR", qty=500, day=5, mtf=True)
    tip_res = evaluate_reasoning_deterministic(
        reason_text="Saw a Telegram tip, price is running fast!",
        reason_tag="tip",
        preview=tip_preview,
        opened_fundamentals=False,
        read_news=False,
        lang="en",
    )
    assert tip_res["verdict"] == "weak"
    assert tip_res["score"] < 40
    assert "tip" in tip_res["flags"]
    assert tip_res["question"] != ""

    sound_preview = preview_order_consequence(state, m, code="GANGOTRI", qty=20, day=5, mtf=False)
    sound_res = evaluate_reasoning_deterministic(
        reason_text="Steady 3-year sales growth, low debt, and long term packaged food business.",
        reason_tag="fundamentals",
        preview=sound_preview,
        opened_fundamentals=True,
        read_news=True,
        lang="en",
    )
    assert sound_res["verdict"] == "sound"
    assert sound_res["score"] >= 80
    assert sound_res["question"] == ""


def test_offline_coach_returns_hindi_and_english_notes():
    hi = fallback_coach_note("lower_circuit_trap", lang="hi")
    en = fallback_coach_note("lower_circuit_trap", lang="en")
    assert "लोअर सर्किट" in hi["title"]
    assert "Lower Circuit" in en["title"]
