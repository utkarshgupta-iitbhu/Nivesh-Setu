"""Unit tests for stateless notification alert evaluation."""

from app.market.alerts import AlertSpec, evaluate_alerts
from app.market.simulator import build_market


def test_volume_spike_alert_fires_on_rocket_infra_rumour_day():
    m = build_market(mode="guided")
    alerts = [AlertSpec(id="a1", code="ROCKINFR", rule="volume_spike_2x")]
    fired = evaluate_alerts(m, alerts, day=5)
    assert len(fired) == 1
    assert fired[0]["id"] == "a1"
    assert "volume spiked" in fired[0]["summary"]["en"]


def test_day_drop_alert_fires_on_crash_day():
    m = build_market(mode="guided")
    alerts = [AlertSpec(id="a2", code="ROCKINFR", rule="day_change_pct_below", threshold=5.0)]
    fired = evaluate_alerts(m, alerts, day=8)
    assert len(fired) == 1
    assert fired[0]["code"] == "ROCKINFR"
    assert "dropped" in fired[0]["summary"]["en"]
