"""Small OpenAQ API v3 client with rate-limit handling and retries.

Endpoints used (checked against https://docs.openaq.org):
  GET /v3/locations?coordinates=lat,lon&radius=...   find stations near a point
  GET /v3/locations/{id}/latest                       latest value per sensor
  GET /v3/sensors/{id}/hours?datetime_from=&datetime_to=&limit=&page=
                                                      precomputed hourly averages
Auth: header "X-API-Key". Free tier: 60 requests/minute, 2,000/hour.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

from src import config

logger = logging.getLogger(__name__)


class OpenAQAuthError(RuntimeError):
    """Raised on 401/403 - retrying will not help, the key is wrong or missing."""


class OpenAQClient:
    """Thin wrapper around requests that respects OpenAQ's rate limits."""

    def __init__(
        self,
        api_key: str,
        session: requests.Session | None = None,
        sleep_s: float = config.REQUEST_SLEEP_S,
    ) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Accept": "application/json"})
        self.sleep_s = sleep_s

    # ------------------------------------------------------------------ core
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """GET with timeout, 429 handling and exponential backoff (max 3 retries)."""
        url = f"{config.OPENAQ_BASE_URL}{path}"
        last_error: Exception | None = None
        for attempt in range(config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=config.REQUEST_TIMEOUT_S)
            except requests.RequestException as exc:  # network error, timeout
                last_error = exc
                self._backoff(attempt, f"network error: {exc}")
                continue

            if resp.status_code in (401, 403):
                raise OpenAQAuthError(
                    f"OpenAQ returned {resp.status_code}. Check that OPENAQ_API_KEY is correct."
                )
            if resp.status_code == 429:
                # The reset header tells us how many seconds until the window resets.
                wait = _header_int(resp, "x-ratelimit-reset", default=60) + 1
                logger.warning("Rate limited (429). Waiting %ss before retrying.", wait)
                last_error = requests.HTTPError("429 Too Many Requests")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                last_error = requests.HTTPError(f"server error {resp.status_code}")
                self._backoff(attempt, f"server error {resp.status_code}")
                continue

            resp.raise_for_status()  # 404/422 etc. are bugs in our request: fail fast
            self._respect_rate_limit(resp)
            return resp.json()

        raise RuntimeError(f"GET {path} failed after {config.MAX_RETRIES} retries: {last_error}")

    def _backoff(self, attempt: int, reason: str) -> None:
        if attempt >= config.MAX_RETRIES:
            return
        wait = config.BACKOFF_BASE_S * (2**attempt)
        logger.warning("%s - retry %d/%d in %.0fs", reason, attempt + 1, config.MAX_RETRIES, wait)
        time.sleep(wait)

    def _respect_rate_limit(self, resp: requests.Response) -> None:
        """Pause between calls, and wait out the window if we are about to hit the limit."""
        remaining = _header_int(resp, "x-ratelimit-remaining", default=None)
        if remaining is not None and remaining <= 1:
            wait = _header_int(resp, "x-ratelimit-reset", default=60) + 1
            logger.info("Rate-limit window almost used up; sleeping %ss.", wait)
            time.sleep(wait)
        else:
            time.sleep(self.sleep_s)

    # ------------------------------------------------------------- endpoints
    def find_locations(
        self,
        lat: float = config.DELHI_CENTER[0],
        lon: float = config.DELHI_CENTER[1],
        radius_m: int = config.SEARCH_RADIUS_M,
    ) -> list[dict]:
        """Stationary locations within radius_m that measure PM2.5 (parameter id 2)."""
        data = self._get(
            "/locations",
            {
                "coordinates": f"{lat:.4f},{lon:.4f}",  # API truncates beyond 4 decimals
                "radius": radius_m,
                "parameters_id": 2,
                "limit": 1000,
            },
        )
        return data.get("results", [])

    def get_latest(self, location_id: int) -> list[dict]:
        """Latest measurement of every sensor at a location."""
        return self._get(f"/locations/{location_id}/latest").get("results", [])

    def get_hours(self, sensor_id: int, start: datetime, end: datetime) -> list[dict]:
        """All hourly averages for one sensor between start and end, following pages."""
        results: list[dict] = []
        page = 1
        while True:
            data = self._get(
                f"/sensors/{sensor_id}/hours",
                {
                    "datetime_from": _iso_utc(start),
                    "datetime_to": _iso_utc(end),
                    "limit": config.OPENAQ_PAGE_LIMIT,
                    "page": page,
                },
            )
            batch = data.get("results", [])
            results.extend(batch)
            if len(batch) < config.OPENAQ_PAGE_LIMIT:
                return results
            page += 1


# ---------------------------------------------------------------- helpers
def _header_int(resp: requests.Response, name: str, default: int | None) -> int | None:
    try:
        return int(float(resp.headers.get(name)))
    except (TypeError, ValueError):
        return default


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_ugm3(value: float | None, parameter: str, units: str | None) -> float | None:
    """Convert gas readings reported in ppm/ppb to µg/m³ so all rows share one unit."""
    if value is None:
        return None
    unit = (units or "").lower().replace(" ", "")
    if unit in ("ppm", "ppb") and parameter in config.MOLECULAR_WEIGHT:
        ppb = value * 1000 if unit == "ppm" else value
        return ppb * config.MOLECULAR_WEIGHT[parameter] / config.MOLAR_VOLUME_L
    return value


def parse_hours(results: list[dict], parameter: str, units: str | None) -> dict[datetime, float | None]:
    """Turn /hours results into {hour_start_in_IST: value_in_µg/m³}.

    We label each hour by its START time (period.datetimeFrom), which matches
    how CPCB labels hourly data ("From Date").
    """
    out: dict[datetime, float | None] = {}
    for item in results:
        period = item.get("period") or {}
        start = (period.get("datetimeFrom") or {}).get("utc")
        if not start:
            continue
        ts = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(config.IST)
        out[ts] = to_ugm3(item.get("value"), parameter, units)
    return out
