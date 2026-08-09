from __future__ import annotations

import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
SOURCE_REPORTS = BT / "reports" / "gold-liquidity-sweep"
TESTER = BT / "MQL5" / "Profiles" / "Tester"
REPORTS = ROOT / "Reports"
SETTINGS = ROOT / "Best Settings"


def load(name: str) -> list[dict]:
    return json.loads((ROOT / f"{name}-results.json").read_text(encoding="utf-8"))


def money(value: float) -> str:
    return f"${value:,.2f}"


def metrics(row: dict) -> str:
    return (f"{row['return_pct']:+.2f}% / {row['equity_dd_pct']:.2f}% / "
            f"{row['profit_factor']:.2f} / {row['trades']}")


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    SETTINGS.mkdir(exist_ok=True)
    for source in SOURCE_REPORTS.glob("*.htm"):
        shutil.copy2(source, REPORTS / source.name)
        graph = source.with_suffix(".png")
        if graph.exists():
            shutil.copy2(graph, REPORTS / graph.name)

    source_set = TESTER / "GLS aggressive-core.set"
    rejected_text = source_set.read_text(encoding="utf-8-sig").replace(
        "InpEnableTrading=true||", "InpEnableTrading=false||", 1
    )
    rejected_name = "REJECTED - XAUUSD M5 - Gold Liquidity Sweep - 1pct.set"
    (SETTINGS / rejected_name).write_text(rejected_text, encoding="utf-8-sig")

    development = load("development")
    selection = load("selection")[0]
    final = load("final")[0]
    full = load("full")[0]

    lines = [
        "# Gold Liquidity Sweep EA — honest validation report",
        "",
        "## Verdict: REJECTED",
        "",
        "The mechanical version of the supplied video strategy is not valid for the synchronized live EA portfolio. It failed both the Jan-Aug 2025 selection slice and the locked last year, and the continuous 2022-2026 test was also negative. The BAT installer and active portfolio were not changed.",
        "",
        "## Test protocol",
        "",
        "- Broker/history: Exness `Exness-MT5Trial16`, XAUUSD",
        "- Initial balance: USD 10,000 per independent test",
        "- Risk: 1.00% of current equity per trade",
        "- Engine: MT5 Every Tick with random execution delay",
        "- Chart: M5; H1 and M15 confirmed swing-structure alignment",
        "- Permanent hard stop; maximum two entries per UTC day; three-hour time exit",
        "- Acceptance gate: positive locked-final return, PF at least 1.15, equity DD no more than 12%, and at least 20 final trades",
        "",
        "## Development variants, 2022-01-03 through 2024-12-31",
        "",
        "| Variant | Return | Max equity DD | PF | Win rate | Trades |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(development, key=lambda item: item["return_pct"], reverse=True):
        lines.append(
            f"| {row['variant']} | {row['return_pct']:+.2f}% | {row['equity_dd_pct']:.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['trades']} |"
        )

    lines += [
        "",
        "Only `aggressive-core` was positive in development, but +1.48% from only 19 trades over three years was already insufficient evidence. It was nevertheless locked before the later tests and carried forward without retuning.",
        "",
        "## Locked checks",
        "",
        "Cells show return / max equity DD / PF / trades.",
        "",
        "| Period | Result | Decision |",
        "|---|---:|---|",
        f"| Jan-Aug 2025 selection | {metrics(selection)} | Fail |",
        f"| 2025-08-07 to 2026-08-06 final | {metrics(final)} | Fail |",
        f"| Continuous 2022-01-03 to 2026-08-06 | {metrics(full)} | Fail |",
        "",
        "## Continuous-test trade statistics",
        "",
        f"- Final balance: {money(full['final'])}; net: {money(full['net'])}",
        f"- Gross profit / loss: {money(full['gross_profit'])} / {money(full['gross_loss'])}",
        f"- Wins / losses: {full['wins']} / {full['losses']} ({full['win_rate_pct']:.2f}% win rate)",
        f"- Largest win / loss: {money(full['largest_win'])} / {money(full['largest_loss'])}",
        f"- Average win / loss: {money(full['average_win'])} / {money(full['average_loss'])}",
        f"- Balance max DD: {money(full['balance_dd_amount'])} ({full['balance_dd_pct']:.2f}%)",
        f"- Recovery / Sharpe: {full['recovery_factor']:.2f} / {full['sharpe']:.2f}",
        f"- History quality: {full['history_quality']}",
        "",
        "## Transcript fidelity and limitation",
        "",
        "The EA mechanizes H1/M15 trend alignment, M15 displacement-created supply/demand zones, M5 sweep-and-reclaim entries, nearest M15 swing targets, and protected-candle stops. The video does not give objective formulas for drawing zones or market structure, and one showcased trade removes its stop based on gut feeling. That discretionary stop removal was deliberately excluded. The claimed USD 566,000 from two trades is not evidence of repeatable percentage performance because the account size, exposure and complete trade population are not supplied.",
        "",
        "## Files",
        "",
        "- `Gold Liquidity Sweep EA.mq5/.ex5`: compiled research EA",
        f"- `Best Settings/{rejected_name}`: disabled rejected preset for audit only",
        "- `Reports`: native MT5 reports and equity graphs",
        "- `STRATEGY TRANSLATION.md`: exact mechanical translation and limitations",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Gold liquidity research finalized as REJECTED.")


if __name__ == "__main__":
    main()
