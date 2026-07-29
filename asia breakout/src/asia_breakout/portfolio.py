from __future__ import annotations

from dataclasses import dataclass
from math import inf

import pandas as pd


@dataclass(frozen=True, slots=True)
class PortfolioResult:
    risk_pct: float
    exposure_cap_pct: float
    signals: int
    accepted_trades: int
    skipped_signals: int
    wins: int
    losses: int
    breakeven: int
    win_rate_pct: float
    profit_factor: float
    net_r: float
    starting_balance: float
    ending_balance: float
    net_profit: float
    return_pct: float
    max_realized_drawdown_pct: float
    max_committed_risk_drawdown_pct: float
    max_concurrent_trades: int
    max_planned_exposure_pct: float

    def to_dict(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }


def simulate_portfolio(
    trades_by_instrument: dict[str, pd.DataFrame],
    starting_balance: float,
    risk_pct: float,
    exposure_cap_pct: float,
    priority: tuple[str, ...],
) -> tuple[PortfolioResult, pd.DataFrame]:
    """Compound one account while rejecting entries above the exposure cap."""
    frames: list[pd.DataFrame] = []
    for instrument, frame in trades_by_instrument.items():
        if frame.empty:
            continue
        item = frame.copy()
        item["instrument"] = instrument
        frames.append(item)
    if not frames:
        empty = PortfolioResult(
            risk_pct,
            exposure_cap_pct,
            0,
            0,
            0,
            0,
            0,
            0,
            0.0,
            0.0,
            0.0,
            starting_balance,
            starting_balance,
            0.0,
            0.0,
            0.0,
            0.0,
            0,
            0.0,
        )
        return empty, pd.DataFrame()

    trades = pd.concat(frames, ignore_index=True)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True)
    trades["trade_id"] = range(len(trades))
    priority_rank = {
        instrument: index for index, instrument in enumerate(priority)
    }

    events: list[tuple[pd.Timestamp, int, int, int, int]] = []
    for index, row in trades.iterrows():
        rank = priority_rank.get(str(row["instrument"]), len(priority_rank))
        entry_time = row["entry_time"]
        exit_time = row["exit_time"]
        events.append((entry_time, 1, 1, rank, index))
        # Normal exits release exposure before new entries at the same time.
        # A trade that enters and exits inside the same source bar must be
        # opened first and closed immediately afterwards.
        exit_order = 2 if exit_time <= entry_time else 0
        events.append((exit_time, exit_order, -1, rank, index))
    # Exits release risk before entries at the same timestamp. Entry ties use
    # the explicit, frozen basket order instead of future trade outcomes.
    events.sort(key=lambda event: (event[0], event[1], event[3], event[4]))

    balance = starting_balance
    peak = starting_balance
    max_realized_dd = 0.0
    max_committed_dd = 0.0
    max_active = 0
    max_planned_exposure = 0.0
    active: dict[int, float] = {}
    accepted: list[int] = []
    skipped: list[int] = []
    risk_cash_by_trade: dict[int, float] = {}
    pnl_cash_by_trade: dict[int, float] = {}
    balance_after_exit: dict[int, float] = {}
    exit_sequence: dict[int, int] = {}
    closed_count = 0

    def update_drawdowns() -> None:
        nonlocal peak, max_realized_dd, max_committed_dd
        peak = max(peak, balance)
        if peak <= 0:
            return
        realized_dd = (peak - balance) / peak * 100.0
        committed_equity = balance - sum(active.values())
        committed_dd = (peak - committed_equity) / peak * 100.0
        max_realized_dd = max(max_realized_dd, realized_dd)
        max_committed_dd = max(max_committed_dd, committed_dd)

    for _, _, event_type, _, index in events:
        if event_type == -1:
            risk_cash = active.pop(index, None)
            if risk_cash is None:
                continue
            pnl_cash = risk_cash * float(trades.loc[index, "pnl_r"])
            balance += pnl_cash
            closed_count += 1
            pnl_cash_by_trade[index] = pnl_cash
            balance_after_exit[index] = balance
            exit_sequence[index] = closed_count
            update_drawdowns()
            continue

        proposed_exposure = (len(active) + 1) * risk_pct
        if proposed_exposure > exposure_cap_pct + 1e-12:
            skipped.append(index)
            continue
        risk_cash = balance * risk_pct / 100.0
        active[index] = risk_cash
        risk_cash_by_trade[index] = risk_cash
        accepted.append(index)
        max_active = max(max_active, len(active))
        max_planned_exposure = max(max_planned_exposure, proposed_exposure)
        update_drawdowns()

    selected = trades.loc[accepted].copy()
    selected["portfolio_status"] = "accepted"
    selected["portfolio_risk_cash"] = selected.index.map(risk_cash_by_trade)
    selected["portfolio_pnl_cash"] = selected.index.map(pnl_cash_by_trade)
    selected["portfolio_balance_after_exit"] = selected.index.map(balance_after_exit)
    selected["portfolio_exit_sequence"] = selected.index.map(exit_sequence)
    if skipped:
        rejected = trades.loc[skipped].copy()
        rejected["portfolio_status"] = "skipped_cap"
        rejected["portfolio_risk_cash"] = pd.NA
        rejected["portfolio_pnl_cash"] = pd.NA
        rejected["portfolio_balance_after_exit"] = pd.NA
        rejected["portfolio_exit_sequence"] = pd.NA
        audit = pd.concat([selected, rejected], ignore_index=True)
    else:
        audit = selected
    audit = audit.sort_values(
        ["entry_time", "portfolio_status", "instrument"]
    ).reset_index(drop=True)

    pnl = selected["pnl_r"].astype(float)
    wins = int((pnl > 1e-9).sum())
    losses = int((pnl < -1e-9).sum())
    breakeven = int(len(pnl) - wins - losses)
    gross_profit = float(pnl.clip(lower=0).sum())
    gross_loss = float(abs(pnl.clip(upper=0).sum()))
    result = PortfolioResult(
        risk_pct=risk_pct,
        exposure_cap_pct=exposure_cap_pct,
        signals=int(len(trades)),
        accepted_trades=int(len(selected)),
        skipped_signals=int(len(skipped)),
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate_pct=wins / len(selected) * 100.0 if len(selected) else 0.0,
        profit_factor=(
            gross_profit / gross_loss
            if gross_loss
            else inf if gross_profit else 0.0
        ),
        net_r=float(pnl.sum()),
        starting_balance=starting_balance,
        ending_balance=float(balance),
        net_profit=float(balance - starting_balance),
        return_pct=float((balance / starting_balance - 1.0) * 100.0),
        max_realized_drawdown_pct=float(max_realized_dd),
        max_committed_risk_drawdown_pct=float(max_committed_dd),
        max_concurrent_trades=max_active,
        max_planned_exposure_pct=float(max_planned_exposure),
    )
    return result, audit
