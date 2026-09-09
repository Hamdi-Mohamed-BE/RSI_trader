from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")
BERLIN = ZoneInfo("Europe/Berlin")
LONDON = ZoneInfo("Europe/London")

EXPECTED = {
    "Tokyo pre-fix": ("Tokyo", "long USD"),
    "Tokyo post-fix": ("Tokyo", "short USD"),
    "ECB pre-fix": ("Europe", "long USD"),
    "London post-fix": ("Europe", "short USD"),
}
BASE_QUOTED = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}
USD_QUOTED = {"USDJPY", "USDCHF", "USDCAD"}


def expected_times(row: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp]:
    day = pd.Timestamp(row["business_date"]).date()
    if row["leg"] == "Tokyo pre-fix":
        prior = day - pd.Timedelta(days=1)
        entry = pd.Timestamp(prior).replace(hour=17, minute=0, tzinfo=NY)
        exit_ = pd.Timestamp(day).replace(hour=9, minute=55, tzinfo=TOKYO)
    elif row["leg"] == "Tokyo post-fix":
        entry = pd.Timestamp(day).replace(hour=9, minute=55, tzinfo=TOKYO)
        exit_ = pd.Timestamp(day).replace(hour=2, minute=0, tzinfo=NY)
    elif row["leg"] == "ECB pre-fix":
        entry = pd.Timestamp(day).replace(hour=2, minute=0, tzinfo=NY)
        exit_ = pd.Timestamp(day).replace(hour=14, minute=15, tzinfo=BERLIN)
    elif row["leg"] == "London post-fix":
        entry = pd.Timestamp(day).replace(hour=16, minute=0, tzinfo=LONDON)
        exit_ = pd.Timestamp(day).replace(hour=17, minute=0, tzinfo=NY)
    else:
        raise AssertionError(f"Unexpected leg: {row['leg']}")
    return entry.tz_convert("UTC"), exit_.tz_convert("UTC")


def main() -> None:
    trades = pd.read_csv(ROOT / "raw-trades.csv", parse_dates=["business_date", "entry_utc", "exit_utc"])
    summary = pd.read_csv(ROOT / "raw-portfolio-summary.csv")
    metadata = json.loads((ROOT / "Data" / "metadata.json").read_text(encoding="utf-8"))

    assert set(trades["symbol"]) == BASE_QUOTED | USD_QUOTED
    assert set(trades["leg"]) == set(EXPECTED)
    assert set(trades["cost_mode"]) == {"gross", "half_spread", "full_spread"}
    assert not trades.duplicated(["business_date", "symbol", "leg", "cost_mode"]).any()
    assert (trades["entry_utc"] < trades["exit_utc"]).all()
    assert (trades["business_date"].dt.weekday < 5).all()

    sample = trades[trades["cost_mode"] == "gross"].copy()
    for _, row in sample.iterrows():
        expected_entry, expected_exit = expected_times(row)
        assert row["entry_utc"] == expected_entry
        assert row["exit_utc"] == expected_exit
        group, usd_direction = EXPECTED[row["leg"]]
        assert row["group"] == group
        assert row["usd_direction"] == usd_direction
        if row["symbol"] in BASE_QUOTED:
            expected_quote = "short" if usd_direction == "long USD" else "long"
        else:
            expected_quote = "long" if usd_direction == "long USD" else "short"
        assert row["quote_direction"] == expected_quote

    pivot = trades.pivot(
        index=["business_date", "symbol", "leg"],
        columns="cost_mode",
        values="return_pct",
    )
    assert (pivot["gross"] + 1e-12 >= pivot["half_spread"]).all()
    assert (pivot["half_spread"] + 1e-12 >= pivot["full_spread"]).all()

    # Independently rebuild the full-spread, five-year equal-weight portfolio.
    full = trades[trades["cost_mode"] == "full_spread"].copy()
    full["log_return"] = np.log1p(full["return_pct"] / 100.0)
    pair_day = full.groupby(["business_date", "symbol"], as_index=False)["log_return"].sum()
    pair_day["simple"] = np.expm1(pair_day["log_return"])
    daily = pair_day.groupby("business_date")["simple"].mean().sort_index()
    rebuilt_return = (np.prod(1.0 + daily.to_numpy()) - 1.0) * 100.0
    reported = summary[
        (summary["period"] == "5y")
        & (summary["cost_mode"] == "full_spread")
        & (summary["strategy"] == "All")
    ].iloc[0]
    assert abs(rebuilt_return - reported["return_pct"]) < 1e-9

    counts = sample.groupby(["symbol", "leg"]).size()
    assert counts.min() >= 900
    assert counts.max() <= 1300
    assert len(metadata["symbols"]) == 7

    print("VERIFIED")
    print(f"Rows: {len(trades):,} ({len(sample):,} unique raw trades x 3 cost modes)")
    print(f"Full-spread 5y portfolio return: {rebuilt_return:.2f}%")
    print("DST timestamps, quote directions, spread monotonicity and summary reconstruction passed.")


if __name__ == "__main__":
    main()
