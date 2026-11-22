"""21-Day Seeded Market Simulator (Guided Story + Regime-Switching Practice Mode).

Key quantitative features built for investor resilience training:
1. Deterministic seeded simulation (`random.Random(seed)`): identical inputs always
   reproduce identical prices, volumes, and circuits so the server can replay any
   user's order ledger without trusting client-side numbers.
2. Two modes:
   - "guided": Curated 21-day curriculum (calm -> rumour pump -> crash + LC trap ->
     debt shock -> recovery -> Day-21 graduation).
   - "practice": Regime-switching generator (CALM -> HYPE -> CRASH -> RECOVERY)
     where crash timing and which vulnerable stock gets pumped change per seed.
3. Volatility clustering: during high-stress/crash days, daily volatility scales up
   using a simple EWMA-style multiplier instead of staying unrealistically flat.
4. Real Lower-Circuit ("LC") locks: when a pumped rumour stock collapses, buyers
   disappear for 2 days so the user genuinely feels a pump-and-dump exit trap.
5. Zero future leakage: `snapshot_for_day()` strictly slices all series at `day`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal

from .catalog import (
    COMPANIES,
    COMPANY_BY_CODE,
    GUIDED_CRASH_WINDOW,
    GUIDED_MARKET_RETURNS,
    GUIDED_NEWS,
    INDICES,
    PRE_DAYS,
    SEASON_DAYS,
    BilingualText,
    NewsItem,
)

MarketMode = Literal["guided", "practice"]
CircuitStatus = Literal["LC", "UC"] | None


@dataclass(frozen=True)
class StockSeries:
    code: str
    close: tuple[float, ...]           # Length = PRE_DAYS + 1 + SEASON_DAYS (index PRE_DAYS == Day 0)
    low: tuple[float, ...]
    high: tuple[float, ...]
    volume: tuple[int, ...]
    circuit: tuple[CircuitStatus, ...] # "LC" (Lower Circuit), "UC" (Upper Circuit), or None


@dataclass(frozen=True)
class MarketData:
    mode: MarketMode
    seed: int
    season_days: int
    crash_window: tuple[int, int]
    pumped_stock: str
    series: dict[str, StockSeries]
    indices: dict[str, tuple[float, ...]]  # Length = SEASON_DAYS + 1 (index 0 == Day 0)
    news: tuple[NewsItem, ...]
    regimes: tuple[str, ...]               # Length = SEASON_DAYS (Days 1..21)


def _tick(price: float) -> float:
    """Round to nearest ₹0.05 tick size (like NSE/BSE), floored at ₹0.05."""
    return max(0.05, round(price * 20.0) / 20.0)


def _generate_practice_plan(seed: int) -> tuple[
    tuple[float, ...],
    tuple[str, ...],
    tuple[int, int],
    str,
    dict[str, dict[int, float]],
    dict[str, tuple[int, ...]],
    tuple[NewsItem, ...],
]:
    """Generate a reproducible 21-day regime-switching season for Practice Mode."""
    rng = random.Random(seed * 9973 + 17)

    # Pick a vulnerable company (high debt or loss-making) as this season's rumour trap
    vulnerable = [c.code for c in COMPANIES if "high_debt" in c.fundamentals.red_flags or "loss_making" in c.fundamentals.red_flags]
    pumped_code = rng.choice(vulnerable)
    pumped_name = COMPANY_BY_CODE[pumped_code].name

    # Schedule crash start between Day 7 and Day 11 (lasting 4-5 days)
    crash_start = rng.randint(7, 11)
    crash_len = rng.randint(4, 5)
    crash_end = min(SEASON_DAYS - 4, crash_start + crash_len - 1)
    crash_window = (crash_start, crash_end)

    # Schedule rumour pump right before the crash
    pump_start = max(2, crash_start - 4)
    pump_end = crash_start - 1

    market_returns: list[float] = []
    regimes: list[str] = []
    # EWMA-style volatility state: starts at 1.0, spikes during crash, decays in recovery
    vol_state = 1.0

    for d in range(1, SEASON_DAYS + 1):
        if d < pump_start:
            regime = "CALM"
            vol_state = 0.7 * vol_state + 0.3 * 0.9
            ret = rng.gauss(0.35, 0.55 * vol_state)
        elif pump_start <= d <= pump_end:
            regime = "HYPE"
            vol_state = 0.7 * vol_state + 0.3 * 1.15
            ret = rng.gauss(0.45, 0.70 * vol_state)
        elif crash_start <= d <= crash_end:
            regime = "CRASH"
            vol_state = 0.5 * vol_state + 0.5 * 2.2
            # Mostly sharp negative days with occasional dead-cat bounce
            if d == crash_start + 2:
                ret = rng.gauss(0.8, 0.9)
            else:
                ret = -abs(rng.gauss(2.6, 1.1))
        else:
            regime = "RECOVERY"
            vol_state = 0.75 * vol_state + 0.25 * 1.0
            ret = rng.gauss(0.65, 0.85 * vol_state)

        market_returns.append(round(max(-6.5, min(4.5, ret)), 2))
        regimes.append(regime)

    # Company-specific events & 2-day lower circuit lock when rumour bursts
    events: dict[str, dict[int, float]] = {pumped_code: {}}
    for d in range(pump_start, pump_end + 1):
        events[pumped_code][d] = round(rng.uniform(6.5, 10.0), 1)
    events[pumped_code][crash_start] = -10.0
    events[pumped_code][crash_start + 1] = -10.0
    events[pumped_code][crash_start + 2] = -8.0
    lower_circuits: dict[str, tuple[int, ...]] = {
        pumped_code: (crash_start, crash_start + 1),
    }

    news = (
        NewsItem(1, BilingualText("New 21-day practice season begins. Markets open steady.", "नया 21-दिन का अभ्यास सीज़न शुरू। बाज़ार शांत खुला।")),
        NewsItem(
            pump_start,
            BilingualText(
                f"Unverified rumour: {pumped_name} tipped for a massive order. Heavy social buzz.",
                f"अपुष्ट अफ़वाह: {pumped_name} को बड़े ऑर्डर की चर्चा। सोशल मीडिया पर शोर।",
            ),
            stock_code=pumped_code,
            severity="rumour",
        ),
        NewsItem(
            crash_start,
            BilingualText(
                f"Market sell-off begins! {pumped_name} rumour exposed as false — locked in Lower Circuit.",
                f"बाज़ार में तेज़ गिरावट! {pumped_name} की अफ़वाह झूठी निकली — लोअर सर्किट लॉक।",
            ),
            stock_code=pumped_code,
            severity="crash",
        ),
        NewsItem(
            crash_start + 1,
            BilingualText(
                f"Volatility stays elevated. {pumped_name} still has zero buyers at Lower Circuit.",
                f"उतार-चढ़ाव ऊँचा बना हुआ है। {pumped_name} में आज भी कोई ख़रीदार नहीं।",
            ),
            stock_code=pumped_code,
            severity="crash",
        ),
        NewsItem(
            crash_end + 1,
            BilingualText("Selling pressure eases as patient buyers return.", "बिकवाली का दबाव घटा, धैर्यपूर्ण ख़रीदारी लौटी।"),
        ),
        NewsItem(
            SEASON_DAYS,
            BilingualText("Day 21 complete! Review your Behavioural Resilience Report.", "दिन 21 पूरा! अपनी निवेश लचीलापन रिपोर्ट देखें।"),
        ),
    )

    return tuple(market_returns), tuple(regimes), crash_window, pumped_code, events, lower_circuits, news


def build_market(mode: MarketMode = "guided", seed: int = 42) -> MarketData:
    """Build a complete, deterministic 21-day market dataset."""
    if mode == "guided":
        market_returns = GUIDED_MARKET_RETURNS
        crash_window = GUIDED_CRASH_WINDOW
        pumped_stock = "ROCKINFR"
        events_map = {c.code: c.guided_events for c in COMPANIES}
        lc_map = {c.code: c.guided_lower_circuits for c in COMPANIES}
        news = GUIDED_NEWS
        regimes = tuple(
            "CRASH" if crash_window[0] <= d <= crash_window[1]
            else ("HYPE" if 2 <= d <= 6 else ("RECOVERY" if 13 <= d <= 17 else "CALM"))
            for d in range(1, SEASON_DAYS + 1)
        )
    elif mode == "practice":
        market_returns, regimes, crash_window, pumped_stock, events_map, lc_map, news = (
            _generate_practice_plan(seed)
        )
    else:
        raise ValueError(f"Unsupported market mode: {mode}")

    series: dict[str, StockSeries] = {}

    for idx_k, company in enumerate(COMPANIES):
        # Independent seeded RNG per stock so every company's path is stable
        stock_rng = random.Random((seed if mode == "practice" else 1000) + idx_k * 7919)

        # 1. Build 60 days of pre-season history backwards from Day 0 base_price
        pre_closes = [company.base_price]
        for _ in range(PRE_DAYS):
            pre_ret = (company.drift_pct + stock_rng.gauss(0.0, company.daily_vol_pct * 0.9)) / 100.0
            prev_price = pre_closes[0] / max(0.5, 1.0 + pre_ret)
            pre_closes.insert(0, prev_price)

        closes = list(pre_closes)
        circuits: list[CircuitStatus] = [None] * len(closes)

        # 2. Simulate Days 1..21 with volatility clustering + scripted/regime events
        vol_cluster = 1.0
        comp_events = events_map.get(company.code, {})
        comp_lc_days = set(lc_map.get(company.code, ()))

        for d in range(1, SEASON_DAYS + 1):
            mkt_move = market_returns[d - 1]
            ev_shock = comp_events.get(d, 0.0)

            # Volatility clustering: big market drops or shocks amplify idiosyncratic wobble
            stress = abs(mkt_move) / 2.0 + abs(ev_shock) / 6.0
            vol_cluster = 0.65 * vol_cluster + 0.35 * max(1.0, min(2.4, 1.0 + 0.45 * stress))

            if d in comp_lc_days:
                # Strict Lower Circuit (-10% floor, 0 buyers)
                ret_pct = -10.0
                circuit_flag: CircuitStatus = "LC"
            else:
                noise = stock_rng.gauss(0.0, company.daily_vol_pct * vol_cluster)
                ret_pct = company.beta * mkt_move + noise + ev_shock
                # Cap daily moves at +/- 10% for small caps, +/- 20% for larger caps
                limit = 10.0 if company.fundamentals.mcap_cr < 1000 else 20.0
                if ret_pct >= limit:
                    ret_pct = limit
                    circuit_flag = "UC"
                elif ret_pct <= -limit:
                    ret_pct = -limit
                    circuit_flag = "LC"
                else:
                    circuit_flag = None

            next_close = closes[-1] * (1.0 + ret_pct / 100.0)
            closes.append(next_close)
            circuits.append(circuit_flag)

        rounded_closes = tuple(_tick(p) for p in closes)

        # 3. Derive intraday High, Low, and Volume
        lows: list[float] = []
        highs: list[float] = []
        volumes: list[int] = []

        for i, price in enumerate(rounded_closes):
            prev = rounded_closes[i - 1] if i > 0 else price
            day_num = i - PRE_DAYS
            c_flag = circuits[i]

            if c_flag == "LC":
                # Lower circuit: flat/locked at the day's floor, thin trapped volume
                low_p, high_p = price, price
                vol_mult = 0.25
            else:
                wobble_lo = abs(stock_rng.gauss(0.0, 1.0)) * company.daily_vol_pct * 0.004
                wobble_hi = abs(stock_rng.gauss(0.0, 1.0)) * company.daily_vol_pct * 0.004
                low_p = _tick(min(price, prev) * (1.0 - wobble_lo))
                high_p = _tick(max(price, prev) * (1.0 + wobble_hi))

                pct_move = abs((price - prev) / prev * 100.0) if prev > 0 else 0.0
                ev_mag = abs(comp_events.get(day_num, 0.0)) if day_num > 0 else 0.0
                vol_mult = (0.85 + 0.30 * stock_rng.random()) * (1.0 + 0.35 * pct_move + 0.28 * ev_mag)

            base_vol = company.fundamentals.mcap_cr * 25
            lows.append(low_p)
            highs.append(high_p)
            volumes.append(max(100, int(round(base_vol * vol_mult))))

        series[company.code] = StockSeries(
            code=company.code,
            close=rounded_closes,
            low=tuple(lows),
            high=tuple(highs),
            volume=tuple(volumes),
            circuit=tuple(circuits),
        )

    # 4. Build market indices (SIM 50, SIM Midcap 100)
    indices_series: dict[str, tuple[float, ...]] = {}
    for ix in INDICES:
        vals = [ix.base_value]
        for mkt_move in market_returns:
            vals.append(round(vals[-1] * (1.0 + (ix.beta * mkt_move) / 100.0), 2))
        indices_series[ix.id] = tuple(vals)

    return MarketData(
        mode=mode,
        seed=seed,
        season_days=SEASON_DAYS,
        crash_window=crash_window,
        pumped_stock=pumped_stock,
        series=series,
        indices=indices_series,
        news=news,
        regimes=regimes,
    )


# ── Query Helpers (strictly bounded to `day` so future data never leaks) ─────

def _validate_day(market: MarketData, day: int) -> None:
    if not (0 <= day <= market.season_days):
        raise ValueError(f"Day {day} out of bounds (expected 0..{market.season_days})")


def get_price(market: MarketData, code: str, day: int) -> float:
    _validate_day(market, day)
    return market.series[code].close[PRE_DAYS + day]


def get_circuit(market: MarketData, code: str, day: int) -> CircuitStatus:
    _validate_day(market, day)
    return market.series[code].circuit[PRE_DAYS + day]


def get_quote(market: MarketData, code: str, day: int) -> dict:
    _validate_day(market, day)
    s = market.series[code]
    idx = PRE_DAYS + day
    price = s.close[idx]
    prev = s.close[idx - 1]
    chg = round(price - prev, 2)
    pct = round(((price - prev) / prev) * 100.0, 2) if prev else 0.0
    return {
        "code": code,
        "day": day,
        "price": price,
        "change": chg,
        "change_pct": pct,
        "low": s.low[idx],
        "high": s.high[idx],
        "volume": s.volume[idx],
        "avg_volume_20d": round(get_avg_volume(market, code, day, 20)),
        "sma_20d": round(get_sma(market, code, day, 20), 2),
        "change_5d_pct": round(get_change_over(market, code, day, 5), 2),
        "daily_volatility_pct": round(get_realized_volatility(market, code, day, 20), 2),
        "circuit": s.circuit[idx],
    }


def get_history(market: MarketData, code: str, day: int, lookback: int = 60) -> list[dict]:
    """Return OHLCV history up to `day` (never includes `day + 1`)."""
    _validate_day(market, day)
    s = market.series[code]
    end_idx = PRE_DAYS + day
    start_idx = max(0, end_idx - lookback)
    return [
        {
            "day": i - PRE_DAYS,
            "close": s.close[i],
            "low": s.low[i],
            "high": s.high[i],
            "volume": s.volume[i],
            "circuit": s.circuit[i],
        }
        for i in range(start_idx, end_idx + 1)
    ]


def get_sma(market: MarketData, code: str, day: int, window: int = 20) -> float:
    _validate_day(market, day)
    s = market.series[code]
    end_idx = PRE_DAYS + day
    start_idx = max(0, end_idx - window + 1)
    chunk = s.close[start_idx : end_idx + 1]
    return sum(chunk) / len(chunk)


def get_avg_volume(market: MarketData, code: str, day: int, window: int = 20) -> float:
    _validate_day(market, day)
    s = market.series[code]
    end_idx = PRE_DAYS + day
    start_idx = max(0, end_idx - window)
    chunk = s.volume[start_idx:end_idx] if end_idx > start_idx else s.volume[:1]
    return sum(chunk) / len(chunk)


def get_change_over(market: MarketData, code: str, day: int, days: int = 5) -> float:
    _validate_day(market, day)
    s = market.series[code]
    end_idx = PRE_DAYS + day
    start_idx = max(0, end_idx - days)
    a, b = s.close[start_idx], s.close[end_idx]
    return ((b - a) / a) * 100.0 if a else 0.0


def get_realized_volatility(market: MarketData, code: str, day: int, window: int = 20) -> float:
    """Compute sample standard deviation of daily % returns over the last `window` days."""
    _validate_day(market, day)
    s = market.series[code]
    end_idx = PRE_DAYS + day
    start_idx = max(1, end_idx - window + 1)
    rets = [
        ((s.close[i] - s.close[i - 1]) / s.close[i - 1]) * 100.0
        for i in range(start_idx, end_idx + 1)
        if s.close[i - 1] > 0
    ]
    if len(rets) < 2:
        return COMPANY_BY_CODE[code].daily_vol_pct
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var)


def snapshot_for_day(market: MarketData, day: int) -> dict:
    """Return everything the frontend needs for `day` — strictly zero future leakage."""
    _validate_day(market, day)

    indices_out = []
    for ix in INDICES:
        vals = market.indices[ix.id]
        val = vals[day]
        prev = vals[day - 1] if day > 0 else val
        chg = round(val - prev, 2)
        pct = round(((val - prev) / prev) * 100.0, 2) if prev else 0.0
        indices_out.append({"id": ix.id, "name": ix.name, "value": val, "change": chg, "change_pct": pct})

    stocks_out = []
    for c in COMPANIES:
        q = get_quote(market, c.code, day)
        stocks_out.append({
            "code": c.code,
            "name": c.name,
            "color": c.color,
            "sector": c.sector.to_dict(),
            "about": c.about.to_dict(),
            "fundamentals": {
                "mcap_cr": c.fundamentals.mcap_cr,
                "pe": c.fundamentals.pe,
                "sales_3y_cr": list(c.fundamentals.sales_3y_cr),
                "profit_trend": c.fundamentals.profit_trend,
                "debt_level": c.fundamentals.debt_level,
                "red_flags": list(c.fundamentals.red_flags),
            },
            "quote": q,
            "history": get_history(market, c.code, day, lookback=60),
        })

    visible_news = [n.to_dict() for n in market.news if n.day <= day]

    today_news = [n for n in market.news if n.day == day]
    today_regime = market.regimes[day - 1] if 1 <= day <= len(market.regimes) else "CALM"

    # Determine today's contextual coach event dynamically (works in both Guided & Practice mode)
    coach_event = None
    if day == 1:
        coach_event = "welcome"
    elif day == market.crash_window[0]:
        coach_event = "crash_start"
    elif day == market.crash_window[1] + 1:
        coach_event = "recovery_start"
    elif any(n.severity == "rumour" for n in today_news):
        coach_event = "rumour_buzz"
    elif any(n.stock_code == "VIKISPAT" and n.severity == "crash" for n in today_news):
        coach_event = "debt_shock"

    return {
        "mode": market.mode,
        "seed": market.seed,
        "day": day,
        "season_days": market.season_days,
        "regime": today_regime,
        "coach_event": coach_event,
        "indices": indices_out,
        "stocks": stocks_out,
        "news": visible_news,
    }
