"""Read-only five-year M5 FX acquisition from the isolated Exness demo tester."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import time

import MetaTrader5 as mt5
import numpy as np


ROOT = Path(__file__).resolve().parent
TESTER = ROOT.parent / "_Backtests" / "MT5-DMC-20260811"
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD")
START = datetime(2021, 9, 1, tzinfo=timezone.utc)
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
    metadata = {
        "server": None,
        "account_mode": "demo/read-only",
        "acquired_utc": datetime.now(timezone.utc).isoformat(),
        "timeframe": "M5",
        "requested_start_utc": START.isoformat(),
        "requested_end_utc": END.isoformat(),
        "symbols": {},
    }
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
        metadata["server"] = account.server

        fields = (
            "digits", "point", "trade_contract_size", "trade_tick_size", "trade_tick_value",
            "volume_min", "volume_step", "swap_mode", "swap_long", "swap_short", "swap_rollover3days",
        )
        for symbol in SYMBOLS:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"{symbol} is unavailable: {mt5.last_error()}")
            parts = []
            cursor = START
            while cursor < END:
                finish = min(END, next_quarter(cursor))
                chunk = None
                for _ in range(8):
                    chunk = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, cursor, finish)
                    if chunk is not None and len(chunk):
                        break
                    time.sleep(2)
                if chunk is None or not len(chunk):
                    raise RuntimeError(f"{symbol}: no M5 data for {cursor.date()}..{finish.date()} ({mt5.last_error()})")
                parts.append(chunk)
                print(symbol, cursor.date(), finish.date(), len(chunk), flush=True)
                cursor = finish
            rates = np.concatenate(parts)
            _, unique = np.unique(rates["time"], return_index=True)
            rates = rates[np.sort(unique)]
            rates = rates[(rates["time"] >= START.timestamp()) & (rates["time"] < END.timestamp())]
            np.savez_compressed(data_dir / f"{symbol}-M5.npz", rates=rates)
            info = mt5.symbol_info(symbol)._asdict()
            row = {key: info.get(key) for key in fields}
            row.update(
                bars=int(len(rates)),
                first_utc=datetime.fromtimestamp(int(rates["time"][0]), timezone.utc).isoformat(),
                last_utc=datetime.fromtimestamp(int(rates["time"][-1]), timezone.utc).isoformat(),
                zero_spread_bars=int((rates["spread"] <= 0).sum()),
            )
            metadata["symbols"][symbol] = row
            (data_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            print("SAVED", symbol, len(rates), flush=True)
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
