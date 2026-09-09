"""Read-only BTCUSD M5 acquisition from the isolated Exness demo tester.

This script never connects to either installed live terminal and never enables
trading.  It attempts to extend the already archived M5 sample back to 2022.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import subprocess
import time

import MetaTrader5 as mt5
import numpy as np


ROOT = Path(__file__).resolve().parent
PORTFOLIO_ROOT = ROOT.parent
TESTER = PORTFOLIO_ROOT / "_Backtests" / "MT5-DMC-20260811"
ARCHIVE = PORTFOLIO_ROOT / "Volatility Compression Expansion Research 2026-09-06" / "Data" / "BTCUSD-M5.npz"
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 1, tzinfo=timezone.utc)


def next_quarter(value: datetime) -> datetime:
    month_index = value.year * 12 + value.month - 1 + 3
    return datetime(month_index // 12, month_index % 12 + 1, 1, tzinfo=timezone.utc)


def main() -> None:
    data_dir = ROOT / "Data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config = ROOT / "data-reader.ini"
    config.write_text(
        "[Common]\nLogin=472334559\nServer=Exness-MT5Trial16\n"
        "[Experts]\nEnabled=0\n[Charts]\nMaxBars=10000000\n",
        encoding="utf-8-sig",
    )

    process = subprocess.Popen(
        f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{config}"',
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        time.sleep(8)
        if not mt5.initialize(str(TESTER / "terminal64.exe"), portable=True, timeout=120_000):
            raise RuntimeError(str(mt5.last_error()))
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if not terminal or str(TESTER).lower() != terminal.path.lower():
            raise RuntimeError("Unexpected MT5 terminal; refusing to read from a live installation")
        if not account or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError("History acquisition is restricted to the isolated demo terminal")
        if not mt5.symbol_select("BTCUSD", True):
            raise RuntimeError(f"BTCUSD is unavailable: {mt5.last_error()}")

        parts = []
        cursor = START
        missing = []
        while cursor < END:
            finish = min(END, next_quarter(cursor))
            chunk = None
            for _ in range(6):
                chunk = mt5.copy_rates_range("BTCUSD", mt5.TIMEFRAME_M5, cursor, finish)
                if chunk is not None and len(chunk):
                    break
                time.sleep(2)
            if chunk is None or not len(chunk):
                missing.append(f"{cursor.date()}..{finish.date()}")
            else:
                parts.append(chunk)
                print("BTCUSD", cursor.date(), finish.date(), len(chunk), flush=True)
            cursor = finish

        if parts:
            rates = np.concatenate(parts)
            _, unique = np.unique(rates["time"], return_index=True)
            rates = rates[np.sort(unique)]
            rates = rates[(rates["time"] >= START.timestamp()) & (rates["time"] < END.timestamp())]
        else:
            rates = np.empty(0)

        source = "fresh isolated Exness demo archive"
        if not len(rates) or datetime.fromtimestamp(int(rates["time"][0]), timezone.utc) > datetime(2022, 1, 2, tzinfo=timezone.utc):
            shutil.copy2(ARCHIVE, data_dir / "BTCUSD-M5.npz")
            with np.load(ARCHIVE) as archive:
                rates = archive["rates"]
            source = "existing verified Exness M5 archive (terminal did not expose a longer sample)"
        else:
            np.savez_compressed(data_dir / "BTCUSD-M5.npz", rates=rates)

        info = mt5.symbol_info("BTCUSD")._asdict()
        metadata = {
            "source": source,
            "server": account.server,
            "account_mode": "demo/read-only",
            "acquired_utc": datetime.now(timezone.utc).isoformat(),
            "symbol": "BTCUSD",
            "timeframe": "M5",
            "bars": int(len(rates)),
            "first_utc": datetime.fromtimestamp(int(rates["time"][0]), timezone.utc).isoformat(),
            "last_utc": datetime.fromtimestamp(int(rates["time"][-1]), timezone.utc).isoformat(),
            "point": info.get("point"),
            "digits": info.get("digits"),
            "missing_quarters": missing,
            "volume_note": "MT5 tick_volume is used as the paper's traded-volume proxy; real_volume is unavailable.",
        }
        (data_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2), flush=True)
    finally:
        mt5.shutdown()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
