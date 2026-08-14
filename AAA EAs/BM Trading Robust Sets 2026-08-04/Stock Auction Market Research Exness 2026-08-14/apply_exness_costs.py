from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE_RESULTS = ROOT / "Results Spread Slippage"
OUTPUT = ROOT / "Results Net Costs 2026-08-14"
BACKTEST_PATH = ROOT / "backtest_exness_stock_auction.py"
MANIFEST_PATH = ROOT / "Data" / "manifest.json"
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01
LABELS = [
    "SP500", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL",
    "META", "AVGO", "AMD", "INTC", "TSLA", "JPM",
]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("exness_stock_backtest_for_costs", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BACKTEST = load_module(BACKTEST_PATH)
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def instrument_terms(label: str) -> dict:
    terms = dict(MANIFEST["instruments"][label])
    if int(terms["swap_mode"]) != 1:
        raise RuntimeError(f"{label}: unsupported MT5 swap mode {terms['swap_mode']}")
    return terms


def add_cost_components(label: str, trades: pd.DataFrame, source_result: dict) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    m1, instrument = BACKTEST.load_stock(label)
    spreads = m1[["time", "spread"]].rename(columns={"time": "entry_time_utc"})
    spreads["entry_time_utc"] = pd.to_datetime(spreads.entry_time_utc, utc=True)

    output = trades.copy()
    output["entry_time_utc"] = pd.to_datetime(output.entry_time_utc, utc=True)
    output["exit_time_utc"] = pd.to_datetime(output.exit_time_utc, utc=True)
    output = output.merge(spreads, on="entry_time_utc", how="left", validate="many_to_one")

    point = float(instrument["point"])
    tick_size = float(instrument["tick_size"])
    tick_value = float(instrument["tick_value"])
    contract_size = float(instrument["contract_size"])
    median_spread = float(source_result["data"]["median_spread_price"])
    output["entry_spread_price"] = output.spread.fillna(median_spread / point) * point
    output.drop(columns=["spread"], inplace=True)

    distance = (output.entry - output.initial_stop).abs().clip(lower=1e-12)
    elapsed_days = (
        (output.exit_time_utc - output.entry_time_utc).dt.total_seconds().clip(lower=0.0)
        / 86400.0
    )
    commission_side = float(instrument["commission_usd_per_lot_per_side"])
    daily_swap_per_lot = float(instrument["swap_long"]) * (point / tick_size) * tick_value
    slippage_price = 0.25 * median_spread

    # The source engine already deducts the recorded entry spread and a conservative
    # slippage allowance (25% of median spread at both entry and exit). Commission
    # and current Exness long-swap are layered on here. Calendar days approximate
    # the daily rollovers and naturally include the Friday three-day financing span.
    output["embedded_spread_cost_r"] = output.entry_spread_price / distance
    output["embedded_slippage_cost_r"] = (2.0 * slippage_price) / distance
    output["commission_cost_r"] = (2.0 * commission_side) / (distance * contract_size)
    output["swap_cashflow_r"] = (
        daily_swap_per_lot * elapsed_days / (distance * contract_size)
    )
    output["r_after_spread_slippage_before_commission_swap"] = output.r_multiple.astype(float)
    output["r_before_all_costs"] = (
        output.r_after_spread_slippage_before_commission_swap
        + output.embedded_spread_cost_r
        + output.embedded_slippage_cost_r
    )
    output["r_multiple"] = (
        output.r_after_spread_slippage_before_commission_swap
        - output.commission_cost_r
        + output.swap_cashflow_r
    )
    output["holding_calendar_days"] = elapsed_days
    output["daily_swap_usd_per_lot_snapshot"] = daily_swap_per_lot

    # These audit columns follow the same compounding sequence as the report.
    balances = []
    lots = []
    spread_cash = []
    slippage_cash = []
    commission_cash = []
    swap_cash = []
    balance = STARTING_BALANCE
    for row in output.itertuples(index=False):
        risk_cash = balance * RISK_FRACTION
        trade_distance = abs(float(row.entry) - float(row.initial_stop))
        modeled_lots = risk_cash / max(trade_distance * contract_size, 1e-12)
        lots.append(modeled_lots)
        spread_cash.append(float(row.embedded_spread_cost_r) * risk_cash)
        slippage_cash.append(float(row.embedded_slippage_cost_r) * risk_cash)
        commission_cash.append(float(row.commission_cost_r) * risk_cash)
        swap_cash.append(float(row.swap_cashflow_r) * risk_cash)
        balance *= max(0.0, 1.0 + RISK_FRACTION * float(row.r_multiple))
        balances.append(balance)
    output["modeled_lots_exact_risk"] = lots
    output["embedded_spread_cost_usd"] = spread_cash
    output["embedded_slippage_cost_usd"] = slippage_cash
    output["commission_usd"] = commission_cash
    output["swap_cashflow_usd"] = swap_cash
    output["balance_net_costs"] = balances
    output["contract_size"] = contract_size
    return output


def period_metrics(
    trades: pd.DataFrame,
    start_year: int,
    end_year: int,
    intratrade_dd_floor: float,
) -> dict:
    years = trades.entry_time_utc.dt.year if not trades.empty else pd.Series(dtype=int)
    subset = trades.loc[(years >= start_year) & (years <= end_year)].copy()
    if subset.empty:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "profit_factor": 0.0, "net_r": 0.0, "mean_r": 0.0,
            "return_pct": 0.0, "max_drawdown_pct": 0.0,
            "final_balance": STARTING_BALANCE,
            "embedded_spread_cost_usd": 0.0,
            "embedded_slippage_cost_usd": 0.0,
            "commission_usd": 0.0, "swap_cashflow_usd": 0.0,
            "total_debit_cost_usd": 0.0,
        }

    r_values = subset.r_multiple.to_numpy(float)
    balances = []
    spread_cash = slippage_cash = commission_cash = swap_cash = 0.0
    balance = STARTING_BALANCE
    for row in subset.itertuples(index=False):
        risk_cash = balance * RISK_FRACTION
        spread_cash += float(row.embedded_spread_cost_r) * risk_cash
        slippage_cash += float(row.embedded_slippage_cost_r) * risk_cash
        commission_cash += float(row.commission_cost_r) * risk_cash
        swap_cash += float(row.swap_cashflow_r) * risk_cash
        balance *= max(0.0, 1.0 + RISK_FRACTION * float(row.r_multiple))
        balances.append(balance)

    curve = np.r_[STARTING_BALANCE, np.asarray(balances, dtype=float)]
    peak = np.maximum.accumulate(curve)
    closed_dd = float(np.max((peak - curve) / peak * 100.0))
    gross_profit_r = float(r_values[r_values > 0.0].sum())
    gross_loss_r = float(r_values[r_values <= 0.0].sum())
    pf = gross_profit_r / abs(gross_loss_r) if gross_loss_r < 0.0 else (
        999.0 if gross_profit_r > 0.0 else 0.0
    )
    return {
        "trades": int(len(subset)),
        "wins": int((r_values > 0.0).sum()),
        "losses": int((r_values <= 0.0).sum()),
        "win_rate_pct": float(100.0 * (r_values > 0.0).mean()),
        "profit_factor": float(pf),
        "net_r": float(r_values.sum()),
        "mean_r": float(r_values.mean()),
        "return_pct": float((balance / STARTING_BALANCE - 1.0) * 100.0),
        "max_drawdown_pct": max(float(intratrade_dd_floor), closed_dd),
        "final_balance": float(balance),
        "embedded_spread_cost_usd": float(spread_cash),
        "embedded_slippage_cost_usd": float(slippage_cash),
        "commission_usd": float(commission_cash),
        "swap_cashflow_usd": float(swap_cash),
        "total_debit_cost_usd": float(
            spread_cash + slippage_cash + commission_cash + max(0.0, -swap_cash)
        ),
    }


