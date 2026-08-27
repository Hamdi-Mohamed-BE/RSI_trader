from __future__ import annotations

import csv
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
STORE_ROOT = PACKAGE_ROOT.parent / "EA store"
sys.path.insert(0, str(STORE_ROOT))

from app.catalog import get_sellable_catalog  # noqa: E402
from app.evidence_series import (  # noqa: E402
    CUSTOM_REPORTS,
    CUSTOM_SERIES,
    _active_report_for,
)

STARTING_BALANCE = 10_000.0
BASE_RISK_PCT = 1.0
TIME_PATTERN = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")


@dataclass(frozen=True)
class Trade:
    trade_id: str
    bot: str
    symbol: str
    open_time: datetime
    close_time: datetime
    base_net: float


@dataclass
class Scenario:
    name: str
    daily_profit_pct: float | None
    daily_loss_pct: float | None
    recovery_factor: float = 1.0
    maximum_multiplier: float | None = 1.0


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str) -> float:
    cleaned = compact(value).replace(" ", "").replace(",", "")
    return float(cleaned) if cleaned else 0.0


def read_report(path: Path) -> str:
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    raise UnicodeError(f"Could not decode {path}")


def report_for(product: Any) -> Path | None:
    direct = CUSTOM_REPORTS.get(product.label)
    if direct is not None:
        return direct if direct.is_file() else None
    custom = CUSTOM_SERIES.get(product.label)
    if custom is not None:
        result_path, case_name = custom
        rows = json.loads(result_path.read_text(encoding="utf-8-sig"))
        row = next((item for item in rows if item.get("case") == case_name), None)
        if row and row.get("report"):
            candidate = Path(str(row["report"]))
            return candidate if candidate.is_file() else None
    return _active_report_for(product.installer_label)


