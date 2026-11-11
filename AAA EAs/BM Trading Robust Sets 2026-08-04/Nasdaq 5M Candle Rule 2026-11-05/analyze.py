"""Nasdaq 5M, 13 versions side by side (PLAN.md, frozen 2026-11-05 + Addendum 1). Reads the native window runs, the all-years ledgers and the FTMO results;
applies the frozen choice rule. No tester, no new runs.  python analyze.py  -> RESULTS.json, RESULTS.md"""
import gzip, importlib.util, json, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

H = Path(__file__).resolve().parent; sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline'))
import buy_hold, robustness  # noqa: E402
spec = importlib.util.spec_from_file_location('nas', H / 'nas.py'); NAS = importlib.util.module_from_spec(spec); spec.loader.exec_module(NAS)
VERSIONS = list(NAS.VERSIONS); WINDOWS = dict(NAS.WINDOWS); WINDOWS['5y'] = ('2021-11-01', '2026-11-01'); WINDOWS['3y'] = ('2023-11-01', '2026-11-01')
RISKS = ('0.50', '0.75', '1.00')


def ledger(v, w):
    p = H / 'native' / f'nw-USTEC-{v}-{w}'
    meta = json.loads((p / 'run.json').read_text(encoding='utf-8')) if (p / 'run.json').exists() else {}
    if not meta.get('ok'): return None, None
    return sorted(json.loads(gzip.open(p / 'trades.json.gz').read()), key=lambda t: t['close_time']), p


def rows(T):
    bal = 1e4; out = []
    for t in T:
        out.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'])); bal += t['net_profit']
    return out


def stats(x, a, b):
    x = [r for r in x if a <= r['o'][:10] < b]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0); eq = pk = dd = 0.0
    for r in x:
        eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq)
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375; tot = sum(r['r'] for r in x)
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_weekday=round(len(x) / (months * 21.74), 3), total_r=round(tot, 2), pf=round(gw / gl, 3) if gl else None,
                win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), closed_dd_r=round(dd, 2))


def window_run(v, w):
    T, p = ledger(v, w)
    if T is None: return None
    net = sum(t['net_profit'] for t in T); gw = sum(t['net_profit'] for t in T if t['net_profit'] > 0); gl = -sum(t['net_profit'] for t in T if t['net_profit'] < 0)
    a, b = WINDOWS[w]; months = (datetime.fromisoformat(b) - datetime.fromisoformat(max(a, '2019-07-16'))).days / 30.4375
    return dict(trades=len(T), per_month=round(len(T) / months, 2), per_weekday=round(len(T) / (months * 21.74), 3), return_pct=round(net / 100, 2), pf=round(gw / gl, 3) if gl else None,
                win=round(100 * sum(t['net_profit'] > 0 for t in T) / max(1, len(T)), 1), equity_dd_pct=buy_hold.relative_equity_dd(p / f'{p.name}.htm.gz'))


def load(prefix, name, r):
    f = H / f'{prefix}-{name}-{r}.json'
    return json.loads(f.read_text(encoding='utf-8'))['mc'] if f.exists() else None


