"""Raw replications for two recent paper ideas on the connected Exness account.

The Treasury test is a documented *core-calendar replication*: exact BLS CPI and
Employment Situation dates, BEA GDP dates, and the DOL weekly-claims schedule
are conditioned on official Treasury auction dates.  ADP, ISM and Conference
Board dates used by the paper are not silently approximated.

The metals test implements the paper's three UTC sessions and the immediately
preceding-session sign rule.  Both the paper's fixed 2 bp turnover charge and
the connected broker's recorded spread plus $3.50/lot/side commission are
reported.  No production files are changed by this script.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import math
import re
import urllib.parse
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
CHARTS = ROOT / "Charts"
TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
START = pd.Timestamp("2021-09-11", tz="UTC")
END = pd.Timestamp("2026-09-11", tz="UTC")
PAPER_START = pd.Timestamp("2024-07-22", tz="UTC")
PAPER_END = pd.Timestamp("2026-08-08", tz="UTC")
NY = ZoneInfo("America/New_York")
COMMISSION_PER_LOT_SIDE = 3.50


@dataclass(frozen=True)
class SymbolMeta:
    canonical: str
    broker_symbol: str
    point: float
    digits: int
    contract_size: float
    swap_mode: int
    swap_long: float
    swap_short: float
    swap_rollover3days: int


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def fetch(url: str) -> tuple[str, dict]:
    request = urllib.request.Request(url, headers={"User-Agent": "CalyxResearch/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
        return raw.decode("utf-8"), {
            "url": url,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "http_status": response.status,
        }


def previous_business_day(day: date) -> date:
    day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def parse_bls(year: int) -> tuple[list[dict], dict]:
    source = f"https://www.bls.gov/schedule/{year}/home.htm"
    text, receipt = fetch("https://r.jina.ai/http://www.bls.gov/schedule/%d/home.htm" % year)
    rows: list[dict] = []
    pattern = re.compile(
        r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
        r"([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+08:30 AM\s+"
        r"(Employment Situation|Consumer Price Index)\b",
        re.I | re.M,
    )
    for match in pattern.finditer(text):
        when = datetime.strptime(match.group(1), "%B %d, %Y").date()
        rows.append({"date": when.isoformat(), "event": match.group(2), "source": source})
    receipt["official_source_url"] = source
    receipt["rows"] = len(rows)
    return rows, receipt


def parse_bea(year: int) -> tuple[list[dict], dict]:
    source = f"https://www.bea.gov/news/schedule/full-{year}"
    text, receipt = fetch("https://r.jina.ai/http://www.bea.gov/news/schedule/full-%d" % year)
    lines = [line.strip() for line in text.splitlines()]
    rows: list[dict] = []
    month_day: str | None = None
    for line in lines:
        if re.fullmatch(r"[A-Za-z]+\s+\d{1,2}", line):
            month_day = line
            continue
        if not month_day or "8:30 AM" not in line or "Gross Domestic Product" not in line:
            continue
        lower = line.lower()
        if "by state" in lower or "puerto rico" in lower or "by county" in lower:
            continue
        when = datetime.strptime(f"{month_day} {year}", "%B %d %Y").date()
        rows.append({"date": when.isoformat(), "event": "Gross Domestic Product", "source": source})
        month_day = None
    receipt["official_source_url"] = source
    receipt["rows"] = len(rows)
    return rows, receipt


def weekly_claim_dates(start: date, end: date) -> list[dict]:
    # DOL states 08:30 every Thursday, with a preceding Wednesday exception
    # when Thursday is a federal holiday.  A small explicit federal-holiday set
    # covers the relevant five-year window.
    holidays = {
        date(2021, 11, 11), date(2021, 11, 25),
        date(2022, 11, 24),
        date(2023, 11, 23),
        date(2024, 7, 4), date(2024, 11, 28),
        date(2025, 6, 19), date(2025, 12, 25),
        date(2026, 1, 1), date(2026, 6, 19), date(2026, 11, 26),
    }
    cursor = start
    while cursor.weekday() != 3:
        cursor += timedelta(days=1)
    rows = []
    while cursor <= end:
        release = cursor - timedelta(days=1) if cursor in holidays else cursor
        rows.append({
            "date": release.isoformat(),
            "event": "Initial Jobless Claims",
            "source": "https://oui.doleta.gov/unemploy/claims_arch.asp",
        })
        cursor += timedelta(days=7)
    return rows


def treasury_auctions(start: date, end: date) -> tuple[list[dict], dict]:
    params = {
        "filter": f"auction_date:gte:{start.isoformat()},auction_date:lte:{end.isoformat()}",
        "page[size]": "5000",
        "sort": "auction_date",
    }
    official = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
    url = official + "?" + urllib.parse.urlencode(params)
    text, receipt = fetch(url)
    payload = json.loads(text)
    rows = payload.get("data", [])
    receipt["official_source_url"] = official
    receipt["rows"] = len(rows)
    return rows, receipt


def build_macro_calendar() -> tuple[pd.DataFrame, set[date], dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    receipts: list[dict] = []
    for year in range(START.year, END.year + 1):
        bls, bls_receipt = parse_bls(year)
        bea, bea_receipt = parse_bea(year)
        rows.extend(bls)
        rows.extend(bea)
        receipts.extend((bls_receipt, bea_receipt))
    rows.extend(weekly_claim_dates(START.date(), END.date()))
    macro = pd.DataFrame(rows).drop_duplicates(["date", "event"]).sort_values(["date", "event"])
    auction_rows, auction_receipt = treasury_auctions((START - pd.Timedelta(days=7)).date(), END.date())
    # The paper studies marketable coupon-bearing Treasury issuance.  Treasury
    # bills would make the recent condition almost permanently true because
    # bills now auction on nearly every business day, which is inconsistent
    # with the paper's reported auction-day counts.
    coupon_rows = [row for row in auction_rows if row.get("security_type") in {"Note", "Bond"}]
    auction_dates = {date.fromisoformat(str(row["auction_date"])[:10]) for row in coupon_rows}
    macro["prior_business_day"] = [previous_business_day(date.fromisoformat(x)).isoformat() for x in macro.date]
    macro["prior_day_had_auction"] = [date.fromisoformat(x) in auction_dates for x in macro.prior_business_day]
    macro.to_csv(DATA / "core-macro-calendar.csv", index=False)
    pd.DataFrame(auction_rows).to_csv(DATA / "treasury-auctions.csv", index=False)
    source_audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "window": [START.isoformat(), END.isoformat()],
        "macro_rows": len(macro),
        "macro_days": int(macro.date.nunique()),
        "auction_rows_all_marketables": len(auction_rows),
        "auction_rows_coupon_notes_bonds": len(coupon_rows),
        "auction_days": len(auction_dates),
        "conditioned_macro_days": int(macro.loc[macro.prior_day_had_auction, "date"].nunique()),
        "coverage_note": (
            "Core-calendar replication only: exact BLS CPI/Employment Situation, exact BEA GDP, "
            "and DOL weekly-claims schedule. The paper's ADP, ISM and Conference Board dates are omitted."
        ),
        "receipts": receipts + [auction_receipt],
    }
    write_json(DATA / "source-audit.json", source_audit)
    return macro, auction_dates, source_audit


def resolve_symbol(canonical: str, names: list[str]) -> str:
    exact = [name for name in names if name.upper() == canonical]
    if exact:
        return exact[0]
    candidates = [name for name in names if name.upper().startswith(canonical)]
    if not candidates:
        raise RuntimeError(f"No broker symbol resolves {canonical}")
    return min(candidates, key=len)


def download_rates() -> tuple[dict[str, pd.DataFrame], dict[str, SymbolMeta], dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=str(TERMINAL)):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    frames: dict[str, pd.DataFrame] = {}
    metas: dict[str, SymbolMeta] = {}
    audit = {"terminal": str(TERMINAL), "downloaded_at_utc": datetime.now(timezone.utc).isoformat(), "symbols": {}}
    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        audit["broker"] = account.company if account else None
        audit["server"] = account.server if account else None
        audit["account_name"] = account.name if account else None
        audit["terminal_build"] = terminal.build if terminal else None
        names = [item.name for item in (mt5.symbols_get() or ())]
        for canonical, timeframe in {
            "EURUSD": mt5.TIMEFRAME_M15,
            "GBPUSD": mt5.TIMEFRAME_M15,
            "USDJPY": mt5.TIMEFRAME_M15,
            "XAUUSD": mt5.TIMEFRAME_M30,
            "XAGUSD": mt5.TIMEFRAME_M30,
        }.items():
            symbol = resolve_symbol(canonical, names)
            mt5.symbol_select(symbol, True)
            rates = mt5.copy_rates_range(symbol, timeframe, START.to_pydatetime(), END.to_pydatetime())
            if rates is None or len(rates) < 5000:
                raise RuntimeError(f"Insufficient history for {symbol}: {0 if rates is None else len(rates)}")
            info = mt5.symbol_info(symbol)
            meta = SymbolMeta(
                canonical, symbol, float(info.point), int(info.digits), float(info.trade_contract_size),
                int(info.swap_mode), float(info.swap_long), float(info.swap_short), int(info.swap_rollover3days),
            )
            idx = pd.to_datetime(rates["time"], unit="s", utc=True)
            frame = pd.DataFrame({key: rates[key].astype(float) for key in ("open", "high", "low", "close", "tick_volume", "spread")}, index=idx)
            frame = frame[~frame.index.duplicated(keep="last")].sort_index()
            positive = frame.loc[frame.spread > 0, "spread"]
            spread_floor = float(positive.median()) if len(positive) else max(float(info.spread), 1.0)
            frame["spread_points_used"] = frame.spread.where(frame.spread > 0, spread_floor)
            frames[canonical] = frame
            metas[canonical] = meta
            np.savez_compressed(DATA / f"{canonical}-{('M15' if timeframe == mt5.TIMEFRAME_M15 else 'M30')}.npz", rates=rates)
            audit["symbols"][canonical] = asdict(meta) | {
                "bars": len(frame), "from": frame.index[0].isoformat(), "to": frame.index[-1].isoformat(),
                "median_positive_spread_points": spread_floor,
            }
    finally:
        mt5.shutdown()
    write_json(DATA / "broker-data-audit.json", audit)
    return frames, metas, audit


def nearest_bar(frame: pd.DataFrame, stamp: pd.Timestamp, tolerance: pd.Timedelta = pd.Timedelta("45min")) -> int | None:
    index = int(frame.index.searchsorted(stamp, side="left"))
    if index >= len(frame.index) or frame.index[index] - stamp > tolerance:
        return None
    return index


def quote_notional_usd(symbol: str, meta: SymbolMeta, price: float) -> float:
    if symbol == "USDJPY":
        return meta.contract_size
    return meta.contract_size * price


def commission_fraction(symbol: str, meta: SymbolMeta, price: float, sides: float = 2.0) -> float:
    return COMMISSION_PER_LOT_SIDE * sides / quote_notional_usd(symbol, meta, price)


def swap_fraction(symbol: str, meta: SymbolMeta, price: float, side: int, multiplier: int = 1) -> float:
    if meta.swap_mode != 1:
        return 0.0
    points = meta.swap_long if side > 0 else meta.swap_short
    quote_cash = points * meta.point * meta.contract_size * multiplier
    usd_cash = quote_cash / price if symbol == "USDJPY" else quote_cash
    return usd_cash / quote_notional_usd(symbol, meta, price)


def performance(returns: pd.Series, periods_per_year: float = 252.0) -> dict:
    clean = pd.Series(returns, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return {"count": 0, "return_pct": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe": 0.0}
    equity = (1.0 + clean).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    wins = clean[clean > 0].sum()
    losses = -clean[clean < 0].sum()
    sd = clean.std(ddof=1)
    return {
        "count": int(len(clean)),
        "return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "profit_factor": float(wins / losses) if losses > 0 else 999.0,
        "win_rate_pct": float((clean > 0).mean() * 100.0),
        "max_drawdown_pct": float(-drawdown.min() * 100.0),
        "sharpe": float(clean.mean() / sd * math.sqrt(periods_per_year)) if sd and math.isfinite(sd) else 0.0,
        "mean_bps": float(clean.mean() * 10000.0),
        "gross_gain_pct": float(wins * 100.0),
        "gross_loss_pct": float(losses * 100.0),
    }


def treasury_test(frames: dict[str, pd.DataFrame], metas: dict[str, SymbolMeta], macro: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    event_rows = []
    qualifying = macro.loc[macro.prior_day_had_auction].groupby("date").event.apply(lambda x: "; ".join(sorted(set(x))))
    for event_iso, event_names in qualifying.items():
        event_day = date.fromisoformat(event_iso)
        auction_day = previous_business_day(event_day)
        entry_stamp = pd.Timestamp(datetime.combine(auction_day, time(17, 0), NY)).tz_convert("UTC")
        exit_stamp = pd.Timestamp(datetime.combine(event_day, time(17, 0), NY)).tz_convert("UTC")
        legs = []
        for symbol, side in (("EURUSD", 1), ("GBPUSD", 1), ("USDJPY", -1)):
            frame, meta = frames[symbol], metas[symbol]
            i = nearest_bar(frame, entry_stamp)
            j = nearest_bar(frame, exit_stamp)
            if i is None or j is None or j <= i:
                continue
            entry_bid = float(frame.open.iloc[i])
            exit_bid = float(frame.open.iloc[j])
            entry_spread = float(frame.spread_points_used.iloc[i]) * meta.point
            exit_spread = float(frame.spread_points_used.iloc[j]) * meta.point
            entry = entry_bid + (entry_spread if side > 0 else 0.0)
            exit_price = exit_bid + (exit_spread if side < 0 else 0.0)
            gross = side * (exit_bid - entry_bid) / entry_bid
            after_spread = side * (exit_price - entry) / entry
            commission = commission_fraction(symbol, meta, entry, 2.0)
            triple = 3 if auction_day.weekday() == meta.swap_rollover3days else 1
            swap = swap_fraction(symbol, meta, entry, side, triple)
            net = after_spread - commission + swap
            pip = meta.point * (10.0 if meta.digits in (3, 5) else 1.0)
            stress = net - 0.50 * pip / entry
            legs.append({
                "event_date": event_iso, "auction_date": auction_day.isoformat(), "events": event_names,
                "symbol": symbol, "side": "long" if side > 0 else "short", "entry_utc": entry_stamp.isoformat(),
                "exit_utc": exit_stamp.isoformat(), "gross_return": gross, "net_return": net,
                "stress_return": stress, "spread_cost": gross - after_spread,
                "commission_cost": commission, "swap_return": swap,
            })
        event_rows.extend(legs)
    legs = pd.DataFrame(event_rows)
    if legs.empty:
        raise RuntimeError("Treasury test produced no trades")
    events = legs.groupby(["event_date", "auction_date", "events"], as_index=False).agg(
        gross_return=("gross_return", "mean"), net_return=("net_return", "mean"), stress_return=("stress_return", "mean"),
        spread_cost=("spread_cost", "mean"), commission_cost=("commission_cost", "mean"), swap_return=("swap_return", "mean"),
        legs=("symbol", "count"),
    )
    events["event_date"] = pd.to_datetime(events.event_date, utc=True)
    by_symbol = []
    for symbol, group in legs.groupby("symbol"):
        by_symbol.append({"scope": symbol, **performance(pd.Series(group.net_return.values, index=pd.to_datetime(group.event_date, utc=True)))})
    daily = pd.Series(events.net_return.values, index=events.event_date)
    daily_gross = pd.Series(events.gross_return.values, index=events.event_date)
    daily_stress = pd.Series(events.stress_return.values, index=events.event_date)
    summary = {
        "strategy": "Treasury Auction-Conditioned FX — core calendar raw",
        "portfolio_gross_paper_style": performance(daily_gross),
        "portfolio": performance(daily),
        "portfolio_0_5pip_stress": performance(daily_stress),
        "by_symbol": by_symbol,
        "events": len(events), "legs": len(legs),
        "costs_pct_of_initial": {
            "spread": float(events.spread_cost.sum() * 100.0),
            "commission": float(events.commission_cost.sum() * 100.0),
            "swap": float(events.swap_return.sum() * 100.0),
        },
        "paper_rule": "Long EURUSD and GBPUSD; short USDJPY from 17:00 ET on the auction day to 17:00 ET on the immediately following macro day.",
        "calendar_scope": "BLS CPI + Employment Situation, BEA GDP, DOL Initial Jobless Claims; ADP/ISM/Conference Board omitted.",
    }
    legs.to_csv(ROOT / "treasury-trades.csv", index=False)
    events.to_csv(ROOT / "treasury-event-portfolio.csv", index=False)
    pd.DataFrame([{"scope": "portfolio gross / paper style", **summary["portfolio_gross_paper_style"]}, {"scope": "portfolio after broker costs", **summary["portfolio"]}, {"scope": "portfolio +0.5 pip", **summary["portfolio_0_5pip_stress"]}, *by_symbol]).to_csv(ROOT / "treasury-results.csv", index=False)
    equity = (1.0 + daily).cumprod()
    plt.figure(figsize=(10, 5.5))
    plt.plot(equity.index, equity.values, label="Core-calendar portfolio, broker costs", linewidth=2)
    plt.axhline(1.0, color="#888", linewidth=0.8)
    plt.title("Treasury Auction-Conditioned FX — Exness raw account")
    plt.ylabel("Growth of $1")
    plt.grid(alpha=0.2)
    plt.legend()
    plt.tight_layout()
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.savefig(CHARTS / "treasury-auction-fx-equity.png", dpi=160)
    plt.close()
    return legs, events, summary


SESSIONS = (
    ("Asia", time(0, 0), time(8, 0)),
    ("Europe", time(8, 0), time(14, 30)),
    ("US", time(14, 30), time(0, 0)),
)


def session_rows(frame: pd.DataFrame, meta: SymbolMeta, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    days = pd.date_range(start.normalize(), end.normalize(), freq="D", tz="UTC")
    for day in days:
        if day.weekday() >= 5:
            continue
        for name, begin_t, finish_t in SESSIONS:
            begin = day + pd.Timedelta(hours=begin_t.hour, minutes=begin_t.minute)
            finish = day + pd.Timedelta(days=1) if finish_t == time(0, 0) else day + pd.Timedelta(hours=finish_t.hour, minutes=finish_t.minute)
            i, j = nearest_bar(frame, begin), nearest_bar(frame, finish)
            if i is None or j is None or j <= i:
                continue
            open_bid, close_bid = float(frame.open.iloc[i]), float(frame.open.iloc[j])
            spread_fraction = float(frame.spread_points_used.iloc[i]) * meta.point / open_bid
            # Exness applies the daily metals rollover during the U.S. session.
            # MT5 encodes Sunday as 0, while pandas encodes Monday as 0.
            crosses_rollover = begin_t <= time(21, 0) < finish_t if finish_t != time(0, 0) else begin_t <= time(21, 0)
            mt5_weekday = (int(day.weekday()) + 1) % 7
            rollover_multiplier = 3 if mt5_weekday == meta.swap_rollover3days else 1
            long_swap = swap_fraction(meta.canonical, meta, open_bid, 1, rollover_multiplier) if crosses_rollover else 0.0
            short_swap = swap_fraction(meta.canonical, meta, open_bid, -1, rollover_multiplier) if crosses_rollover else 0.0
            rows.append({
                "start": begin, "end": finish, "session": name, "open": open_bid, "close": close_bid,
                "return": close_bid / open_bid - 1.0, "spread_fraction": spread_fraction,
                "commission_side_fraction": commission_fraction(meta.canonical, meta, open_bid, 1.0),
                "swap_long_fraction": long_swap, "swap_short_fraction": short_swap,
            })
    return pd.DataFrame(rows).sort_values("start").reset_index(drop=True)


def strategy_session_returns(rows: pd.DataFrame, mode: str, target_session: str | None, cost: str) -> pd.DataFrame:
    out = rows.copy()
    signal = np.sign(out["return"].shift(1)).fillna(0.0)
    if mode == "long-only":
        signal = (signal > 0).astype(float)
    if target_session:
        signal = signal.where(out.session == target_session, 0.0)
    # Weekend gaps are not a preceding trading session in this rule.
    gap = out.start - out.end.shift(1)
    signal = signal.where(gap <= pd.Timedelta("3h"), 0.0)
    out["position"] = signal
    out["turnover"] = (out.position - out.position.shift(1).fillna(0.0)).abs()
    if cost == "paper-2bp":
        out["cost"] = out.turnover * 0.0002
    elif cost == "broker":
        out["cost"] = out.turnover * (out.spread_fraction / 2.0 + out.commission_side_fraction)
    else:
        out["cost"] = 0.0
    swap_return = np.where(out.position > 0, out.swap_long_fraction, np.where(out.position < 0, -out.swap_short_fraction, 0.0))
    out["swap_return"] = swap_return if cost == "broker" else 0.0
    out["strategy_return"] = out.position * out["return"] - out.cost + out.swap_return
    return out


def session_strategy_performance(rows: pd.DataFrame) -> dict:
    daily = rows.set_index("start").strategy_return.resample("1D").sum()
    base = performance(daily, 252.0)
    trade_returns: list[float] = []
    current_position = 0.0
    current_return = 0.0
    for row in rows.itertuples(index=False):
        new_position = float(row.position)
        unit_cost = float(row.cost / row.turnover) if row.turnover else 0.0
        if new_position != current_position:
            if current_position != 0.0:
                current_return -= unit_cost
                trade_returns.append(current_return)
                current_return = 0.0
            if new_position != 0.0:
                current_return = -unit_cost
        if new_position != 0.0:
            current_return += new_position * float(row.return_) + float(row.swap_return)
        current_position = new_position
    if current_position != 0.0:
        trade_returns.append(current_return)
    trades = pd.Series(trade_returns, dtype=float)
    wins = trades[trades > 0].sum()
    losses = -trades[trades < 0].sum()
    base.update({
        "count": int(len(trades)),
        "profit_factor": float(wins / losses) if losses > 0 else 999.0,
        "win_rate_pct": float((trades > 0).mean() * 100.0) if len(trades) else 0.0,
        "mean_bps": float(trades.mean() * 10000.0) if len(trades) else 0.0,
    })
    return base


def metals_test(frames: dict[str, pd.DataFrame], metas: dict[str, SymbolMeta]) -> tuple[pd.DataFrame, dict]:
    all_results = []
    selected_curves = {}
    details = {}
    windows = {"paper-sample": (PAPER_START, PAPER_END), "five-year-transfer": (START, END)}
    variants = (
        ("long-short-all", "long-short", None),
        ("long-only-all", "long-only", None),
        ("long-only-Asia", "long-only", "Asia"),
        ("long-only-Europe", "long-only", "Europe"),
        ("long-only-US", "long-only", "US"),
    )
    for symbol in ("XAUUSD", "XAGUSD"):
        base = session_rows(frames[symbol], metas[symbol], START, END)
        details[symbol] = {}
        for window_name, (begin, finish) in windows.items():
            sliced = base[(base.start >= begin) & (base.end <= finish)].reset_index(drop=True)
            for label, mode, target in variants:
                for cost in ("paper-2bp", "broker"):
                    tested = strategy_session_returns(sliced, mode, target, cost)
                    # itertuples renames the source column named "return" to
                    # ``_6``; expose an identifier-safe alias for trade grouping.
                    tested["return_"] = tested["return"]
                    stats = session_strategy_performance(tested)
                    all_results.append({"symbol": symbol, "window": window_name, "variant": label, "cost_model": cost, **stats})
                    if label == "long-only-all" and cost == "broker":
                        key = f"{symbol} {window_name}"
                        daily = tested.set_index("start").strategy_return.resample("1D").sum()
                        selected_curves[key] = (1.0 + daily).cumprod()
            # Session decomposition is gross and deliberately separate from the strategy.
            decomposition = sliced.groupby("session")["return"].sum().to_dict()
            details[symbol][window_name] = {"sessions": len(sliced), "gross_log_return_approx_pct": {k: float(v * 100.0) for k, v in decomposition.items()}}
    results = pd.DataFrame(all_results)
    results.to_csv(ROOT / "metals-cross-session-results.csv", index=False)
    write_json(ROOT / "metals-session-decomposition.json", details)
    plt.figure(figsize=(10, 5.5))
    for label, curve in selected_curves.items():
        if "paper-sample" in label:
            plt.plot(curve.index, curve.values, label=label.replace(" paper-sample", ""), linewidth=2)
    plt.axhline(1.0, color="#888", linewidth=0.8)
    plt.title("Long-only cross-session momentum — paper sample, broker costs")
    plt.ylabel("Growth of $1")
    plt.grid(alpha=0.2)
    plt.legend()
    plt.tight_layout()
    plt.savefig(CHARTS / "metals-cross-session-equity.png", dpi=160)
    plt.close()
    primary = results[(results.variant == "long-only-all") & (results.cost_model == "broker")].to_dict("records")
    return results, {"strategy": "Gold/Silver Cross-Session Momentum", "primary": primary, "decomposition": details}


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def build_report(source_audit: dict, broker_audit: dict, treasury: dict, metals_results: pd.DataFrame, metals_summary: dict) -> None:
    t = treasury["portfolio"]
    treasury_rows = [
        "| Scope | Events/trades | Return | PF | Win rate | Max DD | Sharpe | Mean/event |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| 3-leg portfolio after broker costs | {treasury['events']} events / {treasury['legs']} legs | {fmt(t['return_pct'])}% | {fmt(t['profit_factor'])} | {fmt(t['win_rate_pct'])}% | {fmt(t['max_drawdown_pct'])}% | {fmt(t['sharpe'])} | {fmt(t['mean_bps'])} bps |",
    ]
    gross = treasury["portfolio_gross_paper_style"]
    treasury_rows.insert(2, f"| 3-leg portfolio gross / paper style | {treasury['events']} events / {treasury['legs']} legs | {fmt(gross['return_pct'])}% | {fmt(gross['profit_factor'])} | {fmt(gross['win_rate_pct'])}% | {fmt(gross['max_drawdown_pct'])}% | {fmt(gross['sharpe'])} | {fmt(gross['mean_bps'])} bps |")
    for row in treasury["by_symbol"]:
        treasury_rows.append(
            f"| {row['scope']} | {row['count']} | {fmt(row['return_pct'])}% | {fmt(row['profit_factor'])} | {fmt(row['win_rate_pct'])}% | {fmt(row['max_drawdown_pct'])}% | {fmt(row['sharpe'])} | {fmt(row['mean_bps'])} bps |"
        )
    s = treasury["portfolio_0_5pip_stress"]
    treasury_rows.append(f"| Portfolio +0.5 pip stress | {s['count']} | {fmt(s['return_pct'])}% | {fmt(s['profit_factor'])} | {fmt(s['win_rate_pct'])}% | {fmt(s['max_drawdown_pct'])}% | {fmt(s['sharpe'])} | {fmt(s['mean_bps'])} bps |")

    primary = metals_results[(metals_results.variant == "long-only-all")]
    metal_rows = [
        "| Symbol | Window | Cost model | Sessions/days | Return | PF | Win rate | Max DD | Sharpe |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in primary.to_dict("records"):
        metal_rows.append(
            f"| {row['symbol']} | {row['window']} | {row['cost_model']} | {int(row['count'])} | {fmt(row['return_pct'])}% | {fmt(row['profit_factor'])} | {fmt(row['win_rate_pct'])}% | {fmt(row['max_drawdown_pct'])}% | {fmt(row['sharpe'])} |"
        )

    report = f"""# Treasury Auction FX and Gold/Silver Cross-Session Momentum — raw research

