from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
START = pd.Timestamp("2024-08-11", tz="UTC")
END = pd.Timestamp("2026-08-10 23:59:59", tz="UTC")
URL = "https://fapi.binance.com/fapi/v1/fundingRate"


def main() -> None:
    rows: list[dict] = []
    cursor = int(START.timestamp() * 1000)
    end = int(END.timestamp() * 1000)
    while cursor <= end:
        response = requests.get(
            URL,
            params={"symbol": "BTCUSDT", "startTime": cursor, "endTime": end, "limit": 1000},
            timeout=60,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        next_cursor = int(batch[-1]["fundingTime"]) + 1
        if next_cursor <= cursor:
            raise RuntimeError("Funding pagination did not advance")
        cursor = next_cursor
        time.sleep(0.15)
    frame = pd.DataFrame(rows).drop_duplicates("fundingTime").sort_values("fundingTime")
    frame["time"] = pd.to_datetime(frame["fundingTime"], unit="ms", utc=True)
    frame["rate"] = pd.to_numeric(frame["fundingRate"], errors="raise")
    frame["mark_price"] = pd.to_numeric(frame["markPrice"], errors="coerce")
    frame = frame.loc[(frame["time"] >= START) & (frame["time"] <= END), ["time", "rate", "mark_price"]]
    output = DATA / "btcusdt-funding-2024-08-11_2026-08-10.parquet"
    con = duckdb.connect()
    con.register("funding", frame)
    con.execute(f"COPY funding TO '{output.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    con.close()
    summary = {
        "source": URL, "rows": len(frame), "first": frame["time"].min().isoformat(),
        "last": frame["time"].max().isoformat(), "output": str(output),
    }
    (DATA / "funding-metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
