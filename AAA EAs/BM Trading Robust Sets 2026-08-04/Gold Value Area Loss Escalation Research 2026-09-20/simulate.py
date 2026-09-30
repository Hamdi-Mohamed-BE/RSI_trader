"""Offline, same-fill Gold Value Area position-sizing replay; no terminal calls."""
from __future__ import annotations
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'Gold Overnight Value Area Pipeline 2026-09-19'
CAPITAL = 10000.0
BASE_RISK = 50.0
PERIODS = ('6m', '1y', '3y', '5y')
PROFILES = ('flat', 'loss_1_5x', 'fixed_75_after_loss')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cash(value):
    return float(Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def timestamp(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo is None:
        raise ValueError('Native trade timestamp must declare its timezone')
    return d.astimezone(timezone.utc)


def target_risk(profile, losses, base=BASE_RISK):
    if profile == 'flat':
        return base
    if profile == 'loss_1_5x':
        return base * 1.5 ** losses
    if profile == 'fixed_75_after_loss':
        return base * (1.5 if losses else 1.0)
    raise ValueError(profile)


def sized_volume(target, unit_risk, rounding, contract):
    if not unit_risk > 0:
        raise ValueError('Missing original stop risk')
    exact = target / unit_risk
    if not rounding:
        return exact
    step = contract['volume_step']
    return min(contract['volume_max'], max(contract['volume_min'], math.ceil(exact / step - 1e-10) * step))


def replay(rows, profile, contract, *, rounding=True, stress=False, initial=CAPITAL, base=BASE_RISK):
    rows = sorted(rows, key=lambda r: (timestamp(r['open_time']), timestamp(r['close_time'])))
    balance = peak = minimum = initial
    losses = wins = max_losses = max_wins = 0
    drawdown = drawdown_cash = envelope_dd = 0.0
    gross_wins = gross_losses = 0.0
    ledger = []
    months = defaultdict(lambda: dict(trades=0, wins=0, net_profit=0.0, commission=0.0, swap=0.0, stress_cost=0.0))
    previous_close = None
    for source_row in rows:
        op, cl = timestamp(source_row['open_time']), timestamp(source_row['close_time'])
        if cl < op or (previous_close is not None and op < previous_close):
            raise ValueError('Overlapping or backwards source trades require event-based replay')
        previous_close = cl
        original_volume = source_row['volume']
        original_risk = source_row['initial_risk_usd']
        if original_volume <= 0 or original_risk <= 0:
            raise ValueError('Invalid source volume or original risk')
        if abs(source_row['gross_profit'] + source_row['commission'] + source_row['swap'] - source_row['net_profit']) > .025:
            raise ValueError('Source cash-flow reconciliation failed')
        desired = target_risk(profile, losses, base)
        unit_risk = original_risk / original_volume
        lot = sized_volume(desired, unit_risk, rounding, contract)
        scale = lot / original_volume
        amounts = {k: source_row[k] * scale for k in ('gross_profit', 'commission', 'swap')}
        extra = .25 * contract['trade_contract_size'] * lot if stress else 0.0
        if stress and amounts['commission'] < 0:
            amounts['commission'] *= 1.5
        if rounding:
            amounts = {k: cash(v) for k, v in amounts.items()}
            extra = cash(extra)
        net = sum(amounts.values()) - extra
        if rounding:
            net = cash(net)
        planned = lot * unit_risk
        envelope = balance - planned + min(0, amounts['commission']) + min(0, amounts['swap']) - extra
        envelope_dd = max(envelope_dd, 100 * (peak - envelope) / peak)
        before = balance
        balance += net
        if rounding:
            balance = cash(balance)
        peak = max(peak, balance)
        minimum = min(minimum, balance)
        dd = 100 * (peak - balance) / peak
        drawdown = max(drawdown, dd)
        drawdown_cash = max(drawdown_cash, peak - balance)
        previous_losses = losses
        if net > 1e-9:
            wins += 1
            losses = 0
            gross_wins += net
        elif net < -1e-9:
            losses += 1
            wins = 0
            gross_losses -= net
        max_losses = max(max_losses, losses)
        max_wins = max(max_wins, wins)
        entry = dict(number=len(ledger) + 1, source_number=source_row['number'], open_time=op.isoformat(), close_time=cl.isoformat(),
                     side=source_row['side'], requested_risk=desired, planned_stop_risk=planned,
                     source_volume=original_volume, volume=lot, multiplier=desired/base,
                     losses_before=previous_losses, losses_after=losses, balance_before=before,
                     **amounts, stress_cost=extra, net_profit=net, balance_after=balance,
                     closed_drawdown_pct=dd, minimum_lot_binding=lot <= contract['volume_min'] + 1e-10 and planned > desired + 1e-8)
        ledger.append(entry)
        monthly = months[cl.strftime('%Y-%m')]
        monthly['trades'] += 1
        monthly['wins'] += net > 1e-9
        for k in ('net_profit', 'commission', 'swap', 'stress_cost'):
            monthly[k] += entry[k]
        if balance <= 0:
            break
    count = len(ledger)
    summary = dict(profile=profile, sizing='broker_rounded' if rounding else 'ideal_fractional', scenario='stress' if stress else 'reference',
                   initial_balance=initial, base_risk=base, final_balance=balance, net_profit=balance-initial,
                   return_pct=100*(balance/initial-1), trades=count,
                   wins=sum(r['net_profit'] > 1e-9 for r in ledger), losses=sum(r['net_profit'] < -1e-9 for r in ledger),
                   win_rate_pct=100*sum(r['net_profit'] > 1e-9 for r in ledger)/count if count else None,
                   profit_factor=gross_wins/gross_losses if gross_losses else None,
                   closed_balance_dd_pct=drawdown, closed_balance_dd_usd=drawdown_cash,
                   initial_stop_envelope_dd_pct=envelope_dd, minimum_closed_balance=minimum,
                   max_requested_risk=max((r['requested_risk'] for r in ledger), default=0),
                   max_planned_stop_risk=max((r['planned_stop_risk'] for r in ledger), default=0),
                   average_planned_stop_risk=sum(r['planned_stop_risk'] for r in ledger)/count if count else 0,
                   max_win_streak=max_wins, max_loss_streak=max_losses,
                   largest_loss=min((r['net_profit'] for r in ledger), default=0),
                   max_volume=max((r['volume'] for r in ledger), default=0),
                   minimum_lot_over_target_trades=sum(r['minimum_lot_binding'] for r in ledger),
                   commission=sum(r['commission'] for r in ledger), swap=sum(r['swap'] for r in ledger),
                   stress_cost=sum(r['stress_cost'] for r in ledger), closed_balance_exhausted=balance<=0,
                   monthly=[dict(month=m, **v) for m,v in sorted(months.items())])
    if abs(sum(r['net_profit'] for r in ledger) - summary['net_profit']) > 1e-6:
        raise AssertionError('Replay cash reconciliation failed')
    return summary, ledger


def main():
    raw = read(SOURCE / 'raw-results.json')
    output = dict(created_utc=datetime.now(timezone.utc).isoformat(), strategy='Raw Gold Overnight Value Area',
                  method='Same native fills, offline sizing replay; closed-balance DD, not tick-equity DD or FTMO eligibility',
                  protocol_sha256=sha(ROOT/'PROTOCOL.md'), simulator_sha256=sha(Path(__file__)), periods={})
    for period in PERIODS:
        src = raw[period]
        folder = SOURCE / 'native' / src['case']
        report = folder / (src['case'] + '.htm')
        if sha(report) != src['report_sha256']:
            raise AssertionError('Native report hash mismatch')
        rows = read(folder/'trades.json')
        run = read(folder/'run.json')
        assert len(rows) == src['trades']
        assert abs(sum(r['net_profit'] for r in rows) - src['net_profit']) < .03
        result = dict(start=run['start'].replace('.', '-'), end_exclusive=run['end_exclusive'].replace('.', '-'),
                      history_quality=src['history_quality'], source_trades_sha256=sha(folder/'trades.json'),
                      source_run_sha256=sha(folder/'run.json'), source_report_sha256=sha(report),
                      source_case=src['case'], original_native_percent_risk_return=src['return_pct'], cases=[])
        for rounding in (False, True):
            for stress in (False, True):
                for profile in PROFILES:
                    summary, ledger = replay(rows, profile, run['contract'], rounding=rounding, stress=stress)
                    file = f"{period}-{summary['sizing']}-{summary['scenario']}-{profile}.json"
                    save(ROOT/file, dict(summary=summary, trades=ledger))
                    result['cases'].append(dict(**summary, ledger=file))
                    if rounding and not stress:
                        print(period, profile, json.dumps({k:summary[k] for k in ('net_profit','return_pct','trades','win_rate_pct','profit_factor','closed_balance_dd_pct','max_requested_risk','max_planned_stop_risk','max_loss_streak','minimum_lot_over_target_trades')}), flush=True)
        output['periods'][period] = result
    save(ROOT/'results.json', output)


if __name__ == '__main__':
    main()
