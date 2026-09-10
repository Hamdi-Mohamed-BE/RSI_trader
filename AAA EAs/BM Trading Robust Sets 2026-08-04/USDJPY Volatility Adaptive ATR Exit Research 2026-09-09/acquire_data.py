"""Read-only USDJPY D1 acquisition from the isolated Exness demo tester."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import time

import MetaTrader5 as mt5
import numpy as np


ROOT = Path(__file__).resolve().parent
PORTFOLIO_ROOT = ROOT.parent
TESTER = PORTFOLIO_ROOT / "_Backtests" / "MT5-DMC-20260811"
START = datetime(2021, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 2, tzinfo=timezone.utc)


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
        if not mt5.symbol_select("USDJPY", True):
            raise RuntimeError(f"USDJPY is unavailable: {mt5.last_error()}")

        rates = None
        for _ in range(8):
            rates = mt5.copy_rates_range("USDJPY", mt5.TIMEFRAME_D1, START, END)
            if rates is not None and len(rates) >= 900:
                break
            time.sleep(2)
        if rates is None or not len(rates):
            raise RuntimeError(f"No USDJPY D1 history returned: {mt5.last_error()}")
        rates = rates[(rates["time"] >= START.timestamp()) & (rates["time"] < END.timestamp())]
        np.savez_compressed(data_dir / "USDJPY-D1.npz", rates=rates)

        symbol = mt5.symbol_info("USDJPY")._asdict()
        metadata = {
            "source": "isolated Exness demo MT5 archive",
            "server": account.server,
            "account_mode": "demo/read-only",
            "acquired_utc": datetime.now(timezone.utc).isoformat(),
            "symbol": "USDJPY",
            "timeframe": "D1",
            "bars": int(len(rates)),
            "first_utc": datetime.fromtimestamp(int(rates["time"][0]), timezone.utc).isoformat(),
            "last_utc": datetime.fromtimestamp(int(rates["time"][-1]), timezone.utc).isoformat(),
            "point": symbol.get("point"),
            "digits": symbol.get("digits"),
            "contract_size": symbol.get("trade_contract_size"),
            "volume_min": symbol.get("volume_min"),
            "volume_step": symbol.get("volume_step"),
            "data_note": "D1 bid OHLC and the MT5 bar spread field are used. No orders are sent.",
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
