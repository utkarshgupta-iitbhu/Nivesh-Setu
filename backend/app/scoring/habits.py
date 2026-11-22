"""Deterministic 9-Habit Behavioural Resilience Scoring Engine.

Guardrail: Every score (0-100) is computed from transparent, written mathematical
thresholds — NEVER invented by an LLM. The AI in Part 3 only writes coaching
explanations around these verified numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any, Literal

from app.market.catalog import COMPANY_BY_CODE
from app.market.portfolio import ExecutedOrder, PortfolioState
from app.market.simulator import MarketData, get_change_over

Band = Literal["good", "ok", "poor"]

HABIT_WEIGHTS: dict[str, float] = {
    "research": 0.17,
    "reasoning": 0.17,
    "crash": 0.15,
    "fomo": 0.14,
    "concentration": 0.12,
    "think": 0.10,
    "leverage": 0.07,
    "churn": 0.04,
    "pause": 0.04,
}

HABIT_FORMULAS: dict[str, dict[str, str]] = {
    "research": {
        "en": "Per buy: opened Fundamentals ⓘ (+35) + read News (+25) + viewed 3M Chart (+15) + watched from an earlier day (+25). Score = average across buys.",
        "hi": "हर ख़रीद पर: फ़ंडामेंटल्स ⓘ (+35) + न्यूज़ पढ़ी (+25) + 3-माह चार्ट देखा (+15) + पहले से वॉचलिस्ट में (+25)। स्कोर = औसत।",
    },
    "reasoning": {
        "en": "Average quality score (0-100) given by the pre-trade Reasoning Gate to your final buy reasons.",
        "hi": "ख़रीद से पहले रीजनिंग गेट द्वारा आपके कारणों को दिए गए स्कोर (0-100) का औसत।",
    },
    "think": {
        "en": "Median seconds from opening a stock page to placing a buy: ≤15s = 0, 45s = 50, ≥120s = 100.",
        "hi": "शेयर खोलने से ख़रीदने तक का मीडियन समय: ≤15 सेकंड = 0, 45 सेकंड = 50, ≥120 सेकंड = 100।",
    },
    "fomo": {
        "en": "Share of buys made on a tip, 'price is running', or after a ≥15% 5-day surge: 0% = 100, ≥50% = 0.",
        "hi": "टिप, भागती क़ीमत, या 5 दिन में ≥15% उछाल के बाद की गई ख़रीदों का हिस्सा: 0% = 100, ≥50% = 0।",
    },
    "concentration": {
        "en": "Peak share of your net worth placed in one stock: ≤25% = 100, ≥60% = 0.",
        "hi": "एक ही कंपनी में आपके कुल पैसे का अधिकतम हिस्सा: ≤25% = 100, ≥60% = 0।",
    },
    "crash": {
        "en": "Share of your holdings sold out of fear during the crash window: 0% = 100, ≥50% = 0.",
        "hi": "गिरावट के दिनों में डर से बेचे गए शेयरों का हिस्सा: 0% = 100, ≥50% = 0।",
    },
    "leverage": {
        "en": "No MTF margin = 100, used MTF without a margin call = 45, hit a forced margin call = 0.",
        "hi": "कोई MTF नहीं = 100, बिना मार्जिन कॉल MTF = 45, मार्जिन कॉल = 0।",
    },
    "churn": {
        "en": "Manual orders placed: ≤8 = 100, ≥24 = 30, minus 15 for each quick flip (sold within 2 days of buying).",
        "hi": "कुल ऑर्डर: ≤8 = 100, ≥24 = 30, और ख़रीदने के 2 दिन के भीतर बेचने पर हर बार -15।",
    },
    "pause": {
        "en": "Times you still bought after the Reasoning Gate warned your reason was weak: 0 = 100, 1 = 55, 2+ = 15.",
        "hi": "कमज़ोर कारण की चेतावनी के बाद भी ख़रीदने की संख्या: 0 = 100, 1 = 55, 2+ = 15।",
    },
}


@dataclass(frozen=True)
class OrderBehaviourMeta:
    """Client-recorded behavioural signals attached to each manual order."""
    opened_fundamentals: bool = False
    read_news: bool = False
    viewed_chart: bool = False
    watched_before: bool = False
    gate_score: float | None = None          # 0-100 reasoning score from Gate
    gate_verdict: str | None = None          # "sound" | "mixed" | "weak"
    gate_flags: tuple[str, ...] = ()         # e.g. ("tip", "fomo", "fear")


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _lerp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    if x <= x0:
        return y0
    if x >= x1:
        return y1
    return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0)


def _band(score: float) -> Band:
    if score >= 70:
        return "good"
    if score >= 40:
        return "ok"
    return "poor"


def _research_depth(meta: OrderBehaviourMeta) -> float:
    score = (
        (0.35 if meta.opened_fundamentals else 0.0)
        + (0.25 if meta.read_news else 0.0)
        + (0.15 if meta.viewed_chart else 0.0)
        + (0.25 if meta.watched_before else 0.0)
    )
    return min(1.0, score)


def _is_fomo_buy(order: ExecutedOrder, meta: OrderBehaviourMeta, market: MarketData) -> bool:
    if order.reason_tag in ("tip", "rising"):
        return True
    if any(f in ("tip", "fomo", "hype") for f in meta.gate_flags):
        return True
    return get_change_over(market, order.code, order.day, 5) >= 15.0


def _is_fear_sell(order: ExecutedOrder, meta: OrderBehaviourMeta) -> bool:
    return order.reason_tag == "fear" or any(f in ("fear", "panic") for f in meta.gate_flags)


def score_behaviour(
    state: PortfolioState,
    market: MarketData,
    order_meta: list[OrderBehaviourMeta] | None = None,
    stated_crash_reaction: str | None = None,
) -> dict[str, Any]:
    """Compute the complete 9-habit scorecard and weighted Resilience Score."""
    manual_orders = [o for o in state.orders if not o.forced]
    meta_list = list(order_meta or [])
    while len(meta_list) < len(manual_orders):
        meta_list.append(OrderBehaviourMeta())

    paired = list(zip(manual_orders, meta_list))
    buys = [(o, m) for o, m in paired if o.side == "buy"]
    sells = [(o, m) for o, m in paired if o.side == "sell"]

    crash_start, crash_end = market.crash_window
    habits: list[dict[str, Any]] = []

    def add_habit(habit_id: str, raw_score: float, value: Any, detail: dict[str, Any]) -> None:
        s = round(_clamp(raw_score))
        habits.append({
            "id": habit_id,
            "score": s,
            "band": _band(s),
            "weight": HABIT_WEIGHTS[habit_id],
            "value": value,
            "formula": HABIT_FORMULAS[habit_id],
            "detail": detail,
        })

    if buys:
        # 1. Research depth
        depths = [_research_depth(m) for _, m in buys]
        avg_depth = sum(depths) / len(depths)
        add_habit(
            "research",
            avg_depth * 100.0,
            round(avg_depth * 100.0),
            {
                "buys": len(buys),
                "opened_fundamentals": sum(1 for _, m in buys if m.opened_fundamentals),
                "read_news": sum(1 for _, m in buys if m.read_news),
                "viewed_chart": sum(1 for _, m in buys if m.viewed_chart),
                "watched_before": sum(1 for _, m in buys if m.watched_before),
            },
        )

        # 2. Reasoning quality
        scored_buys = [(o, m) for o, m in buys if m.gate_score is not None]
        if scored_buys:
            avg_reason = sum(m.gate_score for _, m in scored_buys if m.gate_score is not None) / len(scored_buys)
            add_habit(
                "reasoning",
                avg_reason,
                round(avg_reason),
                {
                    "checked": len(scored_buys),
                    "sound": sum(1 for _, m in scored_buys if m.gate_verdict == "sound"),
                    "weak": sum(1 for _, m in scored_buys if m.gate_verdict == "weak"),
                },
            )

        # 3. Thinking time (median seconds)
        secs = [min(600, max(0, round(o.think_ms / 1000.0))) for o, _ in buys]
        med_sec = float(median(secs))
        think_score = (
            0.0 if med_sec <= 15
            else _lerp(med_sec, 15, 45, 0, 50) if med_sec <= 45
            else _lerp(med_sec, 45, 120, 50, 100)
        )
        add_habit(
            "think",
            think_score,
            round(med_sec),
            {
                "median_sec": round(med_sec),
                "fastest_sec": min(secs),
                "slowest_sec": max(secs),
                "under_30s": sum(1 for s in secs if s < 30),
            },
        )

        # 4. FOMO control
        fomo_buys = [(o, m) for o, m in buys if _is_fomo_buy(o, m, market)]
        fomo_share = len(fomo_buys) / len(buys)
        fomo_score = 100.0 * (1.0 - min(1.0, fomo_share / 0.5))
        add_habit(
            "fomo",
            fomo_score,
            round(fomo_share * 100.0),
            {
                "fomo_count": len(fomo_buys),
                "total_buys": len(buys),
                "stocks": [o.code for o, _ in fomo_buys[:3]],
            },
        )

        # 5. Concentration
        max_w = state.max_single_stock_weight
        conc_score = _lerp(max_w, 0.25, 0.60, 100.0, 0.0)
        add_habit(
            "concentration",
            conc_score,
            round(max_w * 100.0),
            {
                "max_weight_pct": round(max_w * 100.0, 1),
                "top_stock": state.max_single_stock_code,
            },
        )

        # 9. Pause adherence (buying despite a weak Reasoning Gate warning)
        ignored_weak = sum(1 for _, m in buys if m.gate_verdict == "weak")
        pause_score = 100.0 if ignored_weak == 0 else (55.0 if ignored_weak == 1 else 15.0)
        add_habit(
            "pause",
            pause_score,
            ignored_weak,
            {"bought_after_weak_warning": ignored_weak},
        )

    # 6. Crash panic (only applies if user held shares entering or during the crash window)
    had_buys_before_crash_end = any(o.day <= crash_end for o, _ in buys)
    panic_sells = [
        (o, m) for o, m in sells
        if crash_start <= o.day <= crash_end and _is_fear_sell(o, m)
    ]
    if had_buys_before_crash_end:
        total_bought_qty = sum(o.qty for o, _ in buys if o.day <= crash_end)
        panic_sold_qty = sum(o.qty for o, _ in panic_sells)
        panic_share = min(1.0, panic_sold_qty / max(1, total_bought_qty))
        crash_score = 100.0 * (1.0 - min(1.0, panic_share / 0.5))
        add_habit(
            "crash",
            crash_score,
            round(panic_share * 100.0),
            {
                "panic_sell_count": len(panic_sells),
                "panic_share_pct": round(panic_share * 100.0, 1),
                "crash_window": list(market.crash_window),
            },
        )

    # 7. Leverage discipline (MTF)
    used_mtf = any(o.mtf for o in state.orders)
    if state.margin_calls > 0:
        lev_score = 0.0
        lev_status = "margin_call"
    elif used_mtf:
        lev_score = 45.0
        lev_status = "used_mtf"
    else:
        lev_score = 100.0
        lev_status = "no_mtf"
    add_habit(
        "leverage",
        lev_score,
        lev_status,
        {
            "used_mtf": used_mtf,
            "margin_calls": state.margin_calls,
            "interest_paid": state.total_interest_paid,
        },
    )

    # 8. Churn / Overtrading
    last_buy_day: dict[str, int] = {}
    quick_flips = 0
    for o, _ in paired:
        if o.side == "buy":
            last_buy_day[o.code] = o.day
        elif o.side == "sell" and o.code in last_buy_day and (o.day - last_buy_day[o.code]) <= 2:
            quick_flips += 1
    base_churn = _lerp(len(manual_orders), 8, 24, 100.0, 30.0)
    churn_score = _clamp(base_churn - 15.0 * quick_flips)
    add_habit(
        "churn",
        churn_score,
        len(manual_orders),
        {"manual_orders": len(manual_orders), "quick_flips": quick_flips},
    )

    # Weighted Resilience Score (normalized across applicable habits)
    total_w = sum(h["weight"] for h in habits) or 1.0
    resilience_score = round(sum(h["score"] * h["weight"] for h in habits) / total_w)

    # Compare stated crash reaction (from onboarding) vs actual crash behaviour
    actual_crash = "sold_in_panic" if panic_sells else ("held_steady" if had_buys_before_crash_end else "stayed_in_cash")
    stated_vs_actual = {
        "stated": stated_crash_reaction or "unknown",
        "actual": actual_crash,
        "aligned": (
            (stated_crash_reaction in ("hold", "buy_more") and actual_crash != "sold_in_panic")
            or (stated_crash_reaction == "sell" and actual_crash == "sold_in_panic")
        ) if stated_crash_reaction else None,
    }

    # Collect up to 3 red-flag lessons for flagged stocks the user bought anyway
    triggered_lessons: list[str] = []
    for o, _ in buys:
        for flag in COMPANY_BY_CODE[o.code].fundamentals.red_flags:
            if flag not in triggered_lessons:
                triggered_lessons.append(flag)
    if state.margin_calls > 0 and "mtf_leverage" not in triggered_lessons:
        triggered_lessons.insert(0, "mtf_leverage")

    final_equity = state.equity_value(market, state.day)
    total_return_pct = round(((final_equity - state.starting_cash) / max(1.0, state.starting_cash)) * 100.0, 2)

    return {
        "resilience_score": resilience_score,
        "resilience_band": _band(resilience_score),
        "day": state.day,
        "season_days": market.season_days,
        "portfolio_summary": {
            "starting_cash": state.starting_cash,
            "final_equity": final_equity,
            "cash": state.cash,
            "total_return_pct": total_return_pct,
            "total_interest_paid": state.total_interest_paid,
            "margin_calls": state.margin_calls,
            "manual_orders": len(manual_orders),
            "total_borrowed": state.total_borrowed(),
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
        "habits": habits,
        "stated_vs_actual_crash": stated_vs_actual,
        "lesson_topics": triggered_lessons[:3],
    }
