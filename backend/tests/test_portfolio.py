"""Unit tests for portfolio accounting, lower-circuit locks, MTF margin calls, and risk previews."""

import pytest

from app.market.portfolio import (
    OrderError,
    OrderRequest,
    PortfolioState,
    apply_order,
    preview_order_consequence,
    replay_orders,
)
from app.market.simulator import build_market, get_price


def test_basic_buy_and_sell_updates_cash_and_pnl():
    m = build_market(mode="guided")
    p_buy = get_price(m, "GANGOTRI", 1)
    p_sell = get_price(m, "GANGOTRI", 6)

    orders = [
        OrderRequest(day=1, code="GANGOTRI", side="buy", qty=10, reason_tag="fundamentals"),
        OrderRequest(day=6, code="GANGOTRI", side="sell", qty=10, reason_tag="target"),
    ]
    state = replay_orders(m, starting_cash=100_000.0, orders=orders, as_of_day=6)

    expected_pnl = round((p_sell - p_buy) * 10, 2)
    assert state.holdings == {}
    assert state.cash == pytest.approx(100_000.0 + expected_pnl, abs=0.05)
    assert state.orders[-1].realized_pnl == pytest.approx(expected_pnl, abs=0.05)


def test_lower_circuit_blocks_sell_on_days_8_and_9_then_allows_day_10():
    m = build_market(mode="guided")
    state = PortfolioState(starting_cash=50_000.0, cash=50_000.0, day=1)
    apply_order(state, m, OrderRequest(day=4, code="ROCKINFR", side="buy", qty=100, reason_tag="tip"))

    # Day 8: Rocket Infra is locked in Lower Circuit -> sell MUST fail
    with pytest.raises(OrderError) as exc_day8:
        apply_order(state, m, OrderRequest(day=8, code="ROCKINFR", side="sell", qty=100, reason_tag="fear"))
    assert exc_day8.value.code == "LOWER_CIRCUIT_LOCK"

    # Day 9: Still locked in Lower Circuit -> sell MUST still fail
    with pytest.raises(OrderError) as exc_day9:
        apply_order(state, m, OrderRequest(day=9, code="ROCKINFR", side="sell", qty=100, reason_tag="fear"))
    assert exc_day9.value.code == "LOWER_CIRCUIT_LOCK"

    # Day 10: Reopens -> sell succeeds (at a heavy loss)
    executed = apply_order(state, m, OrderRequest(day=10, code="ROCKINFR", side="sell", qty=100, reason_tag="fear"))
    assert executed.realized_pnl < 0
    assert "ROCKINFR" not in state.holdings


def test_mtf_interest_and_forced_margin_call_during_crash():
    m = build_market(mode="guided")
    # Buy Rocket Infra near the top (Day 6) using 2x MTF leverage
    p6 = get_price(m, "ROCKINFR", 6)
    qty = int((40_000.0 * 2) // p6)  # Uses ~₹40k own cash + ~₹40k borrowed

    orders = [OrderRequest(day=6, code="ROCKINFR", side="buy", qty=qty, mtf=True, reason_tag="rising")]
    state = replay_orders(m, starting_cash=50_000.0, orders=orders, as_of_day=12)

    assert state.total_interest_paid > 0
    assert state.margin_calls >= 1
    assert any(o.forced and o.reason_tag == "margin_call" for o in state.orders)
    assert "ROCKINFR" not in state.holdings


def test_insufficient_cash_is_rejected():
    m = build_market(mode="guided")
    state = PortfolioState(starting_cash=1_000.0, cash=1_000.0, day=1)
    with pytest.raises(OrderError) as exc:
        apply_order(state, m, OrderRequest(day=1, code="CHANDNI", side="buy", qty=10))
    assert exc.value.code == "INSUFFICIENT_CASH"


def test_preview_order_consequence_computes_grounded_risk_numbers():
    m = build_market(mode="guided")
    state = PortfolioState(starting_cash=50_000.0, cash=50_000.0, day=5)
    p5 = get_price(m, "ROCKINFR", 5)

    preview = preview_order_consequence(state, m, code="ROCKINFR", qty=400, day=5, mtf=True)

    assert preview["order_value"] == pytest.approx(p5 * 400, abs=0.05)
    assert preview["own_cash_needed"] == pytest.approx(preview["order_value"] * 0.5, abs=0.05)
    assert preview["margin_call_price"] == pytest.approx(p5 * 0.75, abs=0.05)
    assert "mtf_leverage" in preview["risk_warnings"]
    assert "chasing_5d_run" in preview["risk_warnings"]
    assert "loss_making" in preview["risk_warnings"]
    assert preview["loss_on_2sigma_rupees"] > 0
