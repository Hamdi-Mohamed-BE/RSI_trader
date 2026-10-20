"""Shared helpers for the Calyx ops monitor (2026-10-20). Read-only: no orders, no MT5 launch, no SET/BAT changes.

Run every tool from AAA EAs/EA store with:  uv run python "../BM Trading Robust Sets 2026-08-04/_Ops Monitor/<tool>.py" ...
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('EA_STORE_DISABLE_MT5', '1')
HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent                                   # BM Trading Robust Sets 2026-08-04
AAA = PACKAGE.parent                                    # AAA EAs
STORE = AAA / 'EA store'
PIPELINE = AAA / 'Calyx Research Pipeline'
for p in (str(STORE), str(PIPELINE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.catalog import PACKAGE_ROOT, get_catalog  # noqa: E402
from robustness import day_block_bootstrap, dependence  # noqa: E402,F401

CACHE = STORE / 'data' / 'evidence-cache' / 'v1' / 'products'
SELECTION = PACKAGE / 'Reviewed EA Deployment 2026-10-06' / 'selection.json'
OUT = HERE / 'output'
NORMAL_TERMINAL = Path(r'C:\Program Files\MetaTrader 5\terminal64.exe')
MAGIC_PATTERN = re.compile(r'(?im)^(?:Inp)?Magic(?:Number|Base)?\s*=\s*(\d+)')
# Magics that the SET files do not show (multi-module EAs / installer-assigned). Sources: 3 Way Gold Deployment README
# (930930100-102) and the 2026-10-09 two-week study's demo mapping for News Pulse / Gold News V9.
EXTRA_MAGICS = {930930101: '3-way-gold', 930930102: '3-way-gold', 861303: 'news-pulse-xau'}


def products() -> dict:
    return {p.slug: p for p in get_catalog()}


def roster() -> dict[str, str]:
    """slug -> phase (live / paused / review) from the shared reviewed selection manifest."""
    sel = json.loads(SELECTION.read_text(encoding='utf-8-sig'))
    return {e['slug']: e['phase'] for e in sel['entries']}


def recommended_mode(p) -> str:
    return 'dynamic' if p.recommended_dynamic_mode else 'safe' if p.recommended_safe_mode else 'standard'


def magic_map() -> dict[int, str]:
    mapping: dict[int, str] = {}
    for p in get_catalog():
        for attr in ('set_source', 'safe_set_source', 'dynamic_set_source'):
            src = getattr(p, attr, None)
            if src and (PACKAGE_ROOT / src).is_file():
                for m in MAGIC_PATTERN.findall((PACKAGE_ROOT / src).read_text(encoding='utf-8-sig', errors='ignore')):
                    mapping.setdefault(int(m), p.slug)
    for m, slug in EXTRA_MAGICS.items():
        mapping.setdefault(m, slug)
    return mapping


def evidence_trades(slug: str, period: str = '5y', mode: str | None = None) -> tuple[list[dict], dict | None, str]:
    """Cached native trades for the product's recommended mode (falls back to standard)."""
    p = products().get(slug)
    modes = [mode] if mode else ([recommended_mode(p)] if p else []) + ['standard']
    for m in modes:
        path = CACHE / slug / m / f'{period}.trades.json'
        if path.is_file():
            meta_path = path.with_name(f'{period}.json')
            meta = json.loads(meta_path.read_text(encoding='utf-8-sig')) if meta_path.is_file() else None
            return json.loads(path.read_text(encoding='utf-8-sig')), meta, m
    return [], None, modes[0] if modes else 'standard'


def r_value(t: dict) -> float | None:
    v = t.get('estimated_r')
    return float(v) if v is not None else None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def save(name: str, value, *, folder: Path | None = None) -> Path:
    folder = folder or OUT
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
    return path
