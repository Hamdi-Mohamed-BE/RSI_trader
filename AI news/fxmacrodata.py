from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests


EVENT_INDICATORS = {
    "NFP": "non_farm_payrolls",
    "CPI": "inflation",
    "FOMC": "policy_rate",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("FXMacroData timestamps must include a timezone.")
    return value.astimezone(timezone.utc)


def _epoch(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _numeric(row: dict[str, Any], event: str) -> float | None:
    key = "change" if event == "NFP" and row.get("change") is not None else "val"
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return None


class FXMacroDataClient:
    """Small REST adapter for the data exposed by the FXMacroData MCP server."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.fxmacrodata.com",
        timeout: float = 20.0,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self._cache: dict[tuple[str, tuple[tuple[str, object], ...]], dict] = {}

    @classmethod
    def from_env(cls) -> "FXMacroDataClient":
        return cls(
            api_key=os.getenv("FXMACRODATA_API_KEY"),
            base_url=os.getenv(
                "FXMACRODATA_BASE_URL",
                "https://api.fxmacrodata.com",
            ),
        )

    def _request(self, path: str, **params: object) -> dict:
        clean = {key: value for key, value in params.items() if value is not None}
        if self.api_key:
            clean["api_key"] = self.api_key
        cache_key = (path, tuple(sorted(clean.items())))
        if cache_key in self._cache:
            return self._cache[cache_key]
        response = self.session.get(
            f"{self.base_url}{path}",
            params=clean,
            timeout=self.timeout,
            headers={"Accept": "application/json", "Accept-Encoding": "gzip"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("FXMacroData returned a non-object response.")
        self._cache[cache_key] = payload
        return payload

    def announcements(self, event: str, *, limit: int = 100) -> dict:
        normalized = event.upper()
        indicator = EVENT_INDICATORS[normalized]
        params = {"limit": limit}
        if normalized in {"NFP", "CPI"}:
            params["revisions"] = "all"
        try:
            return self._request(
                f"/v1/announcements/usd/{indicator}",
                **params,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if "revisions" not in params or status not in {400, 401, 403}:
                raise
            return self._request(
                f"/v1/announcements/usd/{indicator}",
                limit=limit,
            )

    def calendar(self, event: str) -> dict:
        indicator = EVENT_INDICATORS[event.upper()]
        return self._request("/v1/calendar/usd", indicator=indicator)

    def predictions(self, event: str, *, limit: int = 100) -> dict:
        indicator = EVENT_INDICATORS[event.upper()]
        return self._request(
            f"/v1/predictions/usd/{indicator}",
            limit=limit,
        )

    @staticmethod
    def _prediction_time(row: dict[str, Any]) -> datetime | None:
        for key in ("known_at", "generated_at", "observed_at", "created_at"):
            value = row.get(key)
            if isinstance(value, (int, float)):
                return _epoch(value)
            if isinstance(value, str) and value:
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    continue
                return _utc(parsed)
        return None

    def _stored_forecast(
        self,
        event: str,
        announcement_id: str | None,
        cutoff: datetime,
    ) -> dict[str, Any] | None:
        if not self.api_key or not announcement_id:
            return None
        try:
            payload = self.predictions(event)
        except (requests.RequestException, ValueError):
            return None
        candidates: list[tuple[datetime, dict[str, Any]]] = []
        for group in payload.get("data", []):
            if not isinstance(group, dict) or group.get("announcement_id") != announcement_id:
                continue
            for row in group.get("predictions", []):
                if not isinstance(row, dict):
                    continue
                provenance = row.get("provenance") or {}
                capture_mode = provenance.get("capture_mode")
                known_at = self._prediction_time(row)
                if capture_mode != "stored_at_generation" or known_at is None:
                    continue
                if known_at <= cutoff:
                    candidates.append((known_at, row))
        if not candidates:
            return None
        known_at, selected = max(candidates, key=lambda item: item[0])
        return {
            "known_at_utc": known_at.isoformat(),
            "predicted_value": selected.get("predicted_value"),
            "prediction_class": selected.get("prediction_class"),
            "prediction_source": selected.get("prediction_source"),
            "capture_mode": "stored_at_generation",
        }

    def context(
        self,
        event: str,
        release_utc: datetime,
        cutoff_utc: datetime,
    ) -> dict[str, Any]:
        event = event.upper()
        if event not in EVENT_INDICATORS:
            return {
                "status": "unsupported",
                "event": event,
                "decision_weight": 0.0,
            }
        release = _utc(release_utc)
        cutoff = _utc(cutoff_utc)
        if cutoff >= release:
            raise ValueError("FXMacroData context cutoff must be before release.")

        try:
            announcements = self.announcements(event)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            return {
                "status": "authentication_required" if status == 401 else "unavailable",
                "event": event,
                "indicator": EVENT_INDICATORS[event],
                "decision_weight": 0.0,
                "error": f"HTTP {status}" if status else type(exc).__name__,
            }
        except (requests.RequestException, ValueError) as exc:
            return {
                "status": "unavailable",
                "event": event,
                "indicator": EVENT_INDICATORS[event],
                "decision_weight": 0.0,
                "error": type(exc).__name__,
            }

        rows = [row for row in announcements.get("data", []) if isinstance(row, dict)]
        timed = [(stamp, row) for row in rows if (stamp := _epoch(row.get("announcement_datetime")))]
        exact = [
            row
            for stamp, row in timed
            if abs((stamp - release).total_seconds()) <= 120
        ]
        known = [
            (stamp, row)
            for stamp, row in timed
            if stamp <= cutoff
        ]
        known.sort(key=lambda item: item[0])
        values = [
            value
            for _, row in known[-6:]
            if (value := _numeric(row, event)) is not None
        ]
        latest_stamp, latest = known[-1] if known else (None, None)

        verification = "verified" if exact else "unavailable"
        verification_source = "historical announcement audit" if exact else None
        try:
            calendar = self.calendar(event)
            scheduled = [
                (stamp, row)
                for row in calendar.get("data", [])
                if isinstance(row, dict)
                and (stamp := _epoch(row.get("announcement_datetime")))
            ]
            if any(abs((stamp - release).total_seconds()) <= 120 for stamp, _ in scheduled):
                verification = "verified"
                verification_source = "official release calendar"
            elif release > datetime.now(timezone.utc) and scheduled:
                verification = "mismatch"
                verification_source = "official release calendar"
        except (requests.RequestException, ValueError):
            pass

        announcement_id = exact[0].get("announcement_id") if exact else None
        forecast = self._stored_forecast(event, announcement_id, cutoff)
        quality = announcements.get("data_quality") or {}
        freemium = announcements.get("freemium_window") or {}
        return {
            "status": "ok",
            "event": event,
            "indicator": EVENT_INDICATORS[event],
            "event_time_verification": verification,
            "event_time_source": verification_source,
            "event_source_url": exact[0].get("source_url") if exact else None,
            "target_actual_excluded": bool(exact),
            "known_release_count": len(known),
            "latest_known_release_utc": latest_stamp.isoformat() if latest_stamp else None,
            "latest_known_value": _numeric(latest, event) if latest else None,
            "recent_known_values": values,
            "recent_change": values[-1] - values[-2] if len(values) >= 2 else None,
            "stored_pre_release_forecast": forecast,
            "forecast_access": "enabled" if self.api_key else "api_key_required",
            "point_in_time_safe": bool(quality.get("point_in_time_safe")),
            "has_assumed_release_times": bool(quality.get("has_assumed_release_times")),
            "official_source": bool(quality.get("is_official")),
            "freemium_cutoff_date": freemium.get("cutoff_date"),
            "decision_weight": 0.0,
            "decision_note": (
                "Lagged official releases and calendar timing are evidence only. "
                "A forecast affects direction only after stored-at-generation history "
                "passes a chronological promotion test."
            ),
        }
