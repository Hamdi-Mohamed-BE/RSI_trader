import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import databento as dbn
import pandas as pd

from ..settings import CACHE_DIR, settings
from .base import MarketDataProvider


class MarketDataError(RuntimeError):
    pass


class DatabentoProvider(MarketDataProvider):
    def __init__(self, dataset: str = "GLBX.MDP3", api_key: str | None = None):
        self.dataset = dataset
        self.api_key = api_key or os.getenv("DATABENTO_API_KEY") or settings.databento_api_key
        if not self.api_key:
            raise MarketDataError(
                "Databento is not configured. Add DATABENTO_API_KEY to .env and restart."
            )
        self.client = dbn.Historical(self.api_key)

    def bars(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        return self._cached_bars(symbol, start, end)

    def trades(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        return self._range(
            symbol, "trades", start, min(self._utc(end), self.available_end("trades"))
        )

    def depth(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        return self._range(
            symbol, "mbp-10", start, min(self._utc(end), self.available_end("mbp-10"))
        )

    def available_end(self, schema: str = "ohlcv-1m") -> datetime:
        path = CACHE_DIR / "databento_availability.json"
        payload = None
        if path.exists() and time.time() - path.stat().st_mtime < 300:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
        if payload is None:
            payload = self.client.metadata.get_dataset_range(self.dataset)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload), encoding="utf-8")
            temporary.replace(path)
        value = payload.get("schema", {}).get(schema, {}).get("end") or payload["end"]
        timestamp = pd.Timestamp(value).floor("min") - pd.Timedelta(minutes=1)
        return timestamp.to_pydatetime()

    def estimated_cost(
        self, symbol: str, schema: str, start: datetime, end: datetime
    ) -> float | None:
        try:
            return float(
                self.client.metadata.get_cost(
                    dataset=self.dataset,
                    symbols=[symbol],
                    schema=schema,
                    stype_in="continuous",
                    start=start,
                    end=end,
                )
            )
        except Exception:
            return None

    def estimated_uncached_bars_cost(
        self, symbol: str, start: datetime, end: datetime
    ) -> float | None:
        request = self._bar_update_range(symbol, start, end)
        if request is None:
            return 0.0
        request_start, request_end = request
        return self.estimated_cost(symbol, "ohlcv-1m", request_start, request_end)

    def _range(
        self, symbol: str, schema: str, start: datetime, end: datetime, cache: bool = True
    ) -> pd.DataFrame:
        path = self._cache_path(symbol, schema, start, end)
        cacheable = cache and schema.startswith("ohlcv") and (end - start).total_seconds() >= 43_200
        if cacheable and path.exists():
            return pd.read_pickle(path)
        try:
            store = self.client.timeseries.get_range(
                dataset=self.dataset,
                symbols=[symbol],
                schema=schema,
                stype_in="continuous",
                start=start,
                end=end,
            )
            frame = store.to_df()
        except Exception as exc:
            raise MarketDataError(f"Databento request failed for {symbol}/{schema}: {exc}") from exc
        if frame.empty:
            raise MarketDataError(f"Databento returned no {schema} data for {symbol}.")
        frame = self._normalize(frame)
        if cacheable:
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_pickle(path)
        return frame

    def _cached_bars(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        start = self._utc(start)
        end = min(self._utc(end), self.available_end("ohlcv-1m"))
        if start >= end:
            raise MarketDataError("The requested bar range has no completed market time.")
        update_range = self._bar_update_range(symbol, start, end)
        if update_range is not None:
            update_start, update_end = update_range
            try:
                fresh = self._range(symbol, "ohlcv-1m", update_start, update_end, cache=False)
            except MarketDataError as exc:
                corrected_end = self._available_end_from_error(str(exc))
                if corrected_end is None or corrected_end <= update_start:
                    raise
                update_end = min(update_end, corrected_end)
                fresh = self._range(symbol, "ohlcv-1m", update_start, update_end, cache=False)
            self._merge_daily_bars(symbol, fresh, update_start, update_end)
            self._write_bar_coverage(symbol, update_start, update_end)
        frames = []
        for day in pd.date_range(
            pd.Timestamp(start).floor("D"), pd.Timestamp(end).ceil("D"), freq="D", inclusive="left"
        ):
            path = self._daily_bar_path(symbol, day)
            if path.exists():
                frames.append(pd.read_pickle(path))
        if not frames:
            raise MarketDataError(f"No cached bars were produced for {symbol}.")
        result = pd.concat(frames)
        result = result[~result.index.duplicated(keep="last")].sort_index()
        return result.loc[(result.index >= start) & (result.index < end)]

    def _bar_update_range(
        self, symbol: str, start: datetime, end: datetime
    ) -> tuple[datetime, datetime] | None:
        start = self._utc(start)
        end = min(self._utc(end), self.available_end("ohlcv-1m"))
        coverage = self._read_bar_coverage(symbol)
        if coverage is not None:
            covered_start, covered_end = coverage
            if start >= covered_start and end <= covered_end:
                return None
            if start >= covered_start:
                return covered_end, end
            return start, end
        needed: list[datetime] = []
        for day in pd.date_range(
            pd.Timestamp(start).floor("D"), pd.Timestamp(end).ceil("D"), freq="D", inclusive="left"
        ):
            day_start = day.to_pydatetime()
            segment_start = max(start, day_start)
            segment_end = min(end, day_start + timedelta(days=1))
            path = self._daily_bar_path(symbol, day)
            if not path.exists():
                needed.append(segment_start)
                continue
            cached = pd.read_pickle(path)
            if cached.empty:
                needed.append(segment_start)
                continue
            next_minute = cached.index[-1].to_pydatetime() + timedelta(minutes=1)
            if next_minute < segment_end:
                needed.append(max(segment_start, next_minute))
        return (min(needed), end) if needed else None

    def _read_bar_coverage(self, symbol: str) -> tuple[datetime, datetime] | None:
        path = self._bar_coverage_path(symbol)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return datetime.fromisoformat(payload["start"]), datetime.fromisoformat(payload["end"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None

    def _write_bar_coverage(self, symbol: str, start: datetime, end: datetime) -> None:
        existing = self._read_bar_coverage(symbol)
        if existing is not None:
            start = min(start, existing[0])
            end = max(end, existing[1])
        path = self._bar_coverage_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"start": start.isoformat(), "end": end.isoformat()}), encoding="utf-8"
        )
        temporary.replace(path)

    def _merge_daily_bars(
        self, symbol: str, fresh: pd.DataFrame, start: datetime, end: datetime
    ) -> None:
        for day in pd.date_range(
            pd.Timestamp(start).floor("D"), pd.Timestamp(end).ceil("D"), freq="D", inclusive="left"
        ):
            day_start = day.to_pydatetime()
            day_end = day_start + timedelta(days=1)
            addition = fresh.loc[(fresh.index >= day_start) & (fresh.index < day_end)]
            path = self._daily_bar_path(symbol, day)
            if path.exists():
                existing = pd.read_pickle(path)
                addition = pd.concat([existing, addition])
            if addition.empty:
                continue
            addition = addition[~addition.index.duplicated(keep="last")].sort_index()
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            addition.to_pickle(temporary)
            temporary.replace(path)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _daily_bar_path(symbol: str, day: pd.Timestamp) -> Path:
        safe_symbol = symbol.replace(".", "_")
        return CACHE_DIR / "ohlcv-1m-daily" / f"{safe_symbol}_{day.strftime('%Y-%m-%d')}.pkl"

    @staticmethod
    def _bar_coverage_path(symbol: str) -> Path:
        safe_symbol = symbol.replace(".", "_")
        return CACHE_DIR / "ohlcv-1m-daily" / f"{safe_symbol}_coverage.json"

    @staticmethod
    def _available_end_from_error(message: str) -> datetime | None:
        match = re.search(r"available (?:range ends at|up to) '([^']+)'", message, re.IGNORECASE)
        if match is None:
            return None
        timestamp = pd.Timestamp(match.group(1)).floor("min") - pd.Timedelta(minutes=1)
        return timestamp.to_pydatetime()

    @staticmethod
    def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        if not isinstance(result.index, pd.DatetimeIndex):
            for candidate in ("ts_event", "ts_recv"):
                if candidate in result.columns:
                    result.index = pd.to_datetime(result[candidate], utc=True)
                    break
        if isinstance(result.index, pd.DatetimeIndex):
            result.index = pd.to_datetime(result.index, utc=True)
            result = result.sort_index()
        return result

    def _cache_path(self, symbol: str, schema: str, start: datetime, end: datetime) -> Path:
        raw = f"{self.dataset}|{symbol}|{schema}|{start.isoformat()}|{end.isoformat()}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        safe_symbol = symbol.replace(".", "_")
        return CACHE_DIR / schema / f"{safe_symbol}_{digest}.pkl"
