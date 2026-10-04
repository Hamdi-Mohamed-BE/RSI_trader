"""Readable before/after evidence, including independent EA closing-ledger curves."""
from pathlib import Path
from datetime import datetime
import gzip, html, json

R = Path(__file__).resolve().parent
S = R.parent.parent / 'ADX DI Five Bot Review 2026-10-03'
LABELS = {'ema3': 'EMA3 Gold', 'london': 'USDJPY London', 'asia': 'Asia Breakout Gold',
          'trend': 'Trend Progression (0.6R)', 'rsi': 'RSI VWAP Gold — unchanged'}
FILTERS = {'ema3': 'ADX ≥25 H4', 'london': 'ADX ≥20 + DI M15', 'asia': 'DI only H1',
           'trend': 'DI only H4', 'rsi': 'No new filter'}
ONE = {'ema3': 'ADX25', 'london': 'ADX20_DI', 'asia': 'DI_ONLY', 'trend': 'DI_ONLY', 'rsi': 'BASE'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def records():
    result = load(R / 'SUMMARY.json')
    assert len(result) == 18
    for key, variant in ONE.items():
        for arm in (('unchanged',) if key == 'rsi' else ('baseline', 'filtered')):
            folder = S / 'native' / (key + '-' + ('ORIGINAL' if arm != 'filtered' else variant))
            row = load(folder / 'result.json')
            result.append(dict(row, key=key, arm=arm, period='1y', folder=str(folder),
                               start='2025.10.02', end_exclusive='2026.10.02'))
    for row in result:
        row.setdefault('folder', str(R / 'native' / row['tag']))
    return result


def fmt(v, suffix='', signed=False):
    return '—' if v is None else f'{v:+.2f}{suffix}' if signed else f'{v:.2f}{suffix}'


def chart(rows):
    curves = []
    for row in rows:
        ledger = json.loads(gzip.decompress((Path(row['folder']) / 'trades.json.gz').read_bytes()))
        start = datetime.strptime(row['start'], '%Y.%m.%d').timestamp()
        end = datetime.strptime(row['end_exclusive'], '%Y.%m.%d').timestamp()
        balance = 10000
        points = [(start, balance)]
        for t in ledger:
            balance += t['net_profit']
            points.append((datetime.fromisoformat(t['close_time']).timestamp(), balance))
        points.append((end, balance))
        curves.append((row['arm'], points))
    low = min(y for _, p in curves for _, y in p)
    high = max(y for _, p in curves for _, y in p)
    pad = max(100, (high-low)*.08)
    low -= pad
    high += pad
    out = ['<svg viewBox="0 0 780 255" role="img" aria-label="Before versus filtered closed-balance curve">']
    for i in range(5):
        y = 18 + i*48
        val = high - (high-low)*i/4
        out.append(f'<line x1="62" x2="758" y1="{y}" y2="{y}" stroke="#23443b"/><text x="3" y="{y+4}">${val:,.0f}</text>')
    for arm, points in curves:
        color = '#69aaf5' if arm == 'baseline' else '#77efd0'
        coords = ' '.join(f'{62+(x-start)/(end-start)*696:.2f},{18+(high-y)/(high-low)*192:.2f}' for x,y in points)
        out.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
    out.append(f'<text x="62" y="239">{datetime.fromtimestamp(start):%Y-%m-%d}</text><text x="665" y="239">{datetime.fromtimestamp(end):%Y-%m-%d}</text></svg>')
    return ''.join(out)


def table(rows):
    fields = [('return_pct', '%', True), ('pf', '', False), ('win_pct', '%', False),
              ('equity_dd_pct', '%', False), ('sharpe', '', False)]
    out = ['<div class="scroll"><table><thead><tr><th>EA / version</th><th>Return</th><th>PF</th><th>Win rate</th><th>Equity DD</th><th>Sharpe</th><th>Trades</th><th>Wins / losses streak</th><th>Trades / month</th></tr></thead><tbody>']
    for row in rows:
        s = row['stats']
        out.append(f'<tr class="{row["arm"]}"><th>{html.escape(LABELS[row["key"]])}<small>{row["arm"]}: {html.escape(FILTERS[row["key"]] if row["arm"] != "baseline" else "previous study preset")}</small></th>')
        out.extend(f'<td>{fmt(s[k],suffix,signed)}</td>' for k,suffix,signed in fields)
        out.append(f'<td>{s["trades"]}</td><td>{s["max_win_streak"]} / {s["max_loss_streak"]}</td><td>{s["trades_month"]:.2f}</td></tr>')
    return ''.join(out) + '</tbody></table></div>'


def main():
    rows = records()
    comparisons = []
    parts = ['''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Calyx · ADX / DI before and after</title>
<style>body{margin:0;background:#071511;color:#e6f4ef;font:15px system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:40px 24px}h1{font-size:42px;letter-spacing:-1px}h2{margin-top:50px}p{line-height:1.7;color:#a3c3b9}.note{border:1px solid #846d2d;padding:18px;border-radius:15px;color:#f4db9a}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{padding:15px 12px;border-bottom:1px solid #254139;text-align:right}th:first-child{text-align:left}small{display:block;font-weight:400;color:#91b7aa;margin-top:5px}.filtered td,.unchanged td{color:#77efd0}.baseline td{color:#69aaf5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(450px,1fr));gap:18px}.card{background:#0c211a;border:1px solid #29483c;border-radius:18px;padding:20px;min-width:0}svg{width:100%;height:auto}svg text{fill:#9cbcb0;font:11px monospace}a{color:#77efd0}.legend{font-size:13px}.legend span{margin-right:18px}@media(max-width:600px){.grid{grid-template-columns:1fr}h1{font-size:30px}}</style>
<main><p>CALYX · FROZEN NATIVE MT5 COMPARISON · 3 OCTOBER 2026</p><h1>Before vs. ADX / DI.<br>One, three and five years.</h1>
<p>Each EA independently starts at $10,000. Planned risk is 1% of equity per trade, rounded up to broker-valid lots. Same exits, broker, recorded commission / swap, Model 4 and 150ms execution delay. This is not a shared portfolio or an FTMO pass / payout simulation.</p>
<p class="note">Retrospective evidence, not a forecast. The recent year was used to select these filters, so longer overlapping windows are not independent forward validation. Generated ticks fill missing broker history. Trend DI remains a provisional selection based on only 29 recent-year trades.</p>
<p>Baseline means the exact unfiltered preset from the earlier one-year table, not every historical BAT mode. Asia already has its existing Markov filter enabled. EMA3 baseline has Markov off. No new optimization was performed.</p>
<nav><a href="#1y">1 year</a> · <a href="#3y">3 years</a> · <a href="#5y">5 years</a></nav>''']
    for period in ('1y','3y','5y'):
        selected = [r for r in rows if r['period'] == period]
        selected.sort(key=lambda r: (list(LABELS).index(r['key']), r['arm']))
        parts.append(f'<section id="{period}"><h2>{period} · {selected[0]["start"]} → 2026.10.02 exclusive</h2>')
        qualities = sorted(set(r['stats']['history_quality'] for r in selected))
        parts.append('<p>Broker history: '+html.escape('; '.join(qualities))+'. Equity DD includes floating P/L; plotted balances below do not. Sharpe uses calendar-daily closing returns including inactive days, annualized √365.2425.</p>')
        parts.append(table(selected))
        parts.append('<p class="legend"><span style="color:#69aaf5">━ Previous study preset</span><span style="color:#77efd0">━ Selected filter / unchanged reference</span></p><div class="grid">')
        for key in LABELS:
            pair = [r for r in selected if r['key'] == key]
            parts.append(f'<article class="card"><h3>{html.escape(LABELS[key])}</h3>{chart(pair)}<small>Net closed balance after costs, not floating equity.</small></article>')
            old = next((r for r in pair if r['arm']=='baseline'), None)
            new = next(r for r in pair if r['arm']!='baseline')
            comparisons.append(dict(key=key,label=LABELS[key],period=period,baseline=old['stats'] if old else None,
                                    filtered=new['stats'],unchanged=key=='rsi'))
        parts.append('</div></section>')
    parts.append('<p>Native reports, frozen inputs and position ledgers are saved beside this report. Filters only admit new entries; protective exits remain unchanged. No active terminal was changed.</p></main></html>')
    (R / 'Comparison.html').write_text(''.join(parts),encoding='utf-8')
    (R / 'COMPARISON.json').write_text(json.dumps(comparisons,indent=2,allow_nan=False),encoding='utf-8')
    print('REPORT COMPLETE',len(rows),'native records, 15 chart panels',flush=True)


if __name__=='__main__':main()
