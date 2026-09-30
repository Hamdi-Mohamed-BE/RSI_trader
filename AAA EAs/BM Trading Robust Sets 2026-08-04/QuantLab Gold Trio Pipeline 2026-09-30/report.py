"""Builds RESULTS.md, graphs and robustness (Monte Carlo) from the frozen pipeline outputs. Reads only saved evidence."""
from pathlib import Path
import gzip, io, json, subprocess, sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'native'
MC = ROOT / 'robustness'
PIPE = ROOT.parent.parent / 'Calyx Research Pipeline' / 'calyx_pipeline.py'
rng = np.random.default_rng(300930)

TF = {5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4', 1440: 'D1'}
SESS = ['all hours', 'Asia 00-08 UTC', 'London 07-16 UTC', 'New York 09:30-16:00', 'overlap 12-16 UTC', 'NY open 09:30-11:00']
FILT = ['no filter', 'EMA200 bias', 'H4 EMA50 bias', 'ADX>=20', 'ATR percentile 20-80', 'spread<=0.1 ATR', 'D1 EMA50 bias']
DAYX = ['all weekdays', 'no Monday', 'no Friday', 'no Monday/Friday']
SEASON = ['all year', 'Q4 only', 'Jul-Dec only']
DIRN = ['long+short', 'long only', 'short only']
MOD = {0: 'A momentum', 1: 'B breakout', 2: 'C turn of month'}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def describe(c):
    m = int(c['module'])
    parts = [MOD[m]]
    if m != 2:
        parts.append(TF[int(c['tf'])])
        e = int(c['entry'])
        parts.append(['market at next bar', 'confirmation candle', f'limit {c["offset"]} ATR', f'stop-entry {c["offset"]} ATR'][e])
    else:
        parts.append('entry at session open' if c['p3'] == 0 else f'entry from {c["p3"]:g}h UTC')
    st = int(c['stop'])
    parts.append([f'stop {c["sl"]:g} ATR', f'stop {c["sl"]:g}% of price', 'stop 5-bar swing', 'stop 20-bar structure'][st])
    parts.append(f'target {c["rr"]:g}R' if c['rr'] > 0 else 'no target')
    t = int(c['trail'])
    parts.append(['no trail', f'breakeven at {c["start"]:g}R', f'trail at initial distance from {c["start"]:g}R',
                  f'ATR trail {c["dist"]:g} ATR from {c["start"]:g}R', f'{c["dist"]:g}% trail from {c["start"]:g}R', 'EMA20 trail from 1R'][t])
    if int(c['exit']) == 1:
        parts.append(f'time exit {int(c["hold"])} bars')
    if int(c['exit']) == 3:
        parts.append('50% partial at 1R')
    if m != 2:
        parts += [SESS[int(c['session'])], DIRN[int(c['direction'])]]
    parts.append(FILT[int(c['filter'])])
    if int(c['day']):
        parts.append(DAYX[int(c['day'])])
    if int(c['max_day']):
        parts.append(f'max {int(c["max_day"])}/day')
    if int(c['flat']):
        parts.append(['', 'flat daily', 'flat before weekend'][int(c['flat'])])
    if int(c['season']):
        parts.append(SEASON[int(c['season'])])
    if m == 0:
        parts.append(f'lookback {int(c["p1"])}, threshold {c["p2"]:g} ATR, EMA{int(c["p3"])}{"" if c["p4"] else ", no breakout"}')
    elif m == 1:
        parts.append(f'range {int(c["p1"])}, breakout {int(c["p2"])}, edge {c["p3"]:g}, vol window {int(c["p4"]) or "off"}')
    else:
        parts.append(f'enter day {int(c["p1"])}, exit trading day +{int(c["p2"])}')
    return ' · '.join(parts)


COLS = [('trades', 'Trades', '{:d}'), ('trades_per_month', '/month', '{:.1f}'), ('trades_per_day', '/day', '{:.2f}'), ('return_pct', 'Return', '{:+.1f}%'),
        ('pf', 'PF', '{:.2f}'), ('win_pct', 'Win', '{:.1f}%'), ('consistency_pct', 'Consist.', '{:.0f}%'), ('streaks', 'Streaks W/L avg (max)', '{}'),
        ('sharpe', 'Sharpe', '{:.2f}'), ('balance_dd_pct', 'Bal DD', '{:.1f}%'), ('equity_dd_pct', 'Eq DD', '{:.1f}%')]


def cells(st):
    out = []
    for k, _, f in COLS:
        if k == 'streaks':
            v = f'{st["avg_win_streak"] or 0:.1f}/{st["avg_loss_streak"] or 0:.1f} ({st["max_win_streak"]}/{st["max_loss_streak"]})'
        else:
            v = st.get(k)
            v = '—' if v is None else f.format(v)
        out.append(v)
    return out


def table(rows):
    head = '| Case | ' + ' | '.join(h for _, h, _ in COLS) + ' |'
    sep = '|---|' + '---:|' * len(COLS)
    return '\n'.join([head, sep] + ['| ' + label + ' | ' + ' | '.join(cells(st)) + ' |' for label, st in rows])


def ledger(name, i=0):
    return pd.read_csv(io.BytesIO(gzip.decompress((OUT / name / f'{i}-trades.csv.gz').read_bytes())))


def robustness(label, folder, trials):
    """calyx_pipeline bootstrap/DSR + our reshuffle/removal + measured-slippage cost stress on a native 5y report."""
    MC.mkdir(exist_ok=True)
    rep = next((OUT / folder).glob('*.htm.gz'))
    htm = MC / (folder + '.htm')
    htm.write_bytes(gzip.decompress(rep.read_bytes()))
    d = ledger(folder)
    sig_path = OUT / folder / '0-signals.csv.gz'
    extra = None
    if sig_path.exists():
        sig = pd.read_csv(io.BytesIO(gzip.decompress(sig_path.read_bytes())))
        j = d.merge(sig[['position_id', 'actual_side', 'quote', 'fill']], on='position_id', how='inner')
        adverse = (j.actual_side * (j.fill - j.quote)).clip(lower=0) * j.volume * 100  # XAUUSD contract 100 oz
        extra = round(float(adverse.mean()), 4) if len(adverse) else None
    cmd = [sys.executable, str(PIPE), '--report', str(htm), '--label', label, '--output', str(MC / folder), '--paths', '10000', '--block', '5',
           '--tested-configurations', str(trials), '--daily-loss-limit', '5', '--total-loss-limit', '10']
    if extra:
        cmd += ['--extra-cost-per-trade', str(extra)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    audit = load(next((MC / folder).glob('*.json')) if not (MC / folder / 'summary.json').exists() else [p for p in (MC / folder).glob('*.json') if p.name != 'summary.json'][0])
    p = d.sort_values('close_epoch').net_profit.to_numpy()

    def maxdd(seq):
        bal = 10000 + np.cumsum(seq)
        peak = np.maximum.accumulate(np.concatenate([[10000], bal]))[1:]
        return float(((peak - bal) / peak).max() * 100)

    def maxloss(seq):
        best = cur = 0
        for x in seq:
            cur = cur + 1 if x < 0 else 0
            best = max(best, cur)
        return best
    shuf_dd, shuf_ls = [], []
    for _ in range(2000):
        q = rng.permutation(p)
        shuf_dd.append(maxdd(q))
        shuf_ls.append(maxloss(q))
    removal = {}
    for pct in (10, 20):
        nets, pfs = [], []
        for _ in range(2000):
            keep = p[rng.random(len(p)) >= pct / 100]
            nets.append(keep.sum() / 100)
            gl = -keep[keep < 0].sum()
            pfs.append(keep[keep > 0].sum() / gl if gl else np.nan)
        removal[pct] = dict(return_p05=round(float(np.percentile(nets, 5)), 2), return_p50=round(float(np.percentile(nets, 50)), 2),
                            pf_p05=round(float(np.nanpercentile(pfs, 5)), 3))
    return dict(label=label, verdict=audit['verdict'], metrics={k: audit['metrics'][k] for k in ('trades', 'return_pct', 'profit_factor', 'win_rate_pct', 'annualized_sharpe', 'deflated_sharpe_pct', 'recent_half_profit_factor', 'profitable_thirds')},
                bootstrap={k: audit['bootstrap'].get(k) for k in ('paths', 'probability_profit_pct', 'return_p05_pct', 'return_p50_pct', 'return_p95_pct', 'profit_factor_p05', 'profit_factor_p50', 'max_drawdown_p50_pct', 'max_drawdown_p95_pct', 'closed_pnl_daily_limit_breach_pct', 'closed_pnl_total_limit_breach_pct')},
                gates=audit['gates'], cost_stress=audit['cost_stress'], measured_extra_cost_per_trade=extra,
                reshuffle=dict(max_dd_p50=round(float(np.percentile(shuf_dd, 50)), 2), max_dd_p95=round(float(np.percentile(shuf_dd, 95)), 2),
                               loss_streak_p50=int(np.percentile(shuf_ls, 50)), loss_streak_p95=int(np.percentile(shuf_ls, 95))),
                removal=removal, tested_configurations=trials)


def graphs(frozen, combos):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    ax = axes[0]
    for label, c in combos.items():
        folder = [f.name for f in OUT.glob(f'combo-{label.split()[0].lower()}-{len(c["members"])}-{"".join(x[0] for x in c["members"])}-5y')]
        if not folder:
            continue
        tr = pd.read_csv(io.BytesIO(gzip.decompress((OUT / folder[0] / '0-trace.csv.gz').read_bytes())))
        t = pd.to_datetime(tr.time, unit='s')
        line = ax.plot(t, tr.balance, lw=1.6, label=f'{label} balance')[0]
        ax.plot(t, tr.equity, lw=.6, alpha=.45, color=line.get_color())
    ax.axhline(10000, color='grey', lw=.7, ls='--')
    ax.set_title('Gold Trio optimised · native MT5 Model 4 · 5 years · 1% risk per module (thin = equity)')
    ax.legend(fontsize=8, loc='upper left')
    for ax, obj in zip(axes[1:], ('best', 'prop')):
        d5 = [f for f in OUT.glob('frozen-5y')][0]
        res = load(d5 / 'results.json')
        for m in 'ABC':
            k = f'{m}-{obj}'
            if k not in frozen:
                continue
            i = frozen[k]['case_index']
            d = ledger('frozen-5y', i).sort_values('close_epoch')
            ax.step(pd.to_datetime(d.close_epoch, unit='s'), 10000 + d.net_profit.cumsum(), where='post', lw=1.2, label=f'{k} ({frozen[k]["verdict"]})')
        ax.axhline(10000, color='grey', lw=.7, ls='--')
        ax.set_ylabel(f'{obj.upper()} picks, closed balance')
        ax.legend(fontsize=8, loc='upper left')
    for ax in axes:
        for x, lab in [('2021-09-29', 'dev'), ('2024-03-29', 'validation'), ('2025-09-29', 'recent')]:
            ax.axvline(pd.Timestamp(x), color='#999', lw=.6, ls=':')
    fig.tight_layout()
    fig.savefig(ROOT / 'balance-5y.png', dpi=130)


def main():
    frozen = load(ROOT / 'FROZEN PICKS.json')
    combos = load(ROOT / 'COMBINATIONS.json')
    trials = load(ROOT / 'TRIAL ACCOUNTING.json')['passes']
    graphs(frozen, combos)
    rob = {}
    for label, c in combos.items():
        if 'trio' not in label:
            continue
        folder = f'combo-{label.split()[0].lower()}-{len(c["members"])}-{"".join(x[0] for x in c["members"])}-5y'
        rob[label] = robustness(label, folder, trials)
    json.dump(rob, open(ROOT / 'ROBUSTNESS.json', 'w'), indent=2, default=str)
    print(json.dumps({k: (v['verdict'], v['bootstrap']['return_p05_pct'], v['bootstrap']['profit_factor_p05'], v['metrics']['deflated_sharpe_pct']) for k, v in rob.items()}, indent=1))


if __name__ == '__main__':
    main()
