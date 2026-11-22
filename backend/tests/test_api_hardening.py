"""Unit tests for backend hardening: rate limiting, upload bounds, and schema validation."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas import AlertEvaluateRequest, OrderPayload, ScoreReportRequest
from app.security import MAX_AUDIO_UPLOAD_BYTES, SlidingWindowRateLimiter


def test_rate_limiter_blocks_after_max_requests():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    limiter.check("127.0.0.1")
    limiter.check("127.0.0.1")
    limiter.check("127.0.0.1")

    with pytest.raises(HTTPException) as exc:
        limiter.check("127.0.0.1")
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "RATE_LIMITED"

    # Different IP is unaffected
    limiter.check("10.0.0.2")


def test_order_list_length_cap_enforced():
    too_many = [
        OrderPayload(day=1, code="SAHYURJA", side="buy", qty=1)
        for _ in range(201)
    ]
    with pytest.raises(ValidationError):
        ScoreReportRequest(orders=too_many)


def test_invalid_day_and_qty_rejected_by_schema():
    with pytest.raises(ValidationError):
        OrderPayload(day=22, code="SAHYURJA", side="buy", qty=1)
    with pytest.raises(ValidationError):
        OrderPayload(day=1, code="SAHYURJA", side="buy", qty=0)


def test_alert_list_cap_enforced():
    too_many = [{"id": f"a{i}", "code": "SAHYURJA", "rule": "volume_spike_2x"} for i in range(51)]
    with pytest.raises(ValidationError):
        AlertEvaluateRequest(day=1, alerts=too_many)


def test_audio_upload_cap_is_4mb():
    assert MAX_AUDIO_UPLOAD_BYTES == 4 * 1024 * 1024
