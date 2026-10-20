"""Research-only past-data DXY entry-veto screen; no MT5/trading imports."""
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent
HOUR = 3600
DAY = 86400


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, obj):
    Path(path).write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False)+"\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def epoch(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int((stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)).timestamp())


def day_name(value):
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d")


def trade_id(row):
    return f"{row['key']}:{int(row['position_id'])}"


def close_order(row):
    return (int(row["cl"]), int(row["op"]), row["key"], int(row["position_id"]))


class HourlySeries:
    def __init__(self, bars):
        self.ends, self.closes = [], []
        for bar in bars:
            start = epoch(bar["time"]) if isinstance(bar["time"], str) else int(bar["time"])
            close = float(bar["close"])
            if start % HOUR or not math.isfinite(close) or close <= 0:
                raise ValueError("Invalid/non-hourly bar")
            if self.ends and start+HOUR <= self.ends[-1]:
                raise ValueError("Duplicate or unordered bar")
            self.ends.append(start+HOUR)
            self.closes.append(close)
        self.returns = {}
        for i in range(1, len(self.ends)):
            if self.ends[i]-self.ends[i-1] == HOUR:
                self.returns[self.ends[i]] = math.log(self.closes[i]/self.closes[i-1])
        self.return_times = sorted(self.returns)

    def audit(self):
        return dict(bars=len(self.ends), valid_one_hour_returns=len(self.returns),
                    first_bar_open=self.ends[0]-HOUR if self.ends else None,
                    last_bar_close=self.ends[-1] if self.ends else None,
                    missing_one_hour_intervals=sum(max(0, (b-a)//HOUR-1) for a,b in zip(self.ends,self.ends[1:])))


def feature_at(entry, dxy, gold, plan):
    rules = plan["rules"]
    out = dict(entry_epoch=int(entry), valid=False, reason="no_completed_dxy_bar", veto_long=False,
               veto_short=False, correlation_valid=False, correlation=None, correlation_n=0)
    i = bisect_right(dxy.ends, entry)-1
    if i < 0:
        return out
    end = dxy.ends[i]
    out.update(dxy_last_close_epoch=end, dxy_age_seconds=entry-end)
    if entry-end > rules["maximum_closed_bar_age_seconds"]:
        out["reason"] = "stale_dxy"
        return out
    span = rules["signal_clock_hours"]
    if i < span or any(dxy.ends[i-j] != end-j*HOUR for j in range(span+1)):
        out["reason"] = "nonconsecutive_signal_hours"
        return out
    signal_start = end-span*HOUR
    minimum_time = entry-rules["volatility_history_max_calendar_days"]*DAY
    left = bisect_left(dxy.return_times, minimum_time)
    right = bisect_right(dxy.return_times, signal_start)
    times = dxy.return_times[max(left, right-rules["volatility_returns"]):right]
    out.update(signal_start_epoch=signal_start, signal_end_epoch=end, normalizer_n=len(times))
    if len(times) < rules["volatility_returns"]:
        out["reason"] = "insufficient_normalizer"
        return out
    sd = statistics.stdev(dxy.returns[t] for t in times)
    if not math.isfinite(sd) or sd <= 0:
        out["reason"] = "zero_or_invalid_volatility"
        return out
    r3 = math.log(dxy.closes[i]/dxy.closes[i-span])
    threshold = math.sqrt(span)*sd*rules["threshold_sigma_multiplier"]
    out.update(valid=True, reason="valid", momentum=r3, volatility=sd, threshold=threshold,
               signal_z=r3/threshold, normalizer_first_epoch=times[0], normalizer_last_epoch=times[-1],
               veto_long=r3 >= threshold, veto_short=r3 <= -threshold)
    paired = [t for t in dxy.return_times[bisect_left(dxy.return_times, entry-rules["correlation_max_calendar_days"]*DAY):bisect_right(dxy.return_times,end)] if t in gold.returns]
    paired = paired[-rules["correlation_observations"]:]
    out["correlation_n"] = len(paired)
    if len(paired) >= rules["correlation_minimum"]:
        out.update(correlation_first_epoch=paired[0], correlation_last_epoch=paired[-1])
        if entry-paired[-1] > rules["correlation_maximum_endpoint_age_seconds"]:
            out["correlation_reason"] = "stale_paired_gold_dxy_returns"
            return out
        try:
            rho = statistics.correlation([dxy.returns[t] for t in paired], [gold.returns[t] for t in paired])
        except statistics.StatisticsError:
            rho = None
        if rho is not None and math.isfinite(rho):
            out.update(correlation_valid=True, correlation=rho)
    return out


def annotate(row, dxy, gold, plan):
    f = feature_at(int(row["op"]), dxy, gold, plan)
    direction = row["side"]
    if direction not in ("Long", "Short"):
        raise ValueError("Unknown trade side")
    veto = bool(f["valid"] and f["veto_long" if direction == "Long" else "veto_short"])
    conditional = bool(veto and f["correlation_valid"] and f["correlation"] <= -0.25)
    return dict(id=trade_id(row), key=row["key"], position_id=int(row["position_id"]),
                side=direction, op=int(row["op"]), cl=int(row["cl"]),
                primary_veto=veto, secondary_veto=conditional, **f)


def net_r(row, stress=False, plan=None):
    risk = float(row["unit_risk"])
    if not math.isfinite(risk) or risk <= 0:
        raise ValueError("Invalid source stop risk")
    value = sum(float(row[k]) for k in ("unit_gross", "unit_comm", "unit_swap"))
    if stress:
        value -= plan["stress"]["extra_per_lot_roundtrip"]
        if plan["stress"]["double_negative_recorded_swap"]:
            value += min(0., float(row["unit_swap"]))
    if not math.isfinite(value):
        raise ValueError("Invalid source net")
    return value/risk


def metric_pack(rows, start, end, stress, plan):
    rows = sorted(rows, key=close_order)
    initial = float(plan["metrics"]["initial_reference_balance"])
    allocation = float(plan["metrics"]["fixed_initial_stop_risk"])
    ns = [net_r(r, stress, plan) for r in rows]
    cash = [v*allocation for v in ns]
    wins = [v for v in cash if v > 1e-10]
    losses = [v for v in cash if v < -1e-10]
    balance = peak = initial
    nonpositive_closed_balance = False
    dd = dd_pct = 0.
    cw = cl = mw = ml = 0
    curve = [dict(epoch=start, balance=initial)]
    daily_cash = defaultdict(float)
    for row, value in zip(rows, cash):
        balance += value
        nonpositive_closed_balance = nonpositive_closed_balance or balance <= 0
        peak = max(peak, balance)
        dd = max(dd, peak-balance)
        dd_pct = max(dd_pct, 100*(peak-balance)/peak)
        cw = cw+1 if value > 1e-10 else 0
        cl = cl+1 if value < -1e-10 else 0
        mw, ml = max(mw,cw), max(ml,cl)
        curve.append(dict(epoch=int(row["cl"]),balance=balance))
        daily_cash[day_name(int(row["cl"]))] += value
    monthly = {}
    daily_returns = []
    daily_balance = initial
    for t in range(start, end, DAY):
        date = day_name(t)
        net = daily_cash[date]
        daily_returns.append(net/daily_balance if daily_balance > 0 else None)
        daily_balance += net
        key = date[:7]
        if key not in monthly:
            monthly[key] = dict(month=key, net_profit=0.,net_r=0.,trades=0)
        monthly[key]["net_profit"] += net
        monthly[key]["net_r"] += net/allocation
    for row in rows:
        monthly[day_name(int(row["cl"]))[:7]]["trades"] += 1
    valid = bool(daily_returns) and not nonpositive_closed_balance and all(v is not None for v in daily_returns)
    sd = statistics.stdev(daily_returns) if valid and len(daily_returns)>1 else 0.
    sharpe = statistics.mean(daily_returns)/sd*math.sqrt(365) if valid and sd>0 else None
    n = len(rows)
    metrics = dict(trades=n, wins=len(wins),losses=len(losses),breakevens=n-len(wins)-len(losses),
        longs=sum(r["side"]=="Long" for r in rows),shorts=sum(r["side"]=="Short" for r in rows),
        win_rate_pct=100*len(wins)/n if n else None,
        profit_factor=sum(wins)/(-sum(losses)) if losses else None,
        net_r=sum(ns),net_profit=sum(cash),closed_return_pct=100*sum(cash)/initial,
        ending_closed_reference_balance=balance,expectancy_r=sum(ns)/n if n else None,
        average_win=sum(wins)/len(wins) if wins else None,
        average_loss=sum(losses)/len(losses) if losses else None,
        max_closed_dd_cash=dd,max_closed_dd_pct=dd_pct,max_winning_streak=mw,max_losing_streak=ml,
        closed_daily_sharpe=sharpe,calendar_days=(end-start)//DAY,
        average_closed_trades_per_calendar_day=n/((end-start)/DAY))
    return dict(metrics=metrics,curve=curve,monthly=list(monthly.values()))


def make_result(source_rows, features, ea, period, cost, view, plan):
    start,end = epoch(period["start"]),epoch(period["end_exclusive"])
    rows = [r for r in source_rows if r["op"] >= start and r["cl"] < end and (ea=="combined" or r["key"]==ea)]
    stress = cost=="stress"
    veto_key = "primary_veto" if view=="primary" else "secondary_veto"
    selected = rows if view=="baseline" else [r for r in rows if not features[trade_id(r)][veto_key]]
    vetoed = [] if view=="baseline" else [r for r in rows if features[trade_id(r)][veto_key]]
    valid_rows = [r for r in rows if features[trade_id(r)]["valid"] and (view!="secondary" or features[trade_id(r)]["correlation_valid"])]
    selected_valid = valid_rows if view=="baseline" else [r for r in valid_rows if not features[trade_id(r)][veto_key]]
    pack = metric_pack(selected,start,end,stress,plan)
    pack.update(period=period["id"],ea=ea,cost=cost,view=view,
        start=period["start"],end_exclusive=period["end_exclusive"],
        selected_ids=[trade_id(r) for r in sorted(selected,key=close_order)],
        vetoed_ids=[trade_id(r) for r in sorted(vetoed,key=close_order)],
        vetoed_metrics=metric_pack(vetoed,start,end,stress,plan)["metrics"],
        common_valid=dict(candidates=len(valid_rows),baseline=metric_pack(valid_rows,start,end,stress,plan)["metrics"],filtered=metric_pack(selected_valid,start,end,stress,plan)["metrics"]),
        coverage=dict(candidates=len(rows),primary_valid=sum(features[trade_id(r)]["valid"] for r in rows),
                      correlation_valid=sum(features[trade_id(r)]["correlation_valid"] for r in rows),
                      unavailable_reasons=dict(Counter(features[trade_id(r)]["reason"] for r in rows if not features[trade_id(r)]["valid"])),
                      vetoed=len(vetoed),retention_pct=100*len(selected)/len(rows) if rows else None,
                      pre_window_entries_excluded=sum(r["op"]<start and start<=r["cl"]<end and (ea=="combined" or r["key"]==ea) for r in source_rows)))
    return pack


def freeze():
    inputs = read(ROOT/"INPUTS.json")
    paths = [ROOT/"PLAN.json", ROOT/"INPUTS.json", ROOT/"run.py", ROOT/"prepare_sources.py", ROOT/"SOURCE AUDIT.json"]
    paths += sorted((ROOT/"data").glob("*.json"))
    assert not (ROOT/"RESULTS.json").exists(), "Do not refreeze after outcomes exist"
    source_hashes = inputs["source_hashes"]
    assert all(sha(p)==v for p,v in source_hashes.items()), "Source evidence changed"
    save(ROOT/"FROZEN.json",dict(status="FROZEN before feature/outcome computation",files={str(p):sha(p) for p in paths},source_files=source_hashes))
    print(json.dumps(dict(status="FROZEN",files=len(paths),source_files=len(source_hashes))))


def verify_freeze():
    receipt = read(ROOT/"FROZEN.json")
    for group in ("files","source_files"):
        for path,digest in receipt[group].items():
            if sha(path)!=digest:
                raise ValueError("Frozen input changed: "+path)
    return receipt


def main():
    verify_freeze()
    plan=read(ROOT/"PLAN.json")
    source=read(ROOT/"INPUTS.json")
    rows=source["rows"]
    dxy=HourlySeries(read(ROOT/"data/DXY-H1.json")["bars"])
    gold=HourlySeries(read(ROOT/"data/XAUUSD-H1.json")["bars"])
    annotated=[annotate(r,dxy,gold,plan) for r in rows]
    features={r["id"]:r for r in annotated}
    assert len(features)==len(rows)
    results=[make_result(rows,features,ea,period,cost,view,plan)
             for period in plan["periods"] for ea in (*plan["scope"],"combined")
             for cost in ("recorded","stress") for view in ("baseline","primary","secondary")]
    save(ROOT/"RESULTS.json",dict(status="COMPLETE research-only immutable trade-subset screen",plan_sha256=sha(ROOT/"PLAN.json"),inputs_sha256=sha(ROOT/"INPUTS.json"),frozen_sha256=sha(ROOT/"FROZEN.json"),
        data_audit=dict(dxy=dxy.audit(),gold=gold.audit()),features=annotated,results=results))
    print(json.dumps(dict(status="COMPLETE",source_positions=len(rows),comparisons=len(results),results_sha256=sha(ROOT/"RESULTS.json"))))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--freeze",action="store_true")
    args=parser.parse_args()
    freeze() if args.freeze else main()
