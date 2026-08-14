from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE_RESULTS = ROOT / "Results"
OUTPUT = ROOT / "Results Net Costs 2026-08-14"
BACKTEST_PATH = ROOT / "backtest_stock_auction.py"
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01

# Snapshot read directly from MEXAtlantic-Demo on 2026-08-14. Commission is zero
# both in the account's 140 historical trade deals and in the broker's advertised
# Standard/Pro terms. Swap sign follows MT5: negative is a debit, positive a credit.
BROKER_COSTS = {
    "SP500": {
        "commission_rate_per_side": 0.0,
        "swap_mode": "annual interest on current price / 360",
        "annual_long_swap_pct": -6.93181,
        "swap_rollover_three_day": "Friday",
    },
    "DEFAULT_STOCK": {
        "commission_rate_per_side": 0.0,
        "swap_mode": "currency per share per rollover",
        "annual_long_swap_pct": 0.0,
        "swap_rollover_three_day": "Wednesday",
    },
}


def load_backtest_module():
    spec = importlib.util.spec_from_file_location("stock_backtest_for_costs", BACKTEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BACKTEST_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BACKTEST = load_backtest_module()


def terms_for(label: str) -> dict:
    return dict(BROKER_COSTS.get(label, BROKER_COSTS["DEFAULT_STOCK"]))


def add_cost_components(label: str, trades: pd.DataFrame, gross_result: dict) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    m1, instrument = BACKTEST.load_stock(label)
    entry_spreads = m1[["time", "spread"]].rename(columns={"time": "entry_time_utc"})
    entry_spreads["entry_time_utc"] = pd.to_datetime(entry_spreads.entry_time_utc, utc=True)
    output = trades.copy()
    output["entry_time_utc"] = pd.to_datetime(output.entry_time_utc, utc=True)
    output["exit_time_utc"] = pd.to_datetime(output.exit_time_utc, utc=True)
    output = output.merge(entry_spreads, on="entry_time_utc", how="left", validate="many_to_one")
    median_spread = float(gross_result["data"]["median_spread_price"])
    output["entry_spread_price"] = output.spread.fillna(median_spread / float(instrument["point"])) * float(
        instrument["point"]
    )
    output.drop(columns=["spread"], inplace=True)

    distance = (output.entry - output.initial_stop).abs().clip(lower=1e-12)
    slippage_price = 0.25 * median_spread
    contract_size = float(instrument.get("contract_size", 1.0))
    terms = terms_for(label)
    commission_side = float(terms["commission_rate_per_side"])
    annual_swap = float(terms["annual_long_swap_pct"])
    elapsed_days = (output.exit_time_utc - output.entry_time_utc).dt.total_seconds().clip(lower=0.0) / 86400.0
    estimated_exit = output.entry + output.r_multiple.astype(float) * distance

    # R-cost components are balance independent. They can therefore be recomputed
    # correctly for each evaluation period even though position risk compounds.
    output["embedded_spread_cost_r"] = output.entry_spread_price / distance
    output["embedded_slippage_cost_r"] = (2.0 * slippage_price) / distance
    output["commission_cost_r"] = commission_side * (output.entry + estimated_exit.abs()) / distance
    output["swap_cashflow_r"] = annual_swap / 100.0 * output.entry * elapsed_days / (360.0 * distance)
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

    balances = []
    quantities = []
    spread_cash = []
    slippage_cash = []
    commission_cash = []
    swap_cash = []
    balance = STARTING_BALANCE
    for row in output.itertuples(index=False):
        risk_cash = balance * RISK_FRACTION
        trade_distance = abs(float(row.entry) - float(row.initial_stop))
        quantity = risk_cash / max(trade_distance * contract_size, 1e-12)
        quantities.append(quantity)
        spread_cash.append(float(row.embedded_spread_cost_r) * risk_cash)
        slippage_cash.append(float(row.embedded_slippage_cost_r) * risk_cash)
        commission_cash.append(float(row.commission_cost_r) * risk_cash)
        swap_cash.append(float(row.swap_cashflow_r) * risk_cash)
        balance *= max(0.0, 1.0 + RISK_FRACTION * float(row.r_multiple))
        balances.append(balance)
    output["modeled_quantity"] = quantities
    output["embedded_spread_cost_usd"] = spread_cash
    output["embedded_slippage_cost_usd"] = slippage_cash
    output["commission_usd"] = commission_cash
    output["swap_cashflow_usd"] = swap_cash
    output["balance_net_costs"] = balances
    output["contract_size"] = contract_size
    return output


def period_metrics(trades: pd.DataFrame, start_year: int, end_year: int, intratrade_dd_floor: float) -> dict:
    if trades.empty:
        subset = trades.copy()
    else:
        years = trades.entry_time_utc.dt.year
        subset = trades.loc[(years >= start_year) & (years <= end_year)].copy()
    if subset.empty:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "profit_factor": 0.0, "net_r": 0.0, "mean_r": 0.0, "return_pct": 0.0,
            "max_drawdown_pct": 0.0, "final_balance": STARTING_BALANCE,
            "embedded_spread_cost_usd": 0.0, "embedded_slippage_cost_usd": 0.0,
            "commission_usd": 0.0, "swap_cashflow_usd": 0.0,
            "total_debit_cost_usd": 0.0,
        }
    r_values = subset.r_multiple.to_numpy(float)
    balances = []
    spread_cash = 0.0
    slippage_cash = 0.0
    commission_cash = 0.0
    swap_cash = 0.0
    balance = STARTING_BALANCE
    for row in subset.itertuples(index=False):
        risk_cash = balance * RISK_FRACTION
        spread_cash += float(row.embedded_spread_cost_r) * risk_cash
        slippage_cash += float(row.embedded_slippage_cost_r) * risk_cash
        commission_cash += float(row.commission_cost_r) * risk_cash
        swap_cash += float(row.swap_cashflow_r) * risk_cash
        balance *= max(0.0, 1.0 + RISK_FRACTION * float(row.r_multiple))
        balances.append(balance)
    curve = np.r_[STARTING_BALANCE, np.asarray(balances)]
    peak = np.maximum.accumulate(curve)
    closed_drawdown = float(np.max((peak - curve) / peak * 100.0))
    profit = float(r_values[r_values > 0.0].sum())
    loss = float(r_values[r_values <= 0.0].sum())
    profit_factor = profit / abs(loss) if loss < 0.0 else (999.0 if profit > 0.0 else 0.0)
    return {
        "trades": int(len(subset)), "wins": int((r_values > 0.0).sum()),
        "losses": int((r_values <= 0.0).sum()),
        "win_rate_pct": float(100.0 * (r_values > 0.0).mean()),
        "profit_factor": float(profit_factor), "net_r": float(r_values.sum()),
        "mean_r": float(r_values.mean()),
        "return_pct": float((balance / STARTING_BALANCE - 1.0) * 100.0),
        # Preserve the original minute-marked DD as a floor; financing is added to
        # the closed curve. Only US500 has non-zero financing in this snapshot.
        "max_drawdown_pct": max(float(intratrade_dd_floor), closed_drawdown),
        "final_balance": float(balance),
        "embedded_spread_cost_usd": spread_cash,
        "embedded_slippage_cost_usd": slippage_cash,
        "commission_usd": commission_cash,
        "swap_cashflow_usd": swap_cash,
        "total_debit_cost_usd": spread_cash + slippage_cash + commission_cash + max(0.0, -swap_cash),
    }


