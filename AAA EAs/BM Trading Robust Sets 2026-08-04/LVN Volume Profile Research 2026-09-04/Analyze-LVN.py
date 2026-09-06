from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


SYMBOLS = ("xauusd", "xagusd", "btcusd", "us30", "ustec", "gbpjpy")
PHASE_COUNTS = {"screen": 6, "stop": 7, "rr": 8, "trailing": 6, "session": 5}


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    found = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(found.group(0).replace(",", "")) if found else 0.0


def percent(value: str | None) -> float:
    found = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(found.group(1)) if found else 0.0


def read_report(path: Path) -> BeautifulSoup:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return BeautifulSoup(raw.decode(encoding), "html.parser")
        except UnicodeDecodeError:
            continue
    return BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")


def score(row: dict) -> float:
    if row["trades"] < 8 or row["profit_factor"] <= 0:
        return -10_000.0 + row["trades"]
    sample_penalty = max(0, 40 - row["trades"]) * 0.35
    return (
        row["return_pct"]
        + 12.0 * math.log(max(row["profit_factor"], 0.05))
        - 0.85 * row["max_drawdown_pct"]
        + 0.75 * row["sharpe"]
        + 0.35 * row["recovery_factor"]
        - sample_penalty
    )


def parse_report(path: Path) -> dict:
    soup = read_report(path)
    values: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]

    deals = []
    inside_deals = False
    for row in soup.find_all("tr"):
        if compact(row.get_text(" ", strip=True)) == "Deals":
            inside_deals = True
            continue
        if not inside_deals:
            continue
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all("td", recursive=False)]
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]) or cells[3].lower() == "balance":
            continue
        deals.append(
            {
                "time": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"),
                "entry": cells[4].lower(),
                "commission": number(cells[8]),
                "swap": number(cells[9]),
                "profit": number(cells[10]),
                "cashflow": number(cells[8]) + number(cells[9]) + number(cells[10]),
            }
        )

    initial = number(values.get("Initial Deposit")) or 10_000.0
    net = number(values.get("Total Net Profit"))
    result = {
        "initial_balance": initial,
        "final_balance": initial + net,
        "net_profit": net,
        "return_pct": net / initial * 100.0,
        "profit_factor": number(values.get("Profit Factor")),
        "win_rate_pct": percent(values.get("Profit Trades (% of total)", "")),
        "trades": int(number(values.get("Total Trades"))),
        "max_drawdown_pct": percent(values.get("Equity Drawdown Maximal", "")),
        "sharpe": number(values.get("Sharpe Ratio")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "expected_payoff": number(values.get("Expected Payoff")),
        "history_quality": values.get("History Quality", ""),
        "commission": round(sum(item["commission"] for item in deals), 2),
        "swap": round(sum(item["swap"] for item in deals), 2),
        "deals": deals,
    }
    result["score"] = score(result)
    return result


def identify(path: Path, phase: str) -> tuple[str, str]:
    found = re.match(rf"^({'|'.join(SYMBOLS)})--(.+)--{phase}\.htm$", path.name, re.I)
    if not found:
        raise ValueError(path.name)
    return found.group(1).lower(), found.group(2).lower()


def load_reports(directory: Path, phase: str) -> list[dict]:
    rows = []
    for path in directory.glob("*.htm"):
        try:
            symbol, variant = identify(path, phase)
        except ValueError:
            continue
        rows.append({"symbol": symbol, "variant": variant, "path": str(path), **parse_report(path)})
    return rows


def serializable(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def rr_value(variant: str) -> float:
    found = re.fullmatch(r"rr(\d+)", variant)
    return float(found.group(1)) / 100.0 if found else 0.0


def robust_selection_score(row: dict, candidates: list[dict], phase: str) -> float:
    if phase != "rr":
        return row["score"]
    ordered = sorted(candidates, key=lambda item: rr_value(item["variant"]))
    index = ordered.index(row)
    neighbors = ordered[max(0, index - 1) : min(len(ordered), index + 2)]
    neighborhood = sorted(item["score"] for item in neighbors)
    median = neighborhood[len(neighborhood) // 2]
    return 0.55 * row["score"] + 0.45 * median


def plot_candidates(rows: list[dict], winners: dict, phase: str, output: Path) -> None:
    import matplotlib.pyplot as plt

    fig, grid = plt.subplots(3, 2, figsize=(16, 16), constrained_layout=True)
    axes = list(grid.flat)
    fig.suptitle(f"LVN Volume Profile — {phase} development comparison", fontsize=18, fontweight="bold")
    for axis, symbol in zip(axes, SYMBOLS):
        candidates = sorted((row for row in rows if row["symbol"] == symbol), key=lambda row: row["selection_score"], reverse=True)
        labels = [row["variant"] for row in candidates]
        returns = [row["return_pct"] for row in candidates]
        colors = ["#18b981" if row["variant"] == winners[symbol]["variant"] else "#7395c9" for row in candidates]
        axis.barh(range(len(candidates)), returns, color=colors)
        axis.set_yticks(range(len(candidates)), labels)
        axis.invert_yaxis()
        axis.axvline(0, color="#333", linewidth=0.8)
        axis.set_title(symbol.upper())
        axis.set_xlabel("Net return (%)")
        axis.grid(axis="x", alpha=0.2)
        for index, row in enumerate(candidates):
            axis.text(returns[index], index, f" {returns[index]:+.1f}% | PF {row['profit_factor']:.2f} | DD {row['max_drawdown_pct']:.1f}% | n={row['trades']}", va="center", fontsize=7.5)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170, facecolor="white")
    plt.close(fig)


def select_phase(args: argparse.Namespace) -> None:
    rows = load_reports(args.reports, args.phase)
    expected = len(SYMBOLS) * PHASE_COUNTS[args.phase]
    if len(rows) != expected:
        raise RuntimeError(f"Expected {expected} {args.phase} reports, found {len(rows)}")
    winners = {}
    for symbol in SYMBOLS:
        candidates = [row for row in rows if row["symbol"] == symbol]
        for row in candidates:
            row["selection_score"] = robust_selection_score(row, candidates, args.phase)
        eligible = [row for row in candidates if row["trades"] >= args.minimum_trades and row["profit_factor"] > 1.0 and row["return_pct"] > 0]
        winner = max(eligible or candidates, key=lambda row: row["selection_score"])
        winners[symbol] = serializable(winner)

    payload = {
        "selection_policy": "Two-year development only; positive return/PF and adequate sample preferred. RR uses neighboring-setting stability.",
        "winners": winners,
        "rows": [serializable(row) for row in rows],
    }
    args.output_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    fields = ["symbol", "variant", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "selection_score", "history_quality", "commission", "swap", "path"]
    with args.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted((serializable(row) for row in rows), key=lambda row: (row["symbol"], -row["selection_score"])))
    lines = [
        f"# LVN Volume Profile — {args.phase} selection",
        "",
        "Selection used only the two-year development period (2023-09-01 to 2025-08-31).",
        "",
        "| Symbol | Variant | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        row = winners[symbol]
        lines.append(f"| {symbol.upper()} | {row['variant']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    plot_candidates(rows, winners, args.phase, args.chart)


def trade_outcomes(deals: list[dict]) -> list[float]:
    pending = 0.0
    outcomes = []
    for deal in deals:
        if deal["entry"] == "in":
            pending += deal["cashflow"]
        elif deal["entry"] in {"out", "out by"}:
            outcomes.append(pending + deal["cashflow"])
            pending = 0.0
    return outcomes


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def block_path(outcomes: list[float], rng: random.Random, block: int = 5) -> list[float]:
    selected: list[float] = []
    while len(selected) < len(outcomes):
        start = rng.randrange(len(outcomes))
        for offset in range(block):
            selected.append(outcomes[(start + offset) % len(outcomes)])
            if len(selected) == len(outcomes):
                break
    return selected


def monte_carlo(outcomes: list[float], initial: float, samples: int = 10_000) -> dict:
    empty = {
        "samples": samples, "trades": 0, "probability_profitable_pct": 0.0, "ruin_probability_pct": 0.0,
        "drawdown_10pct_probability": 0.0, "drawdown_20pct_probability": 0.0, "return_p5_pct": 0.0,
        "return_median_pct": 0.0, "return_p95_pct": 0.0, "max_dd_median_pct": 0.0,
        "max_dd_p95_pct": 0.0, "fan": [],
    }
    if not outcomes:
        return empty
    rng = random.Random(940409 + len(outcomes))
    returns: list[float] = []
    drawdowns: list[float] = []
    profitable = ruined = dd10 = dd20 = 0
    checkpoints = sorted(set([0, len(outcomes)] + [round(len(outcomes) * index / 20) for index in range(1, 20)]))
    checkpoint_values = {index: [] for index in checkpoints}
    for sample in range(samples):
        equity = peak = initial
        maximum_dd = 0.0
        ever_ruined = False
        path = block_path(outcomes, rng)
        if sample < 2_000:
            checkpoint_values[0].append(equity)
        for index, outcome in enumerate(path, 1):
            equity += outcome
            peak = max(peak, equity)
            if peak > 0:
                maximum_dd = max(maximum_dd, (peak - equity) / peak * 100.0)
            if equity <= 0.0:
                ever_ruined = True
            if sample < 2_000 and index in checkpoint_values:
                checkpoint_values[index].append(equity)
        result=(equity-initial)/initial*100.0
        returns.append(result)
        drawdowns.append(maximum_dd)
        profitable += int(result>0.0)
        ruined += int(ever_ruined)
        dd10 += int(maximum_dd>=10.0)
        dd20 += int(maximum_dd>=20.0)
    fan=[]
    for index in checkpoints:
        values=checkpoint_values[index]
        fan.append({"trade": index, "p5": quantile(values,0.05), "p25": quantile(values,0.25), "p50": quantile(values,0.50), "p75": quantile(values,0.75), "p95": quantile(values,0.95)})
    return {
        "samples": samples,
        "trades": len(outcomes),
        "probability_profitable_pct": profitable/samples*100.0,
        "ruin_probability_pct": ruined/samples*100.0,
        "drawdown_10pct_probability": dd10/samples*100.0,
        "drawdown_20pct_probability": dd20/samples*100.0,
        "return_p5_pct": quantile(returns,0.05),
        "return_median_pct": quantile(returns,0.50),
        "return_p95_pct": quantile(returns,0.95),
        "max_dd_median_pct": quantile(drawdowns,0.50),
        "max_dd_p95_pct": quantile(drawdowns,0.95),
        "fan": fan,
    }


def equity_points(row: dict, start: datetime) -> tuple[list[datetime], list[float]]:
    balance = row["initial_balance"]
    dates = [start]
    balances = [balance]
    for deal in row["deals"]:
        balance += deal["cashflow"]
        dates.append(deal["time"])
        balances.append(balance)
    return dates, balances


def recommendation(row: dict, mc: dict) -> str:
    if row["return_pct"] > 0 and row["profit_factor"] >= 1.15 and row["trades"] >= 30 and mc["return_p5_pct"] > 0:
        return "PASS / demo candidate"
    if row["return_pct"] > 0 and row["profit_factor"] > 1.0:
        return "WATCH / insufficient robustness"
    return "REJECT"


def final_audit(args: argparse.Namespace) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    locked=load_reports(args.locked_reports,"locked")
    full=load_reports(args.full_reports,"full")
    if len(locked)!=len(SYMBOLS)*2 or len(full)!=len(SYMBOLS):
        raise RuntimeError(f"Expected {len(SYMBOLS)*2} locked and {len(SYMBOLS)} full reports, found {len(locked)} and {len(full)}")
    selection_payloads={name:json.loads(path.read_text(encoding="utf-8")) for name,path in (("screen",args.screen),("stop",args.stop),("rr",args.rr),("trailing",args.trailing),("session",args.session))}
    selections={name:payload["winners"] for name,payload in selection_payloads.items()}
    raw_vs_confirmed={}
    for symbol in SYMBOLS:
        candidates=[row for row in selection_payloads["screen"]["rows"] if row["symbol"]==symbol]
        raw=max((row for row in candidates if row["variant"].startswith("raw")),key=lambda row:row["selection_score"])
        confirmed=max((row for row in candidates if not row["variant"].startswith("raw")),key=lambda row:row["selection_score"])
        raw_vs_confirmed[symbol]={"raw":raw,"confirmed":confirmed}
    result={"test_design":{"development":"2023-09-01 to 2025-08-31","locked":"2025-09-01 to 2026-09-01","full":"2023-09-01 to 2026-09-01","development_model":"MT5 1-minute OHLC for parameter search","final_model":"MT5 Every Tick with broker spread, commission, swap and random delay","risk_per_trade_pct":1.0,"monte_carlo":"10,000 five-trade block-bootstrap paths"},"development_raw_vs_confirmed":raw_vs_confirmed,"symbols":{}}

    equity_fig,equity_grid=plt.subplots(3,2,figsize=(16,15),constrained_layout=True)
    equity_axes=list(equity_grid.flat)
    equity_fig.suptitle("LVN Volume Profile — untouched last-year equity",fontsize=18,fontweight="bold")
    mc_fig,mc_grid=plt.subplots(3,2,figsize=(16,15),constrained_layout=True)
    mc_axes=list(mc_grid.flat)
    mc_fig.suptitle("LVN Volume Profile — 10,000-path block-bootstrap Monte Carlo",fontsize=18,fontweight="bold")

    for equity_axis,mc_axis,symbol in zip(equity_axes,mc_axes,SYMBOLS):
        variants={row["variant"]:row for row in locked if row["symbol"]==symbol}
        optimized=variants["optimized"]
        baseline=variants["baseline"]
        full_row=next(row for row in full if row["symbol"]==symbol)
        outcomes=trade_outcomes(optimized["deals"])
        mc=monte_carlo(outcomes,optimized["initial_balance"])
        selected={name:selections[name][symbol]["variant"] for name in selections}
        decision=recommendation(optimized,mc)
        result["symbols"][symbol]={"selected":selected,"baseline_locked":serializable(baseline),"optimized_locked":serializable(optimized),"optimized_full":serializable(full_row),"monte_carlo":mc,"decision":decision}

        for label,row,color in (("Baseline",baseline,"#98a1ad"),("Optimized",optimized,"#18b981")):
            dates,balances=equity_points(row,datetime(2025,9,1))
            equity_axis.step(dates,balances,where="post",label=label,color=color,linewidth=1.5)
        equity_axis.axhline(10_000,color="#444",linestyle="--",linewidth=0.8)
        equity_axis.set_title(f"{symbol.upper()} — {decision} | {optimized['return_pct']:+.2f}% | PF {optimized['profit_factor']:.2f} | DD {optimized['max_drawdown_pct']:.2f}% | n={optimized['trades']}")
        equity_axis.set_ylabel("Balance (USD)")
        equity_axis.grid(alpha=0.2)
        equity_axis.legend(loc="upper left")
        equity_axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

        fan=mc["fan"]
        x=[point["trade"] for point in fan]
        mc_axis.fill_between(x,[point["p5"] for point in fan],[point["p95"] for point in fan],color="#729cff",alpha=0.18,label="5–95%")
        mc_axis.fill_between(x,[point["p25"] for point in fan],[point["p75"] for point in fan],color="#729cff",alpha=0.32,label="25–75%")
        mc_axis.plot(x,[point["p50"] for point in fan],color="#18b981",linewidth=2,label="Median")
        mc_axis.axhline(10_000,color="#444",linestyle="--",linewidth=0.8)
        mc_axis.set_title(f"{symbol.upper()} — P5 {mc['return_p5_pct']:+.1f}% | DD95 {mc['max_dd_p95_pct']:.1f}%")
        mc_axis.set_xlabel("Closed trades")
        mc_axis.set_ylabel("Balance (USD)")
        mc_axis.grid(alpha=0.2)
        mc_axis.legend(loc="upper left")

    args.charts.mkdir(parents=True,exist_ok=True)
    equity_fig.savefig(args.charts/"LOCKED BASELINE VS OPTIMIZED EQUITY.png",dpi=180,facecolor="white")
    mc_fig.savefig(args.charts/"LOCKED MONTE CARLO FAN.png",dpi=180,facecolor="white")
    plt.close(equity_fig);plt.close(mc_fig)
    args.output_json.write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")

    fields=["symbol","period","return_pct","profit_factor","win_rate_pct","max_drawdown_pct","trades","sharpe","recovery_factor","commission","swap","decision"]
    with args.output_csv.open("w",newline="",encoding="utf-8-sig") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for symbol in SYMBOLS:
            for period in ("baseline_locked","optimized_locked","optimized_full"):
                row=result["symbols"][symbol][period]
                writer.writerow({"symbol":symbol.upper(),"period":period,**{key:row.get(key,"") for key in fields},"decision":result["symbols"][symbol]["decision"]})

    lines=[
        "# Step 2 — LVN Volume Profile final native-MT5 audit","",
        "The two-year development period selected each parameter in sequence. The last year was then tested once without changing the selection.","",
        "## Untouched last-year comparison","",
        "| Symbol | Config | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Decision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for symbol in SYMBOLS:
        for label,key in (("Baseline","baseline_locked"),("Optimized","optimized_locked")):
            row=result["symbols"][symbol][key]
            lines.append(f"| {symbol.upper()} | {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} | {result['symbols'][symbol]['decision'] if label=='Optimized' else ''} |")
    lines += ["","## Raw idea versus completed-M15 confirmation (development only)","","| Symbol | Best raw touch | Raw return / PF / trades | Best confirmed approach | Confirmed return / PF / trades |","|---|---|---:|---|---:|"]
    for symbol in SYMBOLS:
        raw=raw_vs_confirmed[symbol]["raw"]
        confirmed=raw_vs_confirmed[symbol]["confirmed"]
        lines.append(f"| {symbol.upper()} | {raw['variant']} | {raw['return_pct']:+.2f}% / {raw['profit_factor']:.2f} / {raw['trades']} | {confirmed['variant']} | {confirmed['return_pct']:+.2f}% / {confirmed['profit_factor']:.2f} / {confirmed['trades']} |")
    lines += ["","These figures are development comparisons, not final evidence. The untouched table above is the decision test.","","## Selected configuration","","| Symbol | Entry/profile | Stop | RR | Trailing | Session |","|---|---|---|---|---|---|"]
    for symbol in SYMBOLS:
        selected=result["symbols"][symbol]["selected"]
        lines.append(f"| {symbol.upper()} | {selected['screen']} | {selected['stop']} | {selected['rr']} | {selected['trailing']} | {selected['session']} |")
    lines += ["","## Three-year and Monte Carlo context","","| Symbol | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 | DD ≥20% | Ruin |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in SYMBOLS:
        row=result["symbols"][symbol]["optimized_full"]
        mc=result["symbols"][symbol]["monte_carlo"]
        lines.append(f"| {symbol.upper()} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {mc['probability_profitable_pct']:.1f}% | {mc['return_p5_pct']:+.2f}% | {mc['return_median_pct']:+.2f}% | {mc['max_dd_p95_pct']:.2f}% | {mc['drawdown_20pct_probability']:.1f}% | {mc['ruin_probability_pct']:.2f}% |")
    lines += [
        "","## Method and limitations","",
        "- The composite profile uses prior M15 broker tick activity because spot CFDs have no centralized exchange volume.",
        "- The profile is rebuilt once per broker day and remains frozen during that day, avoiding look-ahead bias.",
        "- Development used MT5 one-minute OHLC for search speed. Both untouched last-year and three-year final audits used MT5 Every Tick with broker costs and random execution delay.",
        "- Risk was held at the agreed 1% per trade. A negative XAG result remains visible and satisfies the mandatory validation requirement.",
        "- No result is permission for live deployment; only a passing locked result can become a demo candidate after user approval.",
    ]
    args.output_md.write_text("\n".join(lines)+"\n",encoding="utf-8")


def main() -> None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    select=sub.add_parser("select")
    select.add_argument("--phase",choices=tuple(PHASE_COUNTS),required=True)
    select.add_argument("--reports",type=Path,required=True)
    select.add_argument("--minimum-trades",type=int,default=30)
    select.add_argument("--output-json",type=Path,required=True)
    select.add_argument("--output-csv",type=Path,required=True)
    select.add_argument("--output-md",type=Path,required=True)
    select.add_argument("--chart",type=Path,required=True)
    select.set_defaults(func=select_phase)
    final=sub.add_parser("final")
    final.add_argument("--locked-reports",type=Path,required=True)
    final.add_argument("--full-reports",type=Path,required=True)
    final.add_argument("--screen",type=Path,required=True)
    final.add_argument("--stop",type=Path,required=True)
    final.add_argument("--rr",type=Path,required=True)
    final.add_argument("--trailing",type=Path,required=True)
    final.add_argument("--session",type=Path,required=True)
    final.add_argument("--charts",type=Path,required=True)
    final.add_argument("--output-json",type=Path,required=True)
    final.add_argument("--output-csv",type=Path,required=True)
    final.add_argument("--output-md",type=Path,required=True)
    final.set_defaults(func=final_audit)
    args=parser.parse_args()
    args.func(args)


if __name__=="__main__":
    main()
