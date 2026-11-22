"""System and user prompt builders for Sarvam AI.

Every prompt enforces the SEBI public-good guardrails:
- Judge the user's REASONING, never whether a stock is good or bad.
- Use ONLY numbers present in the server-computed facts block.
- Never give buy/sell/hold advice, target prices, or reveal future days.
"""

from __future__ import annotations

import json
from typing import Any

_BASE_GUARDRAIL = (
    "You are NiveshSetu, a calm, non-commercial Indian investor-education guide for a 21-day fictional market simulator. "
    "STRICT RULES: "
    "1) NEVER recommend buying, selling, or holding any stock, and NEVER call a stock 'good' or 'bad'. "
    "2) NEVER predict future prices or reveal future days. "
    "3) ONLY use numbers that appear verbatim in the FACTS section below — never invent any number or percentage. "
    "4) Keep language simple, warm, and jargon-free for Tier-2/3 Indian first-time investors."
)


def _lang_instruction(lang: str) -> str:
    return (
        "Write all text values in simple, natural conversational Hindi (Devanagari script)."
        if lang == "hi"
        else "Write all text values in simple, plain English."
    )


def build_reasoning_prompt(
    *,
    lang: str,
    stock_name: str,
    reason_text: str,
    facts_text: str,
    base_verdict: str,
) -> tuple[str, str]:
    system = (
        f"{_BASE_GUARDRAIL}\n{_lang_instruction(lang)}\n"
        "Your job is to evaluate the user's REASONING (not the company). "
        "Return JSON with exact keys: "
        '{"question": "one short pointed reflective question if verdict is weak/mixed, else empty string", '
        '"what_is_right": "1 short sentence acknowledging any sound thought or honesty", '
        '"what_is_missing": "1 short sentence naming what risk or fact they did not consider", '
        '"next_time_tip": "1 short habit tip for future decisions"}'
    )
    user = (
        f"STOCK: {stock_name}\n"
        f"DETERMINISTIC VERDICT: {base_verdict}\n"
        f"USER REASON: {reason_text}\n"
        f"FACTS (use ONLY these numbers):\n{facts_text}"
    )
    return system, user


def build_coach_prompt(
    *,
    lang: str,
    event_type: str,
    facts_text: str,
) -> tuple[str, str]:
    system = (
        f"{_BASE_GUARDRAIL}\n{_lang_instruction(lang)}\n"
        "Write a short, empathetic 2-sentence coach note about what just happened in the user's portfolio, "
        "ending with 1 reflective question. Never tell them to buy or sell. "
        'Return JSON: {"title": "short 3-5 word title", "note": "2 short sentences", "question": "1 reflective question"}'
    )
    user = f"EVENT: {event_type}\nFACTS (use ONLY these numbers):\n{facts_text}"
    return system, user


def build_ask_prompt(*, lang: str, question: str) -> tuple[str, str]:
    system = (
        f"{_BASE_GUARDRAIL}\n{_lang_instruction(lang)}\n"
        "Explain the financial concept or regulatory process clearly in 3-4 short sentences using an everyday Indian analogy "
        "(like a kirana shop, fixed deposit, or crop harvest). Do not invent statistics."
    )
    return system, f"USER QUESTION: {question}"


def build_report_prompt(*, lang: str, scorecard: dict[str, Any], facts_text: str) -> tuple[str, str]:
    system = (
        f"{_BASE_GUARDRAIL}\n{_lang_instruction(lang)}\n"
        "The deterministic engine has already calculated the user's 21-day Resilience Score and habit scores. "
        "NEVER change or invent any score. Write a warm summary and 3 concrete personal rules for next time. "
        'Return JSON: {"headline": "1 short sentence", "summary": "2-3 short sentences", "rules": ["rule 1", "rule 2", "rule 3"]}'
    )
    compact = {
        "resilience_score": scorecard["resilience_score"],
        "habits": [{"id": h["id"], "score": h["score"], "band": h["band"]} for h in scorecard["habits"]],
        "stated_vs_actual_crash": scorecard["stated_vs_actual_crash"],
    }
    user = f"SCORECARD:\n{json.dumps(compact)}\nFACTS (use ONLY these numbers):\n{facts_text}"
    return system, user