Generated: {datetime.now(timezone.utc).date().isoformat()}

## Verdict

These are **research-only raw replications**. Nothing was added to the website, BAT files or live MT5 account. The Treasury result is a conservative core-calendar replication rather than a claim of exact parity with the authors' Bloomberg calendar. The metals paper has only a two-year, strongly bullish published sample and no independent out-of-sample evidence.

## 1. Treasury Auction-Conditioned FX

### Mechanical rule tested

1. Identify a monitored U.S. macro release day whose immediately preceding business day had a coupon Treasury note or bond auction.
2. At 17:00 New York time on the auction day, buy EURUSD and GBPUSD and sell USDJPY in equal weights.
3. Close all three legs at 17:00 New York on the macro day. There is no stop, target or trailing rule in the paper's raw return construction.
4. Use the connected Exness account's recorded bar spreads, $3.50 per lot per side commission and the terminal's current swap-point schedule. The stress row adds another 0.5 pip round trip.

### Connected-account result

{chr(10).join(treasury_rows)}

Exact evidence window: {START.date()} through {END.date()}. Official-source calendar contains {source_audit['macro_days']} core macro days and {source_audit['conditioned_macro_days']} auction-conditioned days before intersecting tradable bars.

### Fidelity limit

The accessible official calendar covers BLS CPI and Employment Situation, BEA GDP and DOL Initial Jobless Claims. The paper also used ADP Employment, ISM Manufacturing and Conference Board Consumer Confidence. Those three series were omitted rather than guessed. Therefore this is a **core-calendar replication**, not a paper-exact reproduction. The authors' headline total-return chart also abstracts from transaction costs; our headline above is after observable broker costs.

