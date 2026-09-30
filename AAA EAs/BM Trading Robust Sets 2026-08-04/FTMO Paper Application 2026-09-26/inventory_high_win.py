"""Offline inventory and high-win shortlist, 27 September 2026. No terminal import."""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
import additions as a
import compare as c

P = c.ROOT.parent
CACHE = P.parent/'EA store/data/evidence-cache/v1/products'
INSTALLER = P/'_Auto Deploy/Install-BMTradingPortfolio.ps1'
V9 = P.parent.parent/'AI news/usless/archive-20260910-172145/research/news_v9_execution_v2_1y_results.json'
LABELS = {
 c.RAW:'Gold Overnight Value Area — raw',
 'ema3/safe':'EMA3 — Full Safe', 'ema3/standard':'EMA3 — Standard',
 'orb-volume-profile-high-win-0-75r/standard':'ORB Volume Profile — 0.75R (saved; not current launcher)',
 'nasdaq-overnight/standard':'Nasdaq Overnight', a.RSI:'Gold RSI VWAP',
 'xau-squeeze-momentum-standard/safe':'XAU Squeeze Momentum — Safe',
 'dmc-fresh-reaction-us100/standard':'DMC Fresh Reaction US100',
 a.DI:'Nasdaq 5M — Claude DI',
 'us100-selective-orb-v3/standard':'US100 Selective ORB V3',
}

def streaks(values):
    w=l=mw=ml=0
    for v in values:
        w=w+1 if v>0 else 0
        l=l+1 if v<0 else 0
        mw=max(mw,w);ml=max(ml,l)
    return mw,ml