def parse_trades(path: Path, label: str, symbol: str) -> tuple[list[Trade], dict[str, Any]]:
    soup = BeautifulSoup(read_report(path), "html.parser")
    in_deals = False
    open_legs: list[dict[str, Any]] = []
    trades: list[Trade] = []
    unmatched_cashflow = 0.0
    output_rows = 0

    for row in soup.find_all("tr"):
        if compact(row.get_text(" ", strip=True)) == "Deals":
            in_deals = True
            continue
        if not in_deals:
            continue
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all("td", recursive=False)]
        if len(cells) != 13 or not TIME_PATTERN.fullmatch(cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S")
        direction = cells[4].lower()
        volume = number(cells[5])
        cashflow = number(cells[8]) + number(cells[9]) + number(cells[10])
        if direction == "in":
            open_legs.append({"time": when, "volume": volume, "cost": cashflow})
            continue
        if direction not in {"out", "in/out", "inout"}:
            unmatched_cashflow += cashflow
            continue

        output_rows += 1
        remaining = volume
        entry_cost = 0.0
        open_times: list[datetime] = []
        while remaining > 1e-9 and open_legs:
            leg = open_legs[0]
            available = float(leg["volume"])
            take = min(remaining, available)
            ratio = take / available if available else 0.0
            entry_cost += float(leg["cost"]) * ratio
            open_times.append(leg["time"])
            leg["volume"] = available - take
            leg["cost"] = float(leg["cost"]) * (1.0 - ratio)
            remaining -= take
            if float(leg["volume"]) <= 1e-9:
                open_legs.pop(0)
        trade_open = min(open_times) if open_times else when
        trades.append(
            Trade(
                trade_id=f"{label}:{len(trades) + 1}",
                bot=label,
                symbol=symbol,
                open_time=trade_open,
                close_time=when,
                base_net=entry_cost + cashflow,
            )
        )

    leftover_cost = unmatched_cashflow + sum(float(leg["cost"]) for leg in open_legs)
    if trades and abs(leftover_cost) > 1e-9:
        last = trades[-1]
        trades[-1] = Trade(**(asdict(last) | {"base_net": last.base_net + leftover_cost}))
    return trades, {
        "report": str(path),
        "parsed_trades": len(trades),
        "out_rows": output_rows,
        "leftover_cost_assigned": round(leftover_cost, 8),
        "parsed_net": round(sum(trade.base_net for trade in trades), 2),
    }


def drawdown(series: list[tuple[datetime, float]]) -> tuple[float, float]:
    peak = series[0][1]
    worst_amount = 0.0
    worst_pct = 0.0
    for _when, balance in series:
        peak = max(peak, balance)
        amount = peak - balance
        pct = amount / peak * 100.0 if peak > 0 else 100.0
        if pct > worst_pct:
            worst_amount, worst_pct = amount, pct
    return worst_amount, worst_pct


def simulate(trades: list[Trade], scenario: Scenario) -> dict[str, Any]:
    events: list[tuple[datetime, int, str, Trade]] = []
    for trade in trades:
        zero_duration = trade.open_time == trade.close_time
        events.append((trade.open_time, 0 if zero_duration else 1, "open", trade))
        events.append((trade.close_time, 1 if zero_duration else 0, "close", trade))
    events.sort(key=lambda item: (item[0], item[1], item[3].trade_id))

    balance = STARTING_BALANCE
    series: list[tuple[datetime, float]] = [(events[0][0], balance)]
    accepted: dict[str, float] = {}
    loss_streak = 0
    max_loss_streak = 0
    max_multiplier_used = 1.0
    locked_date = None
    current_date = None
    day_start_balance = balance
    lock_days: set[str] = set()
    skipped = 0
    closed = 0
    wins = 0
    gross_profit = 0.0
    gross_loss = 0.0
    ruined = False

    for when, _priority, action, trade in events:
        event_date = when.date()
        if event_date != current_date:
            current_date = event_date
            day_start_balance = balance
            locked_date = None

        if action == "open":
            if ruined or locked_date == event_date:
                skipped += 1
                continue
            multiplier = 1.0
            if scenario.recovery_factor > 1.0:
                try:
                    multiplier = scenario.recovery_factor**loss_streak
                except OverflowError:
                    multiplier = math.inf
                if scenario.maximum_multiplier is not None:
                    multiplier = min(multiplier, scenario.maximum_multiplier)
            accepted[trade.trade_id] = multiplier
            max_multiplier_used = max(max_multiplier_used, multiplier)
            continue

        if trade.trade_id not in accepted or ruined:
            continue
        multiplier = accepted.pop(trade.trade_id)
        result = trade.base_net * multiplier
        balance += result
        closed += 1
        if result > 0:
            wins += 1
            gross_profit += result
            loss_streak = 0
        elif result < 0:
            gross_loss += result
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)
        series.append((when, balance))

        if balance <= 0 or not math.isfinite(balance):
            ruined = True
            balance = max(0.0, balance if math.isfinite(balance) else 0.0)
            series[-1] = (when, balance)
            break

        daily_pnl = balance - day_start_balance
        hit_profit = (
            scenario.daily_profit_pct is not None
            and daily_pnl >= day_start_balance * scenario.daily_profit_pct / 100.0
        )
        hit_loss = (
            scenario.daily_loss_pct is not None
            and daily_pnl <= -day_start_balance * scenario.daily_loss_pct / 100.0
        )
        if hit_profit or hit_loss:
            locked_date = event_date
            lock_days.add(event_date.isoformat())

    dd_amount, dd_pct = drawdown(series)
    pf = gross_profit / abs(gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
    return {
        "name": scenario.name,
        "daily_profit_pct": scenario.daily_profit_pct,
        "daily_loss_pct": scenario.daily_loss_pct,
        "recovery_factor": scenario.recovery_factor,
        "maximum_multiplier": scenario.maximum_multiplier,
        "initial": STARTING_BALANCE,
        "final": round(balance, 2),
        "net": round(balance - STARTING_BALANCE, 2),
        "return_pct": round((balance / STARTING_BALANCE - 1.0) * 100.0, 4),
        "realized_dd_amount": round(dd_amount, 2),
        "realized_dd_pct": round(dd_pct, 4),
        "profit_factor": round(pf, 4),
        "trades": closed,
        "wins": wins,
        "losses": closed - wins,
        "win_rate_pct": round(wins / closed * 100.0 if closed else 0.0, 4),
        "skipped_entries": skipped,
        "lock_days": len(lock_days),
        "max_loss_streak": max_loss_streak,
        "max_multiplier_used": round(max_multiplier_used, 6),
        "max_nominal_risk_pct": round(max_multiplier_used * BASE_RISK_PCT, 6),
        "ruined": ruined,
        "series": [{"time": when.isoformat(sep=" "), "balance": round(value, 2)} for when, value in series],
    }


def main() -> None:
    all_trades: list[Trade] = []
    sources: list[dict[str, Any]] = []
    for product in get_sellable_catalog():
        report = report_for(product)
        if report is None:
            raise FileNotFoundError(f"No native one-year report for {product.label}")
        trades, audit = parse_trades(report, product.label, product.canonical)
        expected = product.evidence.trades if product.evidence else None
        audit.update({"label": product.label, "symbol": product.canonical, "expected_trades": expected})
        sources.append(audit)
        all_trades.extend(trades)
    all_trades.sort(key=lambda trade: (trade.open_time, trade.close_time, trade.trade_id))

    scenarios = [
        Scenario("Baseline 1.0x — no daily locks", None, None),
        Scenario("Fixed recovery 1.6x after loss until win", None, None, 1.6, 1.6),
        Scenario("Literal 1.6x until win — unlimited", None, None, 1.6, None),
        Scenario("Recovery 1.6x — capped at 2.56x", None, None, 1.6, 2.56),
        Scenario("Recovery 1.6x — capped at 4.096x", None, None, 1.6, 4.096),
    ]
    for profit_cap in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        for loss_cap in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
            scenarios.append(Scenario(f"Daily {profit_cap:g}% win / {loss_cap:g}% loss", profit_cap, loss_cap))
            scenarios.append(
                Scenario(
                    f"Daily {profit_cap:g}%/{loss_cap:g}% + fixed recovery 1.6x",
                    profit_cap,
                    loss_cap,
                    1.6,
                    1.6,
                )
            )
            scenarios.append(
                Scenario(
                    f"Daily {profit_cap:g}%/{loss_cap:g}% + recovery cap 2.56x",
                    profit_cap,
                    loss_cap,
                    1.6,
                    2.56,
                )
            )
            scenarios.append(
                Scenario(
                    f"Daily {profit_cap:g}%/{loss_cap:g}% + literal unlimited recovery",
                    profit_cap,
                    loss_cap,
                    1.6,
                    None,
                )
            )

    results = [simulate(all_trades, scenario) for scenario in scenarios]
    baseline = results[0]
    safe_daily = [
        row
        for row in results
        if row["recovery_factor"] == 1.0
        and row["daily_profit_pct"] is not None
        and not row["ruined"]
        and row["realized_dd_pct"] <= baseline["realized_dd_pct"]
    ]
    selected_daily = max(
        safe_daily,
        key=lambda row: (row["return_pct"], -row["realized_dd_pct"]),
    )
    capped_candidates = [
        row
        for row in results
        if row["maximum_multiplier"] == 2.56
        and row["daily_profit_pct"] is not None
        and not row["ruined"]
        and row["realized_dd_pct"] <= baseline["realized_dd_pct"]
    ]
    selected_capped = max(
        capped_candidates,
        key=lambda row: (row["return_pct"], -row["realized_dd_pct"]),
        default=None,
    )

    payload = {
        "method": {
            "starting_balance": STARTING_BALANCE,
            "base_risk_pct": BASE_RISK_PCT,
            "products": len(get_sellable_catalog()),
            "parsed_trades": len(all_trades),
            "first_entry": min(trade.open_time for trade in all_trades).isoformat(sep=" "),
            "last_exit": max(trade.close_time for trade in all_trades).isoformat(sep=" "),
            "daily_lock_basis": "Realized closed-trade P/L, broker report timestamps, percentage of start-of-day simulated balance",
            "recovery_basis": "Multiplier fixed when a trade opens; a loss raises the next accepted entry by 1.6x and a win resets it",
            "limitations": [
                "The curve overlays independent MT5 reports; it is not a shared-margin or floating-equity Strategy Tester run.",
                "The active evidence windows differ by up to sixteen days because newer EAs were validated later.",
                "Daily locks skip only entries opened after a realized threshold breach; already-open trades are not synthetically flattened.",
                "Scaling assumes P/L and transaction costs change linearly with position volume and does not model lot rounding or margin rejection.",
            ],
        },
        "sources": sources,
        "selected_daily": {key: value for key, value in selected_daily.items() if key != "series"},
        "selected_capped_recovery": (
            {key: value for key, value in selected_capped.items() if key != "series"}
            if selected_capped
            else None
        ),
        "results": results,
    }
    (ROOT / "risk-flow-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_fields = [key for key in results[0] if key != "series"]
    with (ROOT / "risk-flow-grid.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        for row in results:
            writer.writerow({key: value for key, value in row.items() if key != "series"})

    focus_names = {
        baseline["name"],
        "Daily 2% win / 2% loss",
        "Fixed recovery 1.6x after loss until win",
        "Literal 1.6x until win — unlimited",
    }
    focus = [row for row in results if row["name"] in focus_names]
    fig, ax = plt.subplots(figsize=(13, 6.5), dpi=160)
    for row in focus:
        values = row["series"]
        times = [datetime.fromisoformat(point["time"]) for point in values]
        balances = [point["balance"] for point in values]
        ax.plot(times, balances, linewidth=1.35, label=row["name"])
    ax.axhline(STARTING_BALANCE, linestyle="--", linewidth=0.9, color="gray")
    ax.set_title("Active BAT portfolio — daily locks and 1.6x recovery comparison")
    ax.set_xlabel("MT5 report time")
    ax.set_ylabel("Realized balance overlay (USD)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "risk-flow-equity-comparison.png")
    plt.close(fig)

    by_name = {row["name"]: row for row in results}
    report_rows = [
        by_name["Baseline 1.0x — no daily locks"],
        by_name["Daily 2% win / 2% loss"],
        by_name["Fixed recovery 1.6x after loss until win"],
        by_name["Daily 2%/2% + fixed recovery 1.6x"],
        by_name["Literal 1.6x until win — unlimited"],
        by_name["Recovery 1.6x — capped at 2.56x"],
        by_name["Daily 2%/2% + recovery cap 2.56x"],
        by_name["Daily 2%/2% + literal unlimited recovery"],
    ]
    lines = [
        "# Active BAT portfolio risk-control study",
        "",
        "## Decision",
        "",
        "- Added to the BAT: a portfolio-wide +2% daily profit lock and -2% daily loss lock.",
        "- Not added: either 1.6x recovery interpretation. Even the fixed 1.6x-original-risk version increased drawdown, while compounding 1.6x after every loss ruined the simulation.",
        "",
        "## Evidence-aligned last-year overlay",
        "",
        "| Policy | Return | Realized DD | PF | Win rate | Closed trades | Skipped entries | Maximum nominal risk | Ruined |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report_rows:
        lines.append(
            f"| {row['name']} | {row['return_pct']:+.2f}% | {row['realized_dd_pct']:.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['trades']:,} | "
            f"{row['skipped_entries']:,} | {row['max_nominal_risk_pct']:.2f}% | "
            f"{'YES' if row['ruined'] else 'No'} |"
        )
    lines.extend(
        [
            "",
            "![Equity comparison](risk-flow-equity-comparison.png)",
            "",
            "## What the 1.6x sequence does",
            "",
            "The phrase '1.6x the original risk until a win' was tested literally as a fixed 1.60% risk after every loss, and separately as a compounding sequence. In the compounding interpretation, consecutive losses request 1.00%, 1.60%, 2.56%, 4.10%, 6.55%, 10.49%, 16.78%, 26.84%, 42.95%, then 68.72% risk. The observed portfolio sequence contained a fourteen-loss streak. A win does not guarantee recovery because the active EAs have different reward/risk ratios and realized losses include spread, commission, swap and slippage.",
            "",
            "## Method limits",
            "",
            "- The source is 18 native MT5 one-year reports and 2,066 reconstructed closed trades, including the newly added BTC and ETH EAs.",
            "- Newer EA evidence ends up to sixteen days later than the original BAT reports, so this is an evidence-aligned one-year overlay rather than one synchronized multi-EA tester run.",
            "- The overlay includes report transaction costs but cannot reproduce shared margin, simultaneous floating drawdown, broker lot rounding or order rejection.",
            "- Backtest daily locks react to realized closed-trade P/L and skip later entries. The live guard also includes managed floating P/L, closes managed positions and deletes managed pending orders, so it can lock earlier and live results will differ.",
            "- EAs that do not natively read the guard lock may try to re-enter. While locked, the controller repeatedly removes those managed orders and positions; extra spread or commission can still occur.",
            "",
        ]
    )
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "products": len(get_sellable_catalog()),
                "trades": len(all_trades),
                "mismatches": [
                    source
                    for source in sources
                    if source["expected_trades"] != source["parsed_trades"]
                ],
                "baseline": {key: value for key, value in baseline.items() if key != "series"},
                "literal": {
                    key: value
                    for key, value in next(
                        row for row in results if row["name"] == "Literal 1.6x until win — unlimited"
                    ).items()
                    if key != "series"
                },
                "capped": {
                    key: value
                    for key, value in next(
                        row for row in results if row["name"] == "Recovery 1.6x — capped at 2.56x"
                    ).items()
                    if key != "series"
                },
                "selected_daily": payload["selected_daily"],
                "selected_capped_recovery": payload["selected_capped_recovery"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