### Pipeline recommendation

**Skip.** The recent five-year three-pair portfolio is negative after broker costs; the added 0.5-pip stress is worse. The gross return is too small to survive spread, commission and swap, so a parameter search would be trying to manufacture an edge absent from the raw executable rule.

## 2. Gold/Silver Cross-Session Momentum

### Mechanical rule tested

UTC sessions are Asia 00:00–08:00, Europe 08:00–14:30 and US 14:30–24:00. At each session open, take the sign of the immediately preceding session's return. The long-only variant holds one unit only after a positive preceding session and otherwise stays flat. Positions are recalculated at every boundary; weekends reset the signal.

{chr(10).join(metal_rows)}

The `paper-2bp` rows apply the paper's 0.02% charge per unit of position change. The `broker` rows use the connected Exness account's recorded spreads plus $3.50/lot/side commission and charge the recorded long/short swap whenever a position survives the U.S.-session rollover. Weekends reset the signal.

### Interpretation

The paper-sample row is the closest comparison to the authors' 22 July 2024–7 August 2026 sample. The five-year transfer is the important robustness check because the published sample was a large precious-metals bull market. Session decomposition and every tested raw variant are retained in the CSV, including Asia-only, Europe-only, US-only and long/short versions; none is promoted automatically.

### Pipeline recommendation