def build_result(label: str) -> tuple[dict, pd.DataFrame]:
    source = json.loads(
        (SOURCE_RESULTS / f"{label}-selected-result.json").read_text(encoding="utf-8")
    )
    source_trades = pd.read_csv(
        SOURCE_RESULTS / f"{label}-selected-trades.csv",
        parse_dates=["entry_time_utc", "exit_time_utc"],
    )
    trades = add_cost_components(label, source_trades, source)
    source_full = source["full_2022_2026"]
    source_confirmation = source["confirmation_2026"]
    full = period_metrics(trades, 2022, 2026, source_full["max_drawdown_pct"])
    confirmation = period_metrics(
        trades, 2026, 2026, source_confirmation["max_drawdown_pct"]
    )

    before_all = trades.copy()
    before_all["r_multiple"] = before_all.r_before_all_costs
    before_full = period_metrics(before_all, 2022, 2026, 0.0)
    before_confirmation = period_metrics(before_all, 2026, 2026, 0.0)

    years = max(
        (
            pd.Timestamp(source["data"]["last_utc"])
            - pd.Timestamp(source["data"]["first_utc"])
        ).total_seconds() / (365.25 * 86400.0),
        1e-9,
    )
    cagr = ((full["final_balance"] / STARTING_BALANCE) ** (1.0 / years) - 1.0) * 100.0
    confirmation_pass = (
        confirmation["trades"] >= 3
        and confirmation["profit_factor"] >= 1.05
        and confirmation["return_pct"] > 0.0
        and confirmation["max_drawdown_pct"] < 15.0
        and full["profit_factor"] >= 1.05
    )
    terms = instrument_terms(label)
    result = dict(source)
    result["after_spread_slippage_before_commission_swap"] = {
        "full_2022_2026": source_full,
        "confirmation_2026": source_confirmation,
        "full_cagr_pct": source["full_cagr_pct"],
    }
    result["before_all_transaction_and_holding_costs"] = {
        "full_2022_2026": before_full,
        "confirmation_2026": before_confirmation,
    }
    result["cost_model"] = {
        "historical_spread": "recorded Exness M1 entry spread",
        "slippage": "25% of median recorded spread at entry and exit",
        "commission_usd_per_lot_per_side": terms["commission_usd_per_lot_per_side"],
        "commission_source": terms["commission_source"],
        "commission_confidence": terms["commission_confidence"],
        "swap_mode": "MT5 points per lot per rollover",
        "long_swap_points_snapshot_2026_08_14": terms["swap_long"],
        "daily_swap_usd_per_lot_snapshot": (
            float(terms["swap_long"]) * float(terms["point"])
            / float(terms["tick_size"]) * float(terms["tick_value"])
        ),
        "triple_swap_day": "Friday",
        "financing_method": "current daily rate multiplied by calendar holding days",
        "limitations": (
            "Historical swap-rate snapshots and dividend adjustments were unavailable. "
            "Current swap is applied to the full sample; stock commission is a published lower bound."
        ),
    }
    result["full_2022_2026"] = full
    result["confirmation_2026"] = confirmation
    result["full_cagr_pct"] = cagr
    result["yearly"] = {
        str(year): period_metrics(
            trades,
            year,
            year,
            float(source["yearly"][str(year)]["max_drawdown_pct"]),
        )
        for year in range(2022, 2027)
    }
    result["research_status"] = (
        "POSITIVE_CONFIRMATION" if confirmation_pass else "FAILED_CONFIRMATION"
    )
    result["final_status"] = "PASS" if confirmation_pass and cagr >= 15.0 else "REJECT"
    return result, trades