def main():
    text=INSTALLER.read_text(encoding='utf-8-sig')
    section=text[text.index('$items = @('):text.index('\n    foreach ($item in $items)')]
    inventory=[dict(name=n,symbol=s) for n,s in re.findall(r"Label\s*=\s*'([^']+)'; Canonical\s*=\s*'([^']+)'",section)]
    assert len(inventory)==34
    data=c.read(c.SOURCE/'prepared.json');ns=c.engine()
    data['rows'][a.DI],di_evidence=a.load_di()
    source_hashes={str(INSTALLER):hashlib.sha256(INSTALLER.read_bytes()).hexdigest()}
    rows=[]
    for key,label in LABELS.items():
        periods={}
        for period in ('1y','5y'):
            path=CACHE/key/(period+'.json');tp=CACHE/key/(period+'.trades.json')
            payload=c.read(path);trades=c.read(tp);s=payload['stats']
            vals=[t['net_profit'] for t in sorted(trades,key=lambda r:r['close_time'])]
            w,l=streaks(vals)
            assert len(trades)==s['trades'],key
            net_win_rate=100*sum(v>0 for v in vals)/len(vals)
            assert w==s['max_win_streak'] and l==s['max_loss_streak'],(key,w,l,s)
            periods[period]=dict(s,net_ledger_win_rate=net_win_rate,
                reported_win_rate_matches_net=abs(net_win_rate-s['win_rate_pct'])<.011,
                trades_per_week=s['trades']/52.1775 if period=='1y' else s['trades']/(5*52.1775))
            source_hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            source_hashes[str(tp)]=hashlib.sha256(tp.read_bytes()).hexdigest()
        six=None
        if key in data['rows']:
            tr=sorted([r for r in data['rows'][key] if c.END-182*c.DAY<=r['op']<c.END and r['cl']<c.END],key=lambda r:r['cl'])
            vals=[(sum(ns['costs'](r,True)[:3])-ns['costs'](r,True)[3])/r['unit_risk'] for r in tr]
            pos=sum(max(0,v) for v in vals);neg=-sum(min(0,v) for v in vals);w,l=streaks(vals)
            six=dict(trades=len(tr),win_rate=100*sum(v>0 for v in vals)/len(vals) if vals else None,
                     pf=pos/neg if neg else None,sum_r=sum(vals),longest_win=w,longest_loss=l)
        rows.append(dict(key=key,label=label,periods=periods,stress6m=six))
    v9=c.read(V9);vtr=sorted(v9['trades'],key=lambda r:r['exit_time_utc'])
    assert len(vtr)==29 and sum(t['pnl_usd']>0 for t in vtr)==27
    w,l=streaks([t['pnl_usd'] for t in vtr]);v9summary=dict(trades=29,wins=27,win_rate=100*27/29,longest_win=w,longest_loss=l,configuration=v9['selected_configuration'],results=v9['results'],data_sources=v9['data_source_counts'])
    source_hashes[str(V9)]=hashlib.sha256(V9.read_bytes()).hexdigest()
    out=dict(as_of='2026-09-27',inventory=inventory,candidates=rows,v9=v9summary,source_hashes=source_hashes,prior_source_hashes=c.verify_sources())
    c.save(c.ROOT/'EA_INVENTORY_HIGH_WIN.json',out)
    lines=['# EA inventory and high-win / win-streak shortlist', '',
        'Read-only-source review, 27 September 2026. No MT5 connection, optimization, fresh native tests, trades or launcher changes.', '',
        '## What is available', '',
        'The current installer contains 34 entries. This means configured for installation, NOT confirmed attached or running on the connected account. Standard/Safe/DI variants are not necessarily distinct entry strategies.', '']
    groups=defaultdict(list)
    for item in inventory:groups[item['symbol']].append(item['name'])
    for symbol,items in groups.items():
        lines += ['### '+symbol+' ('+str(len(items))+')', '']+['- '+n for n in items]+['']
    lines += ['### Saved outside the current launcher', '',
        '- ORB Volume Profile High Win 0.75R',
        '- XAU Squeeze Momentum High Win 0.75R',
        '- Engineered Liquidity XAU',
        '- XAG Session VWAP Snapback',
        '- 3 Way Gold and 3 Way Volume Profile research families; research presence is not deployment approval.', '',
        'The website still has cached evidence for the first four. Their removal is not reversed by this review.', '',
        '## Native saved one-year evidence', '',
        'Standalone broker tests, NOT FTMO portfolio outcomes. Each row uses its saved settings/sizing; most are nominal 1% equity risk. Different window endpoints (1–18 September 2026) and initialization prevent treating this as a perfectly matched leaderboard. DD is the saved native-reported equity drawdown metric, not newly replayed FTMO equity. Winning streaks are historical maxima, not expected future runs.', '',
        '| EA | Window | Trades | Trades/week | Win rate | PF | Reported DD | Longest wins/losses | Return |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        s=r['periods']['1y'];lines.append(f"| {r['label']} | {s['from']}–{s['to']} | {s['trades']} | {s['trades_per_week']:.2f} | {s['win_rate_pct']:.2f}% | {s['profit_factor']:.2f} | {s['max_drawdown_pct']:.2f}% | {s['max_win_streak']}/{s['max_loss_streak']} | {s['return_pct']:+.2f}% |")
    lines += ['', '## Recent equal-risk stress check', '',
        '2 March–30 August 2026, standalone saved trades before portfolio admissions. Each trade is normalized by its reconstructed initial stop risk. PF is calculated from net R, not unequal dollar positions. Same adverse execution assumptions as the FTMO study: gross wins -10%, losses +10%, extra slippage, commission floors and conservative carry. No lot rounding, combined exposure gates or probability simulation in this table.', '',
        '| EA | Trades | Win rate | Stressed PF (net R) | Sum R | Longest wins/losses |',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        s=r['stress6m']
        if not s:lines.append(f"| {r['label']} | Unavailable: incomplete audited stop/cost ledger | — | — | — | — |");continue
        if not s['trades']:lines.append(f"| {r['label']} | 0 | — | — | 0 | — |");continue
        pf='—' if s['pf'] is None else f"{s['pf']:.2f}"
        lines.append(f"| {r['label']} | {s['trades']} | {s['win_rate']:.2f}% | {pf} | {s['sum_r']:+.2f} | {s['longest_win']}/{s['longest_loss']} |")
    lines += ['', 'The saved 0.75R ORB ledger was excluded from the prior portfolio preparation because it lacks complete native cost/volume/price fields. Its headline win rate is evidence to investigate, not proof it improves a jointly traded FTMO portfolio.', '',
        '## Gold News V9: highest reported win rate, different evidence quality', '',
        f"The archived Execution V2 replay reports 27 wins/29 releases (93.10%), PF 3.17, +4.69% at nominal 1% risk, and 1.17% tick-equity DD. Recomputed longest streaks: {w} wins and {l} loss. Execution settings were selected on 20 releases; nine later releases produced 8 wins (88.89%), PF 1.883 and +0.89%. This is an execution holdout, not an independent audit of every model-training input.", '',
        'Configuration: prediction T-15 minutes, entry T-10 seconds, $20 gold-price stop, $4 target, time exit T+15 minutes. Runtime currently defaults to 0.75% risk; the cited replay is 1%. Full-year data ends with the 4 September 2026 NFP; only 29 events, roughly 0.56/week.', '',
        'The replay uses archived ticks plus M1 continuation where needed. Spread and tick gaps are included, but commission, network delay, rejection and market-depth impact are not. TP overshoot assumptions need checking. This is NOT a comparable fully costed native MT5 portfolio test. Do not advertise 93% as established live performance.', '',
        'The 0.2R target requires 83.33% wins just to break even before costs if every winner earns 0.2R and every loser loses 1R. Five nominal TP wins offset one nominal stop. It trades the same gold news events as News Pulse, so adding it does not provide independent event diversification.', '',
        '## Five-year context for the shortlist', '',
        '| EA | Trades | Win rate | PF | Reported DD | Longest wins/losses |',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        s=r['periods']['5y'];lines.append(f"| {r['label']} | {s['trades']} | {s['win_rate_pct']:.2f}% | {s['profit_factor']:.2f} | {s['max_drawdown_pct']:.2f}% | {s['max_win_streak']}/{s['max_loss_streak']} |")
    lines += ['', 'Different native start dates/warm-up and sizing can alter histories, so a five-year standalone run is not guaranteed to reproduce every trade in a separately initialized one-year run. Two five-year native headline win rates differ from net-ledger win rates: Nasdaq DI is 40.27% reported vs 40.16% net, and Selective ORB is 67.65% reported vs 64.71% net. All one-year shortlisted rates match the net ledger; streaks are net-outcome streaks.', '',
        '## Proposed research order, not deployment approval', '',
        '1. Core + Nasdaq Overnight alone. Different session and positive recent stressed net-R expectancy; longer two-year stress was approximately flat, so this is not an established edge. Do not confuse with Nasdaq 5M DI.',
        '2. Core + EMA3 Full Safe alone. Good one-year metrics and stronger five-year PF; recent stress is weak (17 trades, PF about 1.10). Shared gold exposure and carry require a cap.',
        '3. Reconstruct the saved 0.75R ORB native costs/stops, then consider it alone with the core. Shares signals with the original ORB; do not count them as independent diversification.',
        '4. Audit Gold News V9 execution and point-in-time model inputs before any FTMO probability claim. Same-event XAU risk must be pooled with Pulse.', '',
        'Do not add RSI VWAP or full-risk Nasdaq DI solely for headline wins/streaks: the prior matched portfolio simulation worsened six-month payout outcomes. US100 Selective ORB V3 has 80% wins on only five yearly trades, and Squeeze Safe had no trades in the last six-month audited pool; neither supplies reliable daily activity.', '',
        'The completed 3 Way Volume Profile research does not supply an obvious high-win replacement: most optimized variants failed older validation or the latest-year comparison. USDJPY VA reversal, for example, had 58.3% wins but lost 4.29% in the comparison year.', '',
        'Any next comparison should use a strict per-trade dollar ceiling with lot rounding DOWN (skip if minimum lot exceeds the cap), since the inherited $71.43 model rounded UP. Keep aggregate risk fixed when adding an EA and evaluate daily equity, margin, correlated losses, pass/payout and stalled-account rates—not win rate alone.', '',
        'FTMO permits EAs subject to legitimate execution and risk/practice rules; permission for a specific pre-news approach is not established merely by the general EA permission: [official rules](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/).', '',
        '## Checks', '',
        'Recomputed counts and W/L streaks match all 20 shortlisted cached windows; net win rates match 18/20, with the two five-year differences disclosed above. Verified Nasdaq DI build and SET hashes. Recomputed V9 wins/streaks from its 29-trade replay. Source hashes preserved in EA_INVENTORY_HIGH_WIN.json.', '']
    (c.ROOT/'EA_INVENTORY_HIGH_WIN.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(installer_entries=len(inventory),symbols={k:len(v) for k,v in groups.items()},cached_windows_verified=20,v9=v9summary),indent=2))

if __name__=='__main__':main()
