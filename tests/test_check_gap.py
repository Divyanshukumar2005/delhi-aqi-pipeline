"""Tests for the OpenAQ gap diagnostic."""
from __future__ import annotations

from datetime import datetime

from src import check_gap, config


class FakeClient:
    def __init__(self, hours, raw, fail_raw=False):
        self._hours, self._raw, self._fail_raw = hours, raw, fail_raw

    def get_hours(self, sensor_id, start, end):
        return [{"value": v} for v in self._hours]

    def _get(self, path, params=None):
        if self._fail_raw:
            raise RuntimeError("HTTP 404")
        return {"results": [{}] * self._raw}


T0 = datetime(2026, 10, 24, tzinfo=config.IST)


def test_counts_hours_and_raw_and_skips_null_values():
    r = check_gap.count_window(FakeClient([1.0, None, 3.0], 5), 1, T0, T0)
    assert (r["hours"], r["raw"], r["error"]) == (2, 5, None)


def test_one_endpoint_failing_does_not_hide_the_other():
    r = check_gap.count_window(FakeClient([1.0], 0, fail_raw=True), 1, T0, T0)
    assert r["hours"] == 1 and r["raw"] is None and "raw: HTTP 404" in r["error"]


def test_verdicts():
    assert "backfill" in check_gap.verdict([{"hours": 3, "raw": 0}])
    assert "RAW" in check_gap.verdict([{"hours": 0, "raw": 40}])
    assert "NOTHING" in check_gap.verdict([{"hours": 0, "raw": 0}])
