"""Pure-function portfolio accounting, MTF margin calls, lower-circuit enforcement,
and pre-trade consequence analysis.

Why this runs on the server (as well as in tests):
The browser sends the user's starting capital and order history; the server replays
every order against the deterministic market to compute verified ground-truth numbers.
That way, neither the client nor the LLM can invent or tamper with portfolio facts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from .catalog import COMPANY_BY_CODE
from .simulator import (
    MarketData,
    get_change_over,
    get_circuit,
    get_price,
    get_realized_volatility,
)

MTF_DAILY_INTEREST_RATE: float = 0.0005   # 0.05% per day (~18.25% annualized)
MTF_MAINTENANCE_RATIO: float = 0.50       # Forced square-off when equity < 50% of own margin


class OrderError(ValueError):
    """Structured rejection reason when an order violates market or cash rules."""

    def __init__(self, code: str, message_en: str, message_hi: str) -> None:
        super().__init__(message_en)
        self.code = code
        self.message_en = message_en
        self.message_hi = message_hi


@dataclass(frozen=True)
class OrderRequest:
    day: int
    code: str
    side: Literal["buy", "sell"]
    qty: int
    mtf: bool = False                      # 2x margin trading (50% own cash, 50% borrowed)
    reason_tag: str = "other"              # e.g. "fundamentals", "tip", "rising", "fear"
    reason_text: str = ""
    think_ms: int = 0
    is_ato: bool = False                   # Alert Trigger Order (never uses MTF)


@dataclass
class Holding:
    code: str
    qty: int = 0
    avg_cost: float = 0.0
    own_margin: float = 0.0                # User's own cash locked in MTF shares
    borrowed: float = 0.0                  # Loan owed to broker for MTF shares

    @property
    def is_mtf(self) -> bool:
        return self.borrowed > 0.01


@dataclass
class ExecutedOrder:
    day: int
    code: str
    side: Literal["buy", "sell"]
    qty: int
    price: float
    value: float
    mtf: bool = False
    forced: bool = False                   # True for automatic MTF margin-call square-offs
    is_ato: bool = False
    reason_tag: str = "other"
    reason_text: str = ""
    think_ms: int = 0
    realized_pnl: float = 0.0


@dataclass
class PortfolioState:
    starting_cash: float
    cash: float
    day: int = 1
    holdings: dict[str, Holding] = field(default_factory=dict)
    orders: list[ExecutedOrder] = field(default_factory=list)
    total_interest_paid: float = 0.0
    margin_calls: int = 0
    max_single_stock_weight: float = 0.0
    max_single_stock_code: str | None = None

    def equity_value(self, market: MarketData, day: int | None = None) -> float:
        """Total net worth = free cash + market value of holdings - borrowed MTF loan."""
        d = self.day if day is None else day
        holdings_net = 0.0
        for code, h in self.holdings.items():
            if h.qty > 0:
                mkt_val = h.qty * get_price(market, code, d)
                holdings_net += mkt_val - h.borrowed
        return round(self.cash + holdings_net, 2)

    def holdings_market_value(self, market: MarketData, day: int | None = None) -> float:
        d = self.day if day is None else day
        return round(
            sum(h.qty * get_price(market, code, d) for code, h in self.holdings.items() if h.qty > 0),
            2,
        )

    def total_borrowed(self) -> float:
        return round(sum(h.borrowed for h in self.holdings.values() if h.qty > 0), 2)

    def position_weight(self, market: MarketData, code: str, day: int | None = None) -> float:
        """Share of total net worth currently exposed to `code` (0.0 to >1.0 if leveraged)."""
        d = self.day if day is None else day
        eq = self.equity_value(market, d)
        h = self.holdings.get(code)
        if not h or h.qty <= 0 or eq <= 0:
            return 0.0
        return (h.qty * get_price(market, code, d)) / eq


def _update_max_concentration(state: PortfolioState, market: MarketData, day: int) -> None:
    eq = state.equity_value(market, day)
    if eq <= 0:
        return
    for code, h in state.holdings.items():
        if h.qty <= 0:
            continue
        w = (h.qty * get_price(market, code, day)) / eq
        if w > state.max_single_stock_weight:
            state.max_single_stock_weight = w
            state.max_single_stock_code = code


def _apply_daily_mtf_checks(state: PortfolioState, market: MarketData, day: int) -> None:
    """Accrue daily MTF interest and execute forced margin calls if equity < 50% of own margin."""
    for code in list(state.holdings.keys()):
        h = state.holdings[code]
        if h.qty <= 0 or h.borrowed <= 0:
            continue

        # 1. Daily interest adds to the borrowed amount
        interest = round(h.borrowed * MTF_DAILY_INTEREST_RATE, 2)
        h.borrowed = round(h.borrowed + interest, 2)
        state.total_interest_paid = round(state.total_interest_paid + interest, 2)

        # 2. Check maintenance margin at today's price
        price = get_price(market, code, day)
        mkt_val = h.qty * price
        position_equity = mkt_val - h.borrowed

        if position_equity < h.own_margin * MTF_MAINTENANCE_RATIO:
            # Forced square-off (margin call)
            proceeds_after_loan = max(0.0, mkt_val - h.borrowed)
            cost_basis = h.qty * h.avg_cost
            realized_pnl = round(mkt_val - cost_basis, 2)
            state.cash = round(state.cash + proceeds_after_loan, 2)
            state.margin_calls += 1
            state.orders.append(
                ExecutedOrder(
                    day=day,
                    code=code,
                    side="sell",
                    qty=h.qty,
                    price=price,
                    value=round(mkt_val, 2),
                    mtf=True,
                    forced=True,
                    reason_tag="margin_call",
                    reason_text="Automatic MTF margin call square-off",
                    realized_pnl=realized_pnl,
                )
            )
            del state.holdings[code]


def apply_order(state: PortfolioState, market: MarketData, req: OrderRequest) -> ExecutedOrder:
    """Validate and apply a single buy or sell order onto `state`."""
    if req.code not in COMPANY_BY_CODE:
        raise OrderError("UNKNOWN_STOCK", f"Unknown stock: {req.code}", f"अज्ञात शेयर: {req.code}")
    if req.qty <= 0:
        raise OrderError("INVALID_QTY", "Quantity must be at least 1 share.", "मात्रा कम से कम 1 शेयर होनी चाहिए।")
    if req.day < state.day or req.day > market.season_days:
        raise OrderError("INVALID_DAY", f"Invalid order day: {req.day}", f"अमान्य दिन: {req.day}")

    # Advance days cleanly so daily MTF interest & margin calls trigger in order
    while state.day < req.day:
        state.day += 1
        _apply_daily_mtf_checks(state, market, state.day)
        _update_max_concentration(state, market, state.day)

    price = get_price(market, req.code, req.day)
    circuit = get_circuit(market, req.code, req.day)
    value = round(price * req.qty, 2)

    if req.side == "buy":
        if circuit == "UC":
            raise OrderError(
                "UPPER_CIRCUIT_LOCK",
                f"{req.code} is locked at Upper Circuit today — no sellers available.",
                f"{req.code} आज अपर सर्किट में लॉक है — कोई बेचने वाला उपलब्ध नहीं।",
            )
        use_mtf = req.mtf and not req.is_ato
        own_needed = round(value * 0.5, 2) if use_mtf else value
        borrowed_amt = round(value - own_needed, 2) if use_mtf else 0.0

        if own_needed > state.cash + 0.01:
            raise OrderError(
                "INSUFFICIENT_CASH",
                f"Need ₹{own_needed:,.2f} cash, but only ₹{state.cash:,.2f} available.",
                f"₹{own_needed:,.2f} नक़द चाहिए, पर केवल ₹{state.cash:,.2f} उपलब्ध हैं।",
            )

        state.cash = round(max(0.0, state.cash - own_needed), 2)
        h = state.holdings.get(req.code)
        if not h:
            h = Holding(code=req.code)
            state.holdings[req.code] = h

        total_cost = h.qty * h.avg_cost + value
        h.qty += req.qty
        h.avg_cost = round(total_cost / h.qty, 4)
        if use_mtf:
            h.own_margin = round(h.own_margin + own_needed, 2)
            h.borrowed = round(h.borrowed + borrowed_amt, 2)

        executed = ExecutedOrder(
            day=req.day,
            code=req.code,
            side="buy",
            qty=req.qty,
            price=price,
            value=value,
            mtf=use_mtf,
            is_ato=req.is_ato,
            reason_tag=req.reason_tag,
            reason_text=req.reason_text,
            think_ms=req.think_ms,
        )
        state.orders.append(executed)
        _update_max_concentration(state, market, req.day)
        return executed

    # ── Sell Order ────────────────────────────────────────────────────────────
    if circuit == "LC":
        raise OrderError(
            "LOWER_CIRCUIT_LOCK",
            f"{req.code} is locked in Lower Circuit today — zero buyers. This is how pump-and-dump traps lock investors in.",
            f"{req.code} आज लोअर सर्किट में लॉक है — कोई ख़रीदार नहीं। पंप-एंड-डंप ठगी में निवेशक ऐसे ही फँसते हैं।",
        )

    h = state.holdings.get(req.code)
    if not h or h.qty < req.qty:
        owned = h.qty if h else 0
        raise OrderError(
            "INSUFFICIENT_SHARES",
            f"Cannot sell {req.qty} shares of {req.code}; you only hold {owned}.",
            f"{req.code} के {req.qty} शेयर नहीं बेच सकते; आपके पास केवल {owned} हैं।",
        )

    sell_ratio = req.qty / h.qty
    loan_repaid = round(h.borrowed * sell_ratio, 2)
    margin_released = round(h.own_margin * sell_ratio, 2)
    realized_pnl = round((price - h.avg_cost) * req.qty, 2)

    proceeds = round(value - loan_repaid, 2)
    state.cash = round(state.cash + proceeds, 2)
    h.qty -= req.qty
    h.borrowed = round(max(0.0, h.borrowed - loan_repaid), 2)
    h.own_margin = round(max(0.0, h.own_margin - margin_released), 2)
    if h.qty == 0:
        del state.holdings[req.code]

    executed = ExecutedOrder(
        day=req.day,
        code=req.code,
        side="sell",
        qty=req.qty,
        price=price,
        value=value,
        mtf=loan_repaid > 0,
        is_ato=req.is_ato,
        reason_tag=req.reason_tag,
        reason_text=req.reason_text,
        think_ms=req.think_ms,
        realized_pnl=realized_pnl,
    )
    state.orders.append(executed)
    _update_max_concentration(state, market, req.day)
    return executed


def replay_orders(
    market: MarketData,
    starting_cash: float,
    orders: list[OrderRequest],
    as_of_day: int,
) -> PortfolioState:
    """Deterministically replay a full order history up to `as_of_day`."""
    state = PortfolioState(starting_cash=starting_cash, cash=round(starting_cash, 2), day=1)
    for req in sorted(orders, key=lambda o: o.day):
        if req.day <= as_of_day:
            apply_order(state, market, req)

    # Advance through remaining days up to `as_of_day` for MTF interest & margin calls
    while state.day < as_of_day:
        state.day += 1
        _apply_daily_mtf_checks(state, market, state.day)
        _update_max_concentration(state, market, state.day)

    return state


def preview_order_consequence(
    state: PortfolioState,
    market: MarketData,
    code: str,
    qty: int,
    day: int,
    mtf: bool = False,
) -> dict:
    """Compute concrete, quantitative rupee consequences BEFORE the user confirms a buy.

    Used by the Reasoning Gate so the user sees honest risk numbers grounded in
    this stock's actual volatility, debt/red flags, and portfolio concentration.
    """
    company = COMPANY_BY_CODE[code]
    price = get_price(market, code, day)
    order_value = round(price * qty, 2)
    own_cash_needed = round(order_value * 0.5, 2) if mtf else order_value
    borrowed = round(order_value - own_cash_needed, 2) if mtf else 0.0

    current_eq = max(1.0, state.equity_value(market, day))
    existing_val = (state.holdings[code].qty * price) if code in state.holdings else 0.0
    post_trade_weight_pct = round(((existing_val + order_value) / current_eq) * 100.0, 1)

    # Volatility-based 5-day 2-sigma downside estimate (sqrt(5) * 2 * daily_vol)
    daily_vol_pct = get_realized_volatility(market, code, day, window=20)
    two_sigma_5d_drop_pct = round(min(60.0, 2.0 * math.sqrt(5.0) * daily_vol_pct), 1)
    loss_on_2sigma = round(order_value * (two_sigma_5d_drop_pct / 100.0), 2)
    loss_on_30pct_crash = round(order_value * 0.30, 2)

    # Exact MTF margin-call trigger price:
    # Margin call happens when (qty * P_call - borrowed) < 0.5 * own_cash_needed
    # => P_call = (borrowed + 0.5 * own_cash_needed) / qty = 0.75 * price (a 25% drop!)
    margin_call_price = round(price * 0.75, 2) if mtf else None
    margin_call_drop_pct = 25.0 if mtf else None

    change_5d_pct = round(get_change_over(market, code, day, 5), 2)

    risk_warnings: list[str] = list(company.fundamentals.red_flags)
    if post_trade_weight_pct >= 35.0:
        risk_warnings.append("high_concentration")
    if change_5d_pct >= 15.0:
        risk_warnings.append("chasing_5d_run")
    if mtf:
        risk_warnings.append("mtf_leverage")

    return {
        "code": code,
        "day": day,
        "price": price,
        "qty": qty,
        "order_value": order_value,
        "own_cash_needed": own_cash_needed,
        "borrowed": borrowed,
        "post_trade_weight_pct": post_trade_weight_pct,
        "change_5d_pct": change_5d_pct,
        "daily_volatility_pct": round(daily_vol_pct, 2),
        "two_sigma_5d_drop_pct": two_sigma_5d_drop_pct,
        "loss_on_2sigma_rupees": loss_on_2sigma,
        "loss_on_30pct_crash_rupees": loss_on_30pct_crash,
        "margin_call_price": margin_call_price,
        "margin_call_drop_pct": margin_call_drop_pct,
        "risk_warnings": risk_warnings,
    }