def main():
    out = dict(versions={}, missing_ftmo=[])
    ctrl, _ = ledger('CONTROL_ATR6_DIOFF', 'all'); ctrl_rows = rows(ctrl) if ctrl else []
    for v in VERSIONS:
        T, _ = ledger(v, 'all'); R = rows(T); a = WINDOWS['all']
        e = dict(windows={w: window_run(v, w) for w in ('dev', 'val', 'oos', 'all')}, from_all={w: stats(R, *WINDOWS[w]) for w in ('dev', 'val', 'oos', 'all', '5y', '3y')})
        tw = robustness.three_monte_carlo([r['r'] for r in R], runs=1000, seed=20261104); oos = [r for r in R if WINDOWS['oos'][0] <= r['o'][:10]]
        tw_oos = robustness.three_monte_carlo([r['r'] for r in oos], runs=1000, seed=20261104) if len(oos) >= 20 else None
        blk = robustness.day_block_bootstrap([dict(close_time=r['c'], estimated_r=r['r']) for r in R], 365, paths=10000)
        e['mc'] = dict(resample_red=tw['resample']['red_pct'], randomize_red=tw['randomize']['both']['red_pct'], clumped=tw['reshuffle']['real_drawdown_worse_than_pct'],
                       oos_resample_red=tw_oos['resample']['red_pct'] if tw_oos else None, oos_randomize_red=tw_oos['randomize']['both']['red_pct'] if tw_oos else None, block_1y=blk)
        ftmo = {}
        for r in RISKS:
            ftmo[r] = dict(two_guard=load('CH', v, r), two_free=load('CH', v + 'U', r), one_guard=load('F1P', v, r), one_free=load('F1U', v + 'U', r), funded_guard=load('FU', v, r), funded_free=load('FU', v + 'U', r))
            out['missing_ftmo'] += [f'{k}-{v}-{r}' for k, x in ftmo[r].items() if x is None]
        e['ftmo'] = ftmo
        w = e['windows']
        e['step1'] = (e['mc']['resample_red'] <= 5 and e['mc']['randomize_red'] <= 10 and all(w[x] and w[x]['return_pct'] > 0 for x in ('dev', 'val', 'oos')))
        if v.startswith('CANDLE'):
            f = e['from_all']; e['candle_raw_gate'] = all(f[x]['total_r'] > 0 and (f[x]['pf'] or 0) >= 1.15 for x in ('3y', '5y')) and f['5y']['trades'] >= 30 and f['all']['total_r'] > stats(ctrl_rows, *WINDOWS['all'])['total_r']
        out['versions'][v] = e
    ok = [v for v, e in out['versions'].items() if e['step1']]
    def best_one(v):
        best = None
        for r in RISKS:
            x = out['versions'][v]['ftmo'][r]['one_guard']
            if x and x['breach'] <= 0.10 and (best is None or x['pass_180'] > best[1]): best = (r, x['pass_180'])
        return best
    ranked = sorted(((v, best_one(v)) for v in ok if best_one(v)), key=lambda z: -z[1][1])
    out['choice'] = dict(eligible=ok, ranked=ranked, pick=ranked[0] if ranked else None, control_all=stats(ctrl_rows, *WINDOWS['all']) if ctrl_rows else None)
    if not ranked:
        least = sorted(out['versions'], key=lambda v: (out['versions'][v]['mc']['randomize_red'], -out['versions'][v]['from_all']['all']['total_r']))[0]
        out['choice']['least_bad_failing'] = least
    out['buy_hold'] = json.loads((H / 'BH_COMPARE.json').read_text(encoding='utf-8')) if (H / 'BH_COMPARE.json').exists() else None
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    L = ['| Version | Trades | /month | /day | Win % | PF | Total R | Closed DD R | Dev % | Val % | OOS % | All % | Equity DD % (all) | MC resample / randomize red % | Step 1 |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for v, e in out['versions'].items():
        a = e['from_all']['all']; w = e['windows']; pct = lambda x: f"{w[x]['return_pct']:+.1f}" if w[x] else '-'  # noqa: E731
        L.append(f"| {v} | {a['trades']} | {a['per_month']} | {a['per_weekday']} | {a['win']} | {a['pf']} | {a['total_r']:+.1f} | {a['closed_dd_r']} | {pct('dev')} | {pct('val')} | {pct('oos')} | {pct('all')} | {w['all']['equity_dd_pct'] if w['all'] else '-'} | {e['mc']['resample_red']} / {e['mc']['randomize_red']} | {'PASS' if e['step1'] else 'fail'} |")
    L += ['', '| Version | Risk | 2-step guard pass / breach | 2-step no guard pass / breach | 1-Step guard pass / breach | 1-Step no guard pass / breach | Funded guard $/month (total median) | Funded no guard $/month (breach) |', '|---|---|---|---|---|---|---|---|']
    for v, e in out['versions'].items():
        for r in RISKS:
            f = e['ftmo'][r]; p = lambda x, k='pass_both_180': f"{100 * x[k]:.0f}% / {100 * x['breach']:.0f}%" if x else '-'  # noqa: E731
            fu = lambda x: f"${x['monthly_income_while_alive_median']:,.0f} (${x['income_total_median'] / 1000:,.0f}k)" if x else '-'  # noqa: E731
            fub = lambda x: f"${x['monthly_income_while_alive_median']:,.0f} ({100 * sum(n for k, n in x['ends'].items() if k not in ('alive', 'frozen')) / x['n']:.0f}%)" if x else '-'  # noqa: E731
            L.append(f"| {v} | {r}% | {p(f['two_guard'])} | {p(f['two_free'])} | {p(f['one_guard'], 'pass_180')} | {p(f['one_free'], 'pass_180')} | {fu(f['funded_guard'])} | {fub(f['funded_free'])} |")
    L += ['', f"Choice (frozen rule): eligible {ok}; ranked {ranked}; pick {out['choice']['pick']}; least bad if none: {out['choice'].get('least_bad_failing')}", f"Missing FTMO results: {len(out['missing_ftmo'])}"]
    (H / 'RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    main()