def write_chart(label: str, result: dict, trades: pd.DataFrame, axis=None) -> None:
    time = pd.to_datetime(trades.entry_time_utc, utc=True)
    equity = STARTING_BALANCE * np.cumprod(
        1.0 + RISK_FRACTION * trades.r_multiple.to_numpy(float)
    )
    own_figure = axis is None
    if own_figure:
        figure, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
    axis.step(time, equity, where="post", linewidth=1.25)
    axis.axhline(STARTING_BALANCE, color="gray", linestyle="--", linewidth=0.8)
    axis.axvline(
        pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--",
        linewidth=1.0, label="Locked 2026 confirmation",
    )
    full = result["full_2022_2026"]
    confirmation = result["confirmation_2026"]
    axis.set_title(
        f"{label} - {result['final_status']} | Net {full['return_pct']:+.1f}% "
        f"PF {full['profit_factor']:.2f} | 2026 {confirmation['return_pct']:+.1f}%"
    )
    axis.set_ylabel("Net closed equity ($)")
    axis.grid(alpha=0.25)
    if own_figure:
        axis.set_xlabel("Date (UTC)")
        axis.legend()
        figure.savefig(OUTPUT / f"{label}-net-cost-equity.png", dpi=170)
        plt.close(figure)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    outputs = {}
    rows = []
    for label in LABELS:
        result, trades = build_result(label)
        outputs[label] = {"result": result, "trades": trades}
        (OUTPUT / f"{label}-net-cost-result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        trades.to_csv(OUTPUT / f"{label}-net-cost-trades.csv", index=False)
        write_chart(label, result, trades)

        full = result["full_2022_2026"]
        confirmation = result["confirmation_2026"]
        source = result["after_spread_slippage_before_commission_swap"]["full_2022_2026"]
        before = result["before_all_transaction_and_holding_costs"]["full_2022_2026"]
        rows.append({
            "status": result["final_status"],
            "instrument": label,
            "symbol": result["broker_symbol"],
            "trades": full["trades"],
            "win_rate_pct": full["win_rate_pct"],
            "profit_factor": full["profit_factor"],
            "return_before_all_costs_pct": before["return_pct"],
            "return_after_spread_slippage_pct": source["return_pct"],
            "net_return_pct": full["return_pct"],
            "net_cagr_pct": result["full_cagr_pct"],
            "all_cost_return_impact_pct_points": before["return_pct"] - full["return_pct"],
            "net_max_dd_pct": full["max_drawdown_pct"],
            "spread_cost_usd": full["embedded_spread_cost_usd"],
            "slippage_cost_usd": full["embedded_slippage_cost_usd"],
            "commission_usd": full["commission_usd"],
            "swap_cashflow_usd": full["swap_cashflow_usd"],
            "total_debit_cost_usd": full["total_debit_cost_usd"],
            "confirmation_trades": confirmation["trades"],
            "confirmation_pf": confirmation["profit_factor"],
            "confirmation_return_pct": confirmation["return_pct"],
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT / "summary-net-costs.csv", index=False)
    (OUTPUT / "all-net-cost-results.json").write_text(
        json.dumps({key: value["result"] for key, value in outputs.items()}, indent=2),
        encoding="utf-8",
    )

    figure, axes = plt.subplots(4, 3, figsize=(18, 19), constrained_layout=True)
    for axis, label in zip(axes.flat, LABELS):
        write_chart(label, outputs[label]["result"], outputs[label]["trades"], axis)
    figure.suptitle(
        "Exness Zero stock/index auction models - spread, slippage, commission and swap included",
        fontsize=16,
    )
    figure.savefig(OUTPUT / "all-net-cost-equity.png", dpi=180)
    plt.close(figure)
    print(summary.to_string(index=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