def cost_result(label: str) -> tuple[dict, pd.DataFrame]:
    gross = json.loads((SOURCE_RESULTS / f"{label}-selected-result.json").read_text(encoding="utf-8"))
    gross_trades = pd.read_csv(
        SOURCE_RESULTS / f"{label}-selected-trades.csv",
        parse_dates=["entry_time_utc", "exit_time_utc"],
    )
    trades = add_cost_components(label, gross_trades, gross)
    gross_full = gross["full_2022_2026"]
    gross_confirmation = gross["confirmation_2026"]
    full = period_metrics(trades, 2022, 2026, gross_full["max_drawdown_pct"])
    confirmation = period_metrics(trades, 2026, 2026, gross_confirmation["max_drawdown_pct"])
    before_all_costs = trades.copy()
    before_all_costs["r_multiple"] = before_all_costs.r_before_all_costs
    before_cost_full = period_metrics(before_all_costs, 2022, 2026, 0.0)
    before_cost_confirmation = period_metrics(before_all_costs, 2026, 2026, 0.0)
    years_covered = max(
        (
            pd.Timestamp(gross["data"]["last_utc"])
            - pd.Timestamp(gross["data"]["first_utc"])
        ).total_seconds()
        / (365.25 * 86400.0),
        1e-9,
    )
    cagr = ((full["final_balance"] / STARTING_BALANCE) ** (1.0 / years_covered) - 1.0) * 100.0
    confirmation_pass = (
        confirmation["trades"] >= 3
        and confirmation["profit_factor"] >= 1.05
        and confirmation["return_pct"] > 0.0
        and confirmation["max_drawdown_pct"] < 15.0
        and full["profit_factor"] >= 1.05
    )
    result = dict(gross)
    result["gross_before_commission_swap"] = {
        "full_2022_2026": gross_full,
        "confirmation_2026": gross_confirmation,
        "full_cagr_pct": gross["full_cagr_pct"],
    }
    result["before_all_transaction_and_holding_costs"] = {
        "full_2022_2026": before_cost_full,
        "confirmation_2026": before_cost_confirmation,
    }
    result["cost_model"] = {
        **terms_for(label),
        "historical_spread": "exact M1 broker spread at entry is already embedded",
        "slippage": "25% of median spread on entry and exit is already embedded",
        "commission_evidence": "zero across 140 MEXAtlantic-Demo trade deals audited 2026-08-14",
        "warning": "Live account costs must be read again; demo specifications are not a live quote guarantee.",
    }
    result["full_2022_2026"] = full
    result["confirmation_2026"] = confirmation
    result["full_cagr_pct"] = cagr
    result["yearly"] = {
        str(year): period_metrics(
            trades,
            year,
            year,
            float(gross["yearly"][str(year)]["max_drawdown_pct"]),
        )
        for year in range(2022, 2027)
    }
    result["research_status"] = "POSITIVE_CONFIRMATION" if confirmation_pass else "FAILED_CONFIRMATION"
    result["final_status"] = "PASS" if confirmation_pass and cagr >= 15.0 else "REJECT"
    return result, trades


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    labels = ["SP500", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AVGO", "AMD", "INTC", "TSLA", "JPM"]
    outputs = {}
    rows = []
    for label in labels:
        result, trades = cost_result(label)
        outputs[label] = {"result": result, "trades": trades}
        (OUTPUT / f"{label}-net-cost-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        trades.to_csv(OUTPUT / f"{label}-net-cost-trades.csv", index=False)
        full = result["full_2022_2026"]
        confirm = result["confirmation_2026"]
        gross = result["gross_before_commission_swap"]["full_2022_2026"]
        before_cost = result["before_all_transaction_and_holding_costs"]["full_2022_2026"]
        rows.append({
            "status": result["final_status"], "instrument": label,
            "symbol": result["broker_symbol"], "trades": full["trades"],
            "win_rate_pct": full["win_rate_pct"], "profit_factor": full["profit_factor"],
            "return_before_all_costs_pct": before_cost["return_pct"],
            "gross_return_after_spread_slippage_pct": gross["return_pct"],
            "net_return_pct": full["return_pct"], "net_cagr_pct": result["full_cagr_pct"],
            "all_cost_return_impact_pct_points": before_cost["return_pct"] - full["return_pct"],
            "net_max_dd_pct": full["max_drawdown_pct"],
            "embedded_spread_cost_usd": full["embedded_spread_cost_usd"],
            "embedded_slippage_cost_usd": full["embedded_slippage_cost_usd"],
            "commission_usd": full["commission_usd"], "swap_cashflow_usd": full["swap_cashflow_usd"],
            "total_debit_cost_usd": full["total_debit_cost_usd"],
            "confirmation_trades": confirm["trades"], "confirmation_pf": confirm["profit_factor"],
            "confirmation_return_pct": confirm["return_pct"],
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT / "summary-net-costs.csv", index=False)
    (OUTPUT / "all-net-cost-results.json").write_text(
        json.dumps({label: item["result"] for label, item in outputs.items()}, indent=2), encoding="utf-8"
    )

    figure, axes = plt.subplots(4, 3, figsize=(18, 19), constrained_layout=True)
    for axis, label in zip(axes.flat, labels):
        result = outputs[label]["result"]
        trades = outputs[label]["trades"]
        full = result["full_2022_2026"]
        confirm = result["confirmation_2026"]
        time = pd.to_datetime(trades.entry_time_utc, utc=True)
        equity = STARTING_BALANCE * np.cumprod(1.0 + RISK_FRACTION * trades.r_multiple.to_numpy(float))
        axis.step(time, equity, where="post", linewidth=1.2)
        axis.axhline(STARTING_BALANCE, color="gray", linestyle="--", linewidth=0.8)
        axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", linewidth=1.0)
        axis.set_title(
            f"{label} - {result['final_status']} | Net {full['return_pct']:+.1f}% "
            f"PF {full['profit_factor']:.2f} | 2026 {confirm['return_pct']:+.1f}%"
        )
        axis.set_ylabel("Net closed equity ($)")
        axis.grid(alpha=0.25)
        individual, individual_axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
        individual_axis.step(time, equity, where="post")
        individual_axis.axhline(STARTING_BALANCE, color="gray", linestyle="--")
        individual_axis.axvline(
            pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--",
            label="Locked 2026 confirmation",
        )
        individual_axis.set_title(axis.get_title())
        individual_axis.set_xlabel("Date (UTC)")
        individual_axis.set_ylabel("Net closed equity ($)")
        individual_axis.grid(alpha=0.25)
        individual_axis.legend()
        individual.savefig(OUTPUT / f"{label}-net-cost-equity.png", dpi=170)
        plt.close(individual)
    figure.suptitle(
        "US stock/index auction models - spread, slippage, commission and financing included",
        fontsize=16,
    )
    figure.savefig(OUTPUT / "all-net-cost-equity.png", dpi=180)
    plt.close(figure)
    print(summary.to_string(index=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
