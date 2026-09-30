"""Descriptive native results and predeclared gates. No optimized forecasts."""
from collections import Counter
from datetime import datetime, timedelta
import gzip, json, math, statistics
import numpy as np
import run
from verify import DTYPE

ROOT, CFG = run.ROOT, run.CFG


def streaks(values, positive):
    lengths=[]; n=0
    for x in values:
        if (x>0 if positive else x<0): n+=1
        elif n: lengths.append(n); n=0
    if n: lengths.append(n)
    return max(lengths, default=0), statistics.mean(lengths) if lengths else 0


def describe(trades, start, end, asset, observed_days):
    p=[t['net_profit'] for t in trades]; n=len(p)
    gross=sum(max(x,0) for x in p); loss=-sum(min(x,0) for x in p)
    a=datetime.strptime(start,'%Y.%m.%d'); b=datetime.strptime(end,'%Y.%m.%d'); days=(b-a).days
    weekdays=sum((a+timedelta(days=i)).weekday()<5 for i in range(days))
    win=sum(x>0 for x in p); frac=win/n if n else 0
    ci=None
    if n:
        z=1.959963984540054; center=(frac+z*z/(2*n))/(1+z*z/n)
        half=z*math.sqrt(frac*(1-frac)/n+z*z/(4*n*n))/(1+z*z/n)
        ci=[100*(center-half),100*(center+half)]
    mw,aw=streaks(p,True);ml,al=streaks(p,False)
    return dict(trades=n,net_profit=sum(p),return_pct=sum(p)/CFG['deposit']*100,pf=gross/loss if loss else None,
                win_rate=frac*100,win_ci95=ci,per_day=n/observed_days if observed_days else 0,
                available_broker_days=observed_days,per_weekday_approx=n/(days if asset=='BTC' else weekdays),per_week=n/(days/7),
                per_month=n/(days/365.2425*12),max_win_streak=mw,max_loss_streak=ml,
                avg_win_streak=aw,avg_loss_streak=al,avg_win=gross/win if win else 0,
                avg_loss=-loss/sum(x<0 for x in p) if loss else 0,expectancy=sum(p)/n if n else 0,
                commission=sum(t['commission'] for t in trades),swap=sum(t['swap'] for t in trades),fee=sum(t['fee'] for t in trades))


