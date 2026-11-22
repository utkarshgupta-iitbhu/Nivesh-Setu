"""Unit tests for the 21-day seeded market simulator."""

import pytest

from app.market.catalog import COMPANIES, PRE_DAYS, SEASON_DAYS
from app.market.simulator import (
    build_market,
    get_avg_volume,
    get_circuit,
    get_history,
    get_price,
    get_quote,
    get_realized_volatility,
    snapshot_for_day,
)


def test_guided_market_is_21_days_and_deterministic():
    m1 = build_market(mode="guided")
    m2 = build_market(mode="guided")

    assert m1.season_days == 21
    assert SEASON_DAYS == 21
    assert len(m1.indices["sim50"]) == 22  # Day 0 through Day 21

    for c in COMPANIES:
        assert m1.series[c.code].close == m2.series[c.code].close
        assert len(m1.series[c.code].close) == PRE_DAYS + 1 + 21


def test_rocket_infra_pumps_then_locks_lower_circuit_on_days_8_and_9():
    m = build_market(mode="guided")
    day0 = get_price(m, "ROCKINFR", 0)
    day6 = get_price(m, "ROCKINFR", 6)

    # Rumour pump lifts Rocket Infra significantly by Day 6
    assert day6 > day0 * 1.35
    assert get_circuit(m, "ROCKINFR", 8) == "LC"
    assert get_circuit(m, "ROCKINFR", 9) == "LC"
    # Reopens for trading on Day 10
    assert get_circuit(m, "ROCKINFR", 10) is None


def test_volume_spikes_during_rumour_pump():
    m = build_market(mode="guided")
    day5_quote = get_quote(m, "ROCKINFR", 5)
    assert day5_quote["volume"] > day5_quote["avg_volume_20d"] * 2.0


def test_snapshot_never_leaks_future_days():
    m = build_market(mode="guided")
    snap = snapshot_for_day(m, day=5)

    assert snap["day"] == 5
    # All visible news must be <= Day 5
    assert all(item["day"] <= 5 for item in snap["news"])
    # Every stock's chart history must end on Day 5
    for st in snap["stocks"]:
        assert st["history"][-1]["day"] == 5
        assert max(p["day"] for p in st["history"]) == 5


def test_practice_mode_is_reproducible_per_seed_and_varies_across_seeds():
    p42_a = build_market(mode="practice", seed=42)
    p42_b = build_market(mode="practice", seed=42)
    p99 = build_market(mode="practice", seed=99)

    assert p42_a.series["SAHYURJA"].close == p42_b.series["SAHYURJA"].close
    assert p42_a.series["SAHYURJA"].close != p99.series["SAHYURJA"].close

    # Practice mode always schedules a 2-day lower-circuit trap on the pumped stock
    pumped = p42_a.pumped_stock
    lc_days = [d for d in range(1, 22) if get_circuit(p42_a, pumped, d) == "LC"]
    assert len(lc_days) >= 2


def test_volatility_increases_during_crash():
    m = build_market(mode="guided")
    calm_vol = get_realized_volatility(m, "NAVYUGBK", day=4, window=10)
    crash_vol = get_realized_volatility(m, "NAVYUGBK", day=12, window=10)
    assert crash_vol > calm_vol


def test_out_of_bounds_day_raises():
    m = build_market(mode="guided")
    with pytest.raises(ValueError):
        get_price(m, "SAHYURJA", 22)
    with pytest.raises(ValueError):
        get_history(m, "SAHYURJA", -1)


def test_snapshot_exposes_dynamic_regime_and_coach_event():
    g = build_market(mode="guided")
    assert snapshot_for_day(g, 1)["coach_event"] == "welcome"
    assert snapshot_for_day(g, 8)["coach_event"] == "crash_start"
    assert snapshot_for_day(g, 8)["regime"] == "CRASH"
    assert snapshot_for_day(g, 18)["coach_event"] is None

    p = build_market(mode="practice", seed=77)
    crash_day = p.crash_window[0]
    assert snapshot_for_day(p, crash_day)["coach_event"] == "crash_start"
    assert snapshot_for_day(p, crash_day)["regime"] == "CRASH"
