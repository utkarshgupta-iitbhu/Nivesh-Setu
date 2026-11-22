"""Stateless Notification Alert evaluator (Price, Daily %, 2x Volume Spike, 20-day SMA).

Alerts are strictly informational notifications — they never execute orders
automatically, ensuring 100% alignment between the API contract and the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .catalog import COMPANY_BY_CODE
from .simulator import MarketData, get_avg_volume, get_price, get_quote, get_sma

AlertRule = Literal[
    "price_above",
    "price_below",
    "day_change_pct_above",
    "day_change_pct_below",
    "volume_spike_2x",
    "cross_sma20",
]


@dataclass(frozen=True)
class AlertSpec:
    id: str
    code: str
    rule: AlertRule
    threshold: float = 0.0


def evaluate_alerts(market: MarketData, alerts: list[AlertSpec], day: int) -> list[dict]:
    """Return every notification alert that triggers on `day` (pure & stateless)."""
    triggered: list[dict] = []

    for a in alerts:
        if a.code not in COMPANY_BY_CODE:
            continue
        q = get_quote(market, a.code, day)
        price = q["price"]
        prev_price = get_price(market, a.code, day - 1) if day > 0 else price
        sma20 = get_sma(market, a.code, day, 20)
        prev_sma20 = get_sma(market, a.code, day - 1, 20) if day > 0 else sma20
        avg_vol = get_avg_volume(market, a.code, day, 20)

        fired = False
        summary_en = ""
        summary_hi = ""

        if a.rule == "price_above" and price >= a.threshold:
            fired = True
            summary_en = f"{a.code} reached ₹{price:.2f} (above ₹{a.threshold:.2f})."
            summary_hi = f"{a.code} ₹{price:.2f} पर पहुँचा (₹{a.threshold:.2f} से ऊपर)।"
        elif a.rule == "price_below" and price <= a.threshold:
            fired = True
            summary_en = f"{a.code} fell to ₹{price:.2f} (below ₹{a.threshold:.2f})."
            summary_hi = f"{a.code} ₹{price:.2f} पर गिरा (₹{a.threshold:.2f} से नीचे)।"
        elif a.rule == "day_change_pct_above" and q["change_pct"] >= a.threshold:
            fired = True
            summary_en = f"{a.code} jumped {q['change_pct']:.1f}% today."
            summary_hi = f"{a.code} आज {q['change_pct']:.1f}% चढ़ा।"
        elif a.rule == "day_change_pct_below" and q["change_pct"] <= -abs(a.threshold):
            fired = True
            summary_en = f"{a.code} dropped {abs(q['change_pct']):.1f}% today."
            summary_hi = f"{a.code} आज {abs(q['change_pct']):.1f}% गिरा।"
        elif a.rule == "volume_spike_2x" and avg_vol > 0 and q["volume"] >= avg_vol * 2.0:
            ratio = round(q["volume"] / avg_vol, 1)
            fired = True
            summary_en = f"{a.code} volume spiked {ratio}× its 20-day average."
            summary_hi = f"{a.code} का वॉल्यूम 20-दिन के औसत से {ratio}× बढ़ा।"
        elif a.rule == "cross_sma20" and prev_price < prev_sma20 and price >= sma20:
            fired = True
            summary_en = f"{a.code} crossed above its 20-day average (₹{sma20:.2f})."
            summary_hi = f"{a.code} अपने 20-दिन के औसत (₹{sma20:.2f}) से ऊपर निकला।"

        if not fired:
            continue

        triggered.append({
            "id": a.id,
            "code": a.code,
            "day": day,
            "rule": a.rule,
            "price": price,
            "summary": {"en": summary_en, "hi": summary_hi},
        })

    return triggered