**The approved XAUUSD full pipeline is complete and failed the strict research gate; skip XAGUSD.** The selected XAU configuration stayed profitable in the locked year, but its 10,000-path bootstrap P5 return was negative and only half of nearby parameter settings were profitable. It was therefore not promoted or deployed. Silver remains rejected because it loses over the five-year transfer.

## Sources and audit trail

- Krohn and Vala, *Auctions, Announcements, and Abnormal Returns*, April 2025/updated 2026.
- U.S. Treasury Fiscal Data auction API (`auctions_query`).
- BLS annual release schedules, BEA annual release schedules and the DOL UI Weekly Claims publication schedule.
- Wei, *Who Moves the Price? Trading-Session Return Decomposition and Cross-Session Momentum in Gold and Silver Markets*, August 2026.
- Broker: {broker_audit.get('broker')} / {broker_audit.get('server')} / account type {broker_audit.get('account_name')}.

## Files

- `treasury-results.csv` — headline and per-pair statistics.
- `treasury-event-portfolio.csv` and `treasury-trades.csv` — auditable event and leg returns.
- `metals-cross-session-results.csv` — all raw variants, both cost models and both windows.
- `metals-session-decomposition.json` — gross session attribution.
- `Data/source-audit.json` and `Data/broker-data-audit.json` — source receipts and broker metadata.
- `Charts/` — equity curves.
"""
    (ROOT / "RAW RESULTS.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", choices=("treasury", "metals", "all"), default="all")
    args = parser.parse_args()
    CHARTS.mkdir(parents=True, exist_ok=True)
    frames, metas, broker_audit = download_rates()
    saved = {}
    summary_path = ROOT / "research-summary.json"
    if summary_path.exists():
        saved = json.loads(summary_path.read_text(encoding="utf-8"))
    if args.study in ("treasury", "all"):
        macro, _auction_dates, source_audit = build_macro_calendar()
        _legs, _events, treasury = treasury_test(frames, metas, macro)
        saved["treasury"] = treasury
    if args.study in ("metals", "all"):
        metals_results, metals_summary = metals_test(frames, metas)
        saved["metals"] = metals_summary
    write_json(summary_path, saved)
    if "treasury" in saved and "metals" in saved and (ROOT / "metals-cross-session-results.csv").exists():
        source_audit = json.loads((DATA / "source-audit.json").read_text(encoding="utf-8"))
        metals_results = pd.read_csv(ROOT / "metals-cross-session-results.csv")
        build_report(source_audit, broker_audit, saved["treasury"], metals_results, saved["metals"])
        print(ROOT / "RAW RESULTS.md")
    else:
        print(summary_path)


if __name__ == "__main__":
    main()
