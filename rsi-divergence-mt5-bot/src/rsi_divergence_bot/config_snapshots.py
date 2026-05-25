from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .config import AppConfig, save_config


class SnapshotSummary(BaseModel):
    strategy: str
    dry_run: bool
    enabled_symbols: int
    total_symbols: int
    trade_decision_profile: str


class SnapshotEntry(BaseModel):
    slug: str
    name: str
    note: str = ""
    created_at: str
    updated_at: str
    summary: SnapshotSummary


class SnapshotIndex(BaseModel):
    entries: list[SnapshotEntry] = Field(default_factory=list)


def snapshots_dir(config_path: str | Path) -> Path:
    root = Path(config_path).resolve().parent
    path = root / "runtime" / "snapshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path(config_path: str | Path) -> Path:
    return snapshots_dir(config_path) / "index.json"


def _snapshot_path(config_path: str | Path, slug: str) -> Path:
    return snapshots_dir(config_path) / f"{slug}.yaml"


def slugify_snapshot_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Snapshot name is required")
    slug = re.sub(r"[^\w\s-]", "", cleaned.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    if not slug:
        raise ValueError("Snapshot name must contain letters or numbers")
    if slug in {"index", "index.json"}:
        raise ValueError("That snapshot name is reserved")
    return slug[:64].rstrip("-")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_index(config_path: str | Path) -> SnapshotIndex:
    path = _index_path(config_path)
    if not path.exists():
        return SnapshotIndex()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SnapshotIndex.model_validate(payload)


def _save_index(config_path: str | Path, index: SnapshotIndex) -> None:
    path = _index_path(config_path)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(index.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _snapshot_summary(config: AppConfig) -> SnapshotSummary:
    enabled = len(config.enabled_symbols)
    return SnapshotSummary(
        strategy=str(config.bot.strategy),
        dry_run=config.bot.dry_run,
        enabled_symbols=enabled,
        total_symbols=len(config.symbols),
        trade_decision_profile=str(config.bot.trade_decision_profile),
    )


def list_snapshots(config_path: str | Path) -> list[dict]:
    index = _load_index(config_path)
    entries = [entry.model_dump(mode="python") for entry in index.entries]
    entries.sort(key=lambda item: item["updated_at"], reverse=True)
    return entries


def save_snapshot(
    config_path: str | Path,
    *,
    name: str,
    config: AppConfig,
    note: str = "",
) -> dict:
    slug = slugify_snapshot_name(name)
    now = _utc_now()
    index = _load_index(config_path)
    existing = next((entry for entry in index.entries if entry.slug == slug), None)
    created_at = existing.created_at if existing else now

    payload = config.model_dump(mode="python")
    snapshot_path = _snapshot_path(config_path, slug)
    tmp_path = snapshot_path.with_suffix(".yaml.tmp")
    tmp_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    tmp_path.replace(snapshot_path)

    entry = SnapshotEntry(
        slug=slug,
        name=name.strip(),
        note=note.strip(),
        created_at=created_at,
        updated_at=now,
        summary=_snapshot_summary(config),
    )
    index.entries = [item for item in index.entries if item.slug != slug]
    index.entries.append(entry)
    _save_index(config_path, index)
    return entry.model_dump(mode="python")


def load_snapshot(config_path: str | Path, slug: str) -> AppConfig:
    safe_slug = slugify_snapshot_name(slug)
    snapshot_path = _snapshot_path(config_path, safe_slug)
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot not found: {slug}")
    raw = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def delete_snapshot(config_path: str | Path, slug: str) -> None:
    safe_slug = slugify_snapshot_name(slug)
    snapshot_path = _snapshot_path(config_path, safe_slug)
    if snapshot_path.exists():
        snapshot_path.unlink()

    index = _load_index(config_path)
    index.entries = [entry for entry in index.entries if entry.slug != safe_slug]
    _save_index(config_path, index)


def apply_config_snapshot(target: AppConfig, source: AppConfig) -> None:
    validated = AppConfig.model_validate(source.model_dump(mode="python"))
    for field_name in type(target).model_fields:
        setattr(target, field_name, getattr(validated, field_name))


def apply_snapshot(
    config_path: str | Path,
    *,
    slug: str,
    target: AppConfig,
    persist: bool,
) -> AppConfig:
    snapshot = load_snapshot(config_path, slug)
    apply_config_snapshot(target, snapshot)
    if persist:
        save_config(config_path, target)
    return snapshot