def load():
    rows=[]
    for p in sorted((ROOT/'native').glob('*/run.json')):
        r=json.loads(p.read_text())
        if r['smoke']:continue
        trades=json.loads((p.parent/'trades.json').read_text());orders=json.loads((p.parent/'orders.json').read_text())
        audit=np.frombuffer(gzip.decompress((p.parent/'audit.bin.gz').read_bytes()),dtype=DTYPE)
        observed_days=len(np.unique(audit['now']//86400))
        r['net']=describe(trades,r['start'],r['end'],r['asset'],observed_days);r['path']=p.parent.name
        ratios=[float(o['risk'])/float(o['planned']) for o in orders if float(o['planned'])>0]
        slippage=[int(o['side'])*(float(o['fill'])-float(o['entry']))*float(o['risk'])/abs(float(o['entry'])-float(o['sl'])) for o in orders]
        r['sizing']=dict(median_risk_ratio=statistics.median(ratios) if ratios else None,max_risk_ratio=max(ratios,default=None),above_110pct=sum(x>1.1 for x in ratios))
        r['entry_slippage']=dict(mean_adverse_usd=statistics.mean(slippage) if slippage else None,max_adverse_usd=max(slippage,default=None))
        rows.append(r)
    return rows


def f(x,dec=2):return 'n/a' if x is None else f'{x:.{dec}f}'


def gates(index):
    result={}
    for asset in CFG['symbols']:
        for variant in ('A_pullback','B_extreme'):
            checks={}
            for w in ('3y','5y'):
                r=index.get((asset,variant,w));c=index.get((asset,'C_MACD_only',w));d=index.get((asset,'D_A_without_RSI',w))
                if not r or not c or not d:checks[w]=None;continue
                n=r['net'];nc=c['net'];nd=d['net']
                checks[w]=dict(positive=n['return_pct']>0,pf_at_least_115=(n['pf'] or 0)>=1.15,
                               sample=n['trades']>=30,beats_macd=n['return_pct']>nc['return_pct'] and (n['pf'] or 0)>(nc['pf'] or 0))
                if variant=='A_pullback':checks[w]['rsi_incremental']=n['return_pct']>nd['return_pct'] and (n['pf'] or 0)>(nd['pf'] or 0)
            verdict='INCOMPLETE' if any(x is None for x in checks.values()) else 'PASS_RAW_REVIEW' if all(all(x.values()) for x in checks.values()) else 'FAIL'
            result[f'{asset}/{variant}']=dict(verdict=verdict,checks=checks)
    return result


def table(rows):
    lines=['| Asset | Variant | Return | Trades | /month | /day | Win % | Net PF | Equity DD | Max W/L | Avg W/L |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        n=r['net'];m=r['metrics']
        lines.append(f'| {r["asset"]} | {r["variant"]} | {n["return_pct"]:+.2f}% | {n["trades"]} | {n["per_month"]:.1f} | {n["per_day"]:.2f} | {n["win_rate"]:.2f}% | {f(n["pf"])} | {m["max_equity_dd_pct"]:.2f}% | {n["max_win_streak"]}/{n["max_loss_streak"]} | {n["avg_win_streak"]:.2f}/{n["avg_loss_streak"]:.2f} |')
    return lines


def main():
    rows=load();index={(r['asset'],r['variant'],r['window']):r for r in rows};gate=gates(index)
    audit=json.loads((ROOT/'VERIFICATION.json').read_text()) if (ROOT/'VERIFICATION.json').exists() else None
    result=dict(completed=len(rows),expected=176,gates=gate,verification=audit,runs=rows)
    run.save(ROOT/'RESULTS.json',result)
    passed=[k for k,v in gate.items() if v['verdict']=='PASS_RAW_REVIEW']
    lines=['# RSI + MACD — native raw comparison','',f'Main cases complete: **{len(rows)}/176**. Four additional engineering smoke runs. No optimization or live deployment.','',
           '## Decision','']
    if (ROOT/'INTERRUPTIONS.md').exists():
        lines += ['One additional XAU six-month attempt was interrupted by battery-related sleep and rejected for an incomplete report. Its identical retry succeeded; only complete verified runs are counted. See `INTERRUPTIONS.md`.','']
    if len(rows)!=176:lines.append('**IN PROGRESS.** Do not choose a winner from partially completed assets/windows.')
    elif not passed:lines.append('**No A/B combination passes the frozen long-window/control gate. No candidate is approved for optimization or FTMO use.**')
    else:lines.append('**Qualifies for raw-stage review only:** '+', '.join(passed)+'. Not validated for deployment or FTMO.')
    lines += ['', 'All runs start independently at $10,000, with 1% requested current-equity risk, 2 ATR initial stop and 1R target. This is not a portfolio simulation. Native Exness CFD history and contract rules are used, not FTMO-specific execution.', '',
              'A = H1 trend-side RSI40/60 pullback plus MACD recovery. B = RSI30/70 extreme recovery plus fresh MACD crossover. C = MACD-only crossover control. D = A with the RSI requirement removed. Full clock/arm/execution rules are in `RULES.md`. None of these settings is claimed to be an exact paper replication.', '',
              '## Latest year — both RSI candidates','']
    one=[index[(a,v,'1y')] for a in CFG['symbols'] for v in ('A_pullback','B_extreme') if (a,v,'1y') in index]
    lines += table(one)
    lines += ['', '## Frozen gate — both 3y and 5y required','', '| Asset / candidate | Verdict | 3y conditions | 5y conditions |', '|---|---|---|---|']
    for k,v in gate.items():
        desc=lambda x:'pending' if x is None else '; '.join(f'{n}: {"pass" if ok else "fail"}' for n,ok in x.items())
        lines.append(f'| {k} | {v["verdict"]} | {desc(v["checks"]["3y"])} | {desc(v["checks"]["5y"])} |')
    for w,start in CFG['windows'].items():
        lines += ['',f'## {w}: {start} to {CFG["end"]} (exclusive)','']
        lines += table([index[(a,v,w)] for a in CFG['symbols'] for v in CFG['variants'] if (a,v,w) in index])
    lines += ['', '## Latest-year candidate uncertainty and cost audit','',
              '| Asset / candidate | Win 95% interval | /week | Avg win / loss | Commission / swap / fees | Median / max stop-risk ratio | Above 1.1% risk | Mean adverse entry slip |',
              '|---|---|---:|---|---|---|---:|---:|']
    for r in one:
        n=r['net'];s=r['sizing'];ci=n['win_ci95'];cis='n/a' if ci is None else f'{ci[0]:.1f}–{ci[1]:.1f}%'
        lines.append(f'| {r["asset"]} / {r["variant"]} | {cis} | {n["per_week"]:.2f} | ${n["avg_win"]:.2f} / ${n["avg_loss"]:.2f} | ${n["commission"]:.2f} / ${n["swap"]:.2f} / ${n["fee"]:.2f} | {f(s["median_risk_ratio"])}x / {f(s["max_risk_ratio"])}x | {s["above_110pct"]} | ${f(r["entry_slippage"]["mean_adverse_usd"])} |')
    lines += ['', '## Limitations that matter','',
              '- High win rate is not a profit forecast. PF/returns are recomputed after per-position commission, swap and fee totals. Bid/ask spread and simulated delay are already reflected in fills; no double-counted spread subtraction.',
              '- Win rate and streaks classify net position P&L, so they can differ from native headline win counts when costs turn a gross win into a net loss. Controls and candidates use the same net definition.',
              '- Requested 1% risk is not a hard cap: the shared raw-test sizing rounds UP and uses broker minimum lots. Slippage, fees and gaps can increase loss further. The table discloses sizing overshoot rather than silently clipping it.',
              '- Broker real-tick coverage must be read from each retained journal. Native history-quality percentages include the 120-day no-trade warmup. A Model4 label alone does not imply every historical tick was real; older intervals can be generated from bars. Historic contract-cost settings and simulated 150ms delay are not a guarantee of achievable live fills. [MetaTrader tick-generation documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).',
              '- The implementation uses EMA12 minus EMA26 with an SMA9 signal, matching [native MT5 MACD](https://www.metatrader5.com/en/terminal/help/indicators/oscillators/macd); a charting platform using an EMA signal is a different specification.',
              '- Win-rate intervals are descriptive Wilson intervals assuming independent trials; clustered market conditions and selection across 176 tests mean these are not reliable forward-probability bands.',
              '- All windows overlap and are now examined. None may later be advertised as untouched out-of-sample evidence. Controls are unoptimized rules with potentially different entry frequency/occupancy; they are not matched random-entry experiments.',
              '- /day uses broker calendar days with available decision quotes, including days without entries and partial Sunday sessions; it is not restricted to days with trades. /week and /month use elapsed calendar time. A weekday-only approximation is retained separately in JSON. Zero-profit positions break both streaks.',
              '- Candidate B starts each independent window with no armed setup; at most its first eight M15 decisions can depend on that initialization. Indicators themselves receive 120 warmup days. All variants start flat.',
              '- This is raw research, not a passed FTMO simulation, full parameter optimization, Monte Carlo proof or live deployment. Failing candidates are not promoted. A 60% win objective is separate from the profitability gate.', '',
              '## Verification','']
    if audit:
        lines += [f'{audit["helper_tests"]} boundary checks; {audit["completed_cases"]} native cases; {audit["decision_bars"]:,} decision bars; {audit["closed_positions"]:,} closed positions audited.',audit['limitation']]
    else:lines.append('Pending.')
    lines += ['', '## Native data / operational audit','']
    for r in rows:
        lines.append(f'- {r["path"]}: reported quality `{r["metrics"]["history_quality"]}`; flags `{json.dumps(r["flags"])}`; {"; ".join(r["summary"])}. Tick-coverage messages: {"; ".join(r["tick_coverage"])}')
    lines += ['', '## Files','', '`BUILD.json` contains frozen source/dependency/binary/config hashes. `native/<case>/` holds private tester configuration, exact SET, compressed reports/journals, complete deals, position ledgers and the decision audit. `RESULTS.json` keeps every case and gate. `VERIFICATION.json` records the independent rule/ledger checks. Research stays local; the earlier DI-launcher change was pushed separately.']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=len(rows),expected=176,review_survivors=passed)),flush=True)


if __name__=='__main__':main()
