from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

import run_raw_test as raw


ASSETS = [
    ("XAUUSD", False),
    ("XAGUSD", False),
    ("BTCUSD", False),
    ("USTEC", False),
]

PERIODS = [
    ("5y", "2021.09.01", "2026.09.01"),
    ("3y", "2023.09.01", "2026.09.01"),
    ("1y", "2025.09.01", "2026.09.01"),
]


def use_dedicated_tester() -> None:
    """Keep this transfer study away from the terminal used by the stream monitor."""
    raw.TESTER = raw.PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
    raw.TERMINAL = raw.TESTER / "terminal64.exe"
    raw.METAEDITOR = raw.TESTER / "MetaEditor64.exe"
    raw.EXPERT_DIR = (
        raw.TESTER / "MQL5" / "Experts" / "AAA Research" / "Post FOMC FX Reversal"
    )
    raw.EXPERT = raw.EXPERT_DIR / f"{raw.EXPERT_NAME}.ex5"
    raw.TESTER_SETS = raw.TESTER / "MQL5" / "Profiles" / "Tester"
    raw.CONFIGS = (
        raw.TESTER / "backtest-configs" / "post-fomc-fx-reversal-20260909"
    )
    raw.TESTER_REPORTS = (
        raw.TESTER / "reports" / "post-fomc-fx-reversal-20260909"
    )


def main() -> None:
    use_dedicated_tester()
    raw.prepare()
    rows: list[dict] = []
    total_cases = len(ASSETS) * len(PERIODS)
    sequence = 0
    for period, start, end in PERIODS:
        for symbol, usd_is_base in ASSETS:
            sequence += 1
            rows.append(
                raw.run_case(
                    symbol,
                    usd_is_base,
                    period,
                    start,
                    end,
                    sequence,
                    total_cases,
                )
            )

    audit = {
        "strategy": "Post-FOMC reversal - raw cross-asset transfer",
        "source_paper": "Lee and Wang, Jumps and Post-FOMC Announcement Returns in Currency Markets, RAPS (2025)",
        "paper_url": "https://doi.org/10.1093/rapstu/raaf003",
        "transfer_rule": "Sell each USD-quoted metal, crypto or equity-index CFD from +12 to +24 hours after every scheduled 14:00 New York FOMC statement.",
        "research_status": "Exploratory transfer outside the paper's original FX scope.",
        "assets": [symbol for symbol, _ in ASSETS],
        "risk": "1% equity at a 10x H1 ATR emergency stop; no TP, trailing, breakeven, filters, or optimization.",
        "costs": "Native MT5 Every Tick, broker spread, commission, swap and random execution delay.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": [raw.compact(row) for row in rows],
    }
    (raw.ROOT / "raw-cross-asset-audit.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )

    with (raw.ROOT / "raw-cross-asset-results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "period",
                "symbol",
                "return_pct",
                "profit_factor",
                "win_rate_pct",
                "max_drawdown_pct",
                "trades",
                "sharpe",
                "recovery_factor",
                "history_quality",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["period"],
                    row["symbol"],
                    row["return_pct"],
                    row["profit_factor"],
                    row["win_rate_pct"],
                    row["max_drawdown_pct"],
                    row["trades"],
                    row["sharpe"],
                    row["recovery_factor"],
                    row["history_quality"],
                ]
            )
    print(f"SAVED {raw.ROOT / 'raw-cross-asset-audit.json'}", flush=True)


if __name__ == "__main__":
    main()
