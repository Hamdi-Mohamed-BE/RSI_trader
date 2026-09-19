import csv,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LABELS=['Current RR settings','All seven at 0.5R','All seven at 0.75R']

def load(folder):
    p=ROOT/folder
    rows=json.loads((p/'results.json').read_text())
    trades=list(csv.DictReader((p/'orb-combined-trades.csv').open(),delimiter=';'))
    days=list(csv.DictReader((p/'orb-combined-days.csv').open(),delimiter=';'))
    for r in rows:
        g=r['group'];t=[x for x in trades if x['group']==g];d=[x for x in days if x['group']==g]
        assert len(t)==int(r['trades'])
        assert abs(10000+sum(float(x['net']) for x in t)-float(r['balance']))<.02
        assert abs(min(float(x['minimum_equity']) for x in d)-float(r['min']))<.02
        assert abs(max(float(x['daily_loss']) for x in d)-float(r['worst_day']))<.02
        positive=sum(max(0,float(x['net'])) for x in t);negative=sum(max(0,-float(x['net'])) for x in t)
        r['win_rate']=100*sum(float(x['net'])>0 for x in t)/len(t) if t else 0
        r['pf']=positive/negative if negative else None
        r['monthly']={m:round(sum(float(x['net']) for x in t if x['exit'].startswith(m)),2) for m in ['2026.07','2026.08','2026.09']}
        r['target_date']=datetime.fromtimestamp(int(r['target']),timezone.utc).isoformat() if int(r['target']) else None
        if int(r['target']):
            stamp=datetime.fromtimestamp(int(r['target']),timezone.utc).strftime('%Y.%m.%d %H:%M:%S')
            assert not any(x['entry']<=stamp<x['exit'] for x in t), 'Target must be flat'
            closed=[x for x in t if x['exit']<=stamp]
            threshold=10500 if folder=='combined-verification' else 11000
            assert 10000+sum(float(x['net']) for x in closed)>=threshold-.001
            assert len({x['entry'][:10] for x in closed})>=4
            r['target_balance']=round(10000+sum(float(x['net']) for x in closed),2)
    log=(p/'journal.txt').read_text()
    assert 'future_quotes=0' in log and 'margin_errors=0' in log and 'COMBINED_QA|active=0|' in log
    return rows

main=load('combined');verification=load('combined-verification')
result={'full_window':main,'verification':verification}
(ROOT/'combined'/'analysis.json').write_text(json.dumps(result,indent=2))
lines=['# Combined seven-ORB reconstruction','',
       '19 July–18 September 2026. Three separate shared $10,000 portfolios; 1% equity risk per entry, broker lot rounding up, adaptive off. Native MT5 historical quotes mark the saved fills to market; this is NOT a fresh multi-EA strategy backtest or verified FTMO execution.', '',
       '| Portfolio | Final balance | Net return | Trades | Net win rate | PF | Sampled equity DD | Worst daily equity loss | Max concurrent trades | Maximum initial-stop exposure |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in main:
    lines.append(f'| {LABELS[int(r["group"])]} | ${float(r["balance"]):,.2f} | {(float(r["balance"])-10000)/100:+.2f}% | {r["trades"]} | {r["win_rate"]:.2f}% | {r["pf"]:.2f} | {float(r["dd"]):.2f}% | ${float(r["worst_day"]):.2f} | {r["max_open"]} | ${float(r["max_risk"]):.2f} |')
lines+=['','These balances assume uninterrupted trading. Challenge phases are instead evaluated below with a fresh $10K Verification balance from the next business day after passing Phase 1. No administrative delay is modeled.', '',
        '| Portfolio | Phase 1 reached +10%, flat and four entry days | Verification final balance | Verification closed trades | Verification reached +5% | Loss breach in either phase replay |',
        '|---|---|---:|---:|---|---|']
for r,v in zip(main,verification):
    reached=bool(int(r['target']));vbal=f'${float(v["balance"]):,.2f}' if reached else 'Not started'
    lines.append(f'| {LABELS[int(r["group"])]} | {r["target_date"] or "Not reached"} | {vbal} | {v["trades"] if reached else "—"} | {v["target_date"] if reached and int(v["target"]) else "No"} | {"Yes" if int(r["breach"]) or (reached and int(v["breach"])) else "None observed"} |')
lines+=['','## Uninterrupted monthly net USD','', '| Portfolio | July 19–31 | August | September 1–18 |','|---|---:|---:|---:|']
for r in main:lines.append('| '+LABELS[int(r['group'])]+' | '+' | '.join(f'${v:+,.2f}' for v in r['monthly'].values())+' |')
lines+=['','## Limitations and evidence','',
        '- All 39 signals per portfolio come from the seven standalone native tests. Fills, entry timing and exit timing are held constant; new lot sizes use shared marked-to-market equity. Broker-valid lots round up. Historical commissions are scaled by volume, swaps are zero in the source ledgers.',
        '- Simultaneous timestamps process existing closes first, then new entries by EA identifier. Saved timestamps have second precision. This ordering and reuse of fills introduce reconstruction uncertainty.',
        '- Equity is sampled on USTEC ticks and timer callbacks using historical XAUUSD/USTEC bid/ask quotes. No future quotes or margin-calculation errors were observed. Secondary quotes were up to six seconds old in the full-window replay; this is not a merged, every-symbol-tick equity path.',
        '- Original Exness history used generated ticks on September 14–15. Spread is reflected in fills and bid/ask marking; no additional latency/slippage stress was added.',
        '- Exness symbol specifications and tester 1:30 leverage were used for available-margin checks, not validated FTMO symbol margins. No entry was skipped for margin in the full-window replay.',
        '- Maximum initial-stop exposure sums original stop risks of concurrently open trades; it does not assume later trailing stops remain at their original levels.',
        '- FTMO 2-Step loss checks use $500 daily equity loss from Prague-midnight balance and $9,000 static equity floor. Phase targets require flat positions and four entry days. Phase transition assumes the next business day with no administrative wait. This is historical evidence, not a passing probability or payout guarantee. [Official objectives](https://ftmo.com/en/trading-objectives/)',
        '- Research files only. No live trade, active EA, installer/BAT, or website setting changed.',
        '', 'Inputs, per-trade cash flows, daily equity minima and native journals are saved under `combined/` and `combined-verification/`.']
(ROOT/'combined'/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[:31]))
