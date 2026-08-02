from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Iterable


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event_name", "message"),
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "event_data", {}))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    root = logging.getLogger()
    if getattr(root, "_asia_breakout_configured", False):
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    resolved_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(resolved_level)

    console = logging.StreamHandler()
    console.setLevel(resolved_level)
    console.setFormatter(
        logging.Formatter(
            "%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    text_file = TimedRotatingFileHandler(
        log_dir / "asia-breakout.log",
        when="midnight",
        backupCount=90,
        encoding="utf-8",
        utc=True,
    )
    text_file.setLevel(resolved_level)
    text_file.setFormatter(
        logging.Formatter(
            "%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s"
        )
    )
    json_file = TimedRotatingFileHandler(
        log_dir / "events.jsonl",
        when="midnight",
        backupCount=90,
        encoding="utf-8",
        utc=True,
    )
    json_file.setLevel(resolved_level)
    json_file.setFormatter(JsonFormatter())
    root.addHandler(console)
    root.addHandler(text_file)
    root.addHandler(json_file)
    root._asia_breakout_configured = True  # type: ignore[attr-defined]


def log_event(
    logger: logging.Logger,
    level: int,
    event_name: str,
    message: str,
    **fields: object,
) -> None:
    logger.log(
        level,
        message,
        extra={"event_name": event_name, "event_data": fields},
    )


def render_table(
    rows: Iterable[dict[str, object]],
    columns: tuple[str, ...],
) -> str:
    items = list(rows)
    if not items:
        return "(no rows)"
    widths = {
        column: max(
            len(column),
            *(len(str(row.get(column, ""))) for row in items),
        )
        for column in columns
    }
    header = " | ".join(column.upper().ljust(widths[column]) for column in columns)
    divider = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns)
        for row in items
    ]
    return "\n".join((header, divider, *body))
