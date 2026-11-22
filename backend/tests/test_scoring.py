"""Unit tests for the 9-habit behavioural scoring model using realistic investor personas."""

from app.market.portfolio import OrderRequest, replay_orders
from app.market.simulator import build_market
from app.scoring.habits import OrderBehaviourMeta, score_behaviour


def test_disciplined_researcher_scores_high():
    m = build_market(mode="guided")
    orders = [
        OrderRequest(day=2, code="GANGOTRI", side="buy", qty=30, reason_tag="fundamentals", think_ms=135_000),
        OrderRequest(day=4, code="CHANDNI", side="buy", qty=15, reason_tag="fundamentals", think_ms=150_000),
        OrderRequest(day=6, code="SAHYURJA", side="buy", qty=100, reason_tag="fundamentals", think_ms=125_000),
    ]
    metas = [
        OrderBehaviourMeta(
            opened_fundamentals=True, read_news=True, viewed_chart=True, watched_before=True,
            gate_score=88, gate_verdict="sound",
        ),
        OrderBehaviourMeta(
            opened_fundamentals=True, read_news=True, viewed_chart=True, watched_before=True,
            gate_score=92, gate_verdict="sound",
        ),
        OrderBehaviourMeta(
            opened_fundamentals=True, read_news=True, viewed_chart=True, watched_before=True,
            gate_score=85, gate_verdict="sound",
        ),
    ]

    state = replay_orders(m, starting_cash=100_000.0, orders=orders, as_of_day=21)
    report = score_behaviour(state, m, order_meta=metas, stated_crash_reaction="hold")

    assert report["resilience_score"] >= 85
    assert report["resilience_band"] == "good"
    assert report["stated_vs_actual_crash"]["aligned"] is True
    assert report["lesson_topics"] == []


def test_impulsive_fomo_trader_scores_low_and_triggers_lessons():
    m = build_market(mode="guided")
    # Buys Rocket Infra on a Day-5 rumour with 2x MTF in 10 seconds, then panic-sells Navyug Bank in crash
    orders = [
        OrderRequest(day=5, code="ROCKINFR", side="buy", qty=900, mtf=True, reason_tag="tip", think_ms=10_000),
        OrderRequest(day=6, code="NAVYUGBK", side="buy", qty=100, reason_tag="rising", think_ms=12_000),
        OrderRequest(day=9, code="NAVYUGBK", side="sell", qty=100, reason_tag="fear", think_ms=8_000),
    ]
    metas = [
        OrderBehaviourMeta(gate_score=18, gate_verdict="weak", gate_flags=("tip", "fomo")),
        OrderBehaviourMeta(gate_score=25, gate_verdict="weak", gate_flags=("fomo",)),
        OrderBehaviourMeta(gate_flags=("fear",)),
    ]

    state = replay_orders(m, starting_cash=100_000.0, orders=orders, as_of_day=21)
    report = score_behaviour(state, m, order_meta=metas, stated_crash_reaction="hold")

    habits_by_id = {h["id"]: h for h in report["habits"]}
    assert report["resilience_score"] < 40
    assert report["resilience_band"] == "poor"
    assert habits_by_id["think"]["score"] == 0
    assert habits_by_id["fomo"]["score"] == 0
    assert habits_by_id["pause"]["score"] == 15
    assert habits_by_id["leverage"]["score"] == 0  # Margin call triggered on Rocket Infra
    assert report["stated_vs_actual_crash"]["aligned"] is False
    assert "mtf_leverage" in report["lesson_topics"]
    assert "loss_making" in report["lesson_topics"]


def test_quick_flip_penalizes_churn_score():
    m = build_market(mode="guided")
    orders = [
        OrderRequest(day=1, code="SAHYURJA", side="buy", qty=20, reason_tag="other", think_ms=60_000),
        OrderRequest(day=2, code="SAHYURJA", side="sell", qty=20, reason_tag="other", think_ms=60_000),
        OrderRequest(day=3, code="GANGOTRI", side="buy", qty=10, reason_tag="other", think_ms=60_000),
        OrderRequest(day=4, code="GANGOTRI", side="sell", qty=10, reason_tag="other", think_ms=60_000),
    ]
    state = replay_orders(m, starting_cash=100_000.0, orders=orders, as_of_day=10)
    report = score_behaviour(state, m)
    churn = next(h for h in report["habits"] if h["id"] == "churn")
    assert churn["detail"]["quick_flips"] == 2
    assert churn["score"] == 70
