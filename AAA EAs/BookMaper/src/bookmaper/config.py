from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data" / "market"
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts"
ACTIVE_PACKAGE_ROOT = PROJECT_ROOT.parent / "BM Trading Robust Sets 2026-08-04"
ACTIVE_RISK_JSON = (
    ACTIVE_PACKAGE_ROOT
    / "Portfolio Risk Controls Research 2026-08-27"
    / "risk-flow-results.json"
)

TEST_START = "2025-08-11"
TEST_END = "2026-08-21"
TRAIN_SCORE_START = "2022-08-11"
INITIAL_BALANCE = 10_000.0


@dataclass(frozen=True)
class AssetSpec:
    key: str
    label: str
    ticker: str
    symbol_family: str
    roundtrip_cost_bps: float


ASSETS: dict[str, AssetSpec] = {
    "xau": AssetSpec("xau", "XAU", "GC=F", "XAUUSD", 5.0),
    "us100": AssetSpec("us100", "US100", "NQ=F", "USTEC", 3.0),
    "btc": AssetSpec("btc", "BTC", "BTC-USD", "BTCUSD", 12.0),
    "eth": AssetSpec("eth", "ETH", "ETH-USD", "ETHUSD", 15.0),
    "us30": AssetSpec("us30", "US30", "YM=F", "US30", 3.0),
}


def ensure_directories() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

