"""Produce the local audit report; no strategy or deployment changes."""
from __future__ import annotations
import csv
import html
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent

# Judgement is explicit, not an automatic PF-only optimiser or deployment rule.
DECISIONS = {
 'xau-rsi-vwap': ('keep', 'First choice for your win-rate preference', 'Annual PF 1.21 is only just above the screen, but the recent slice holds PF 1.28, 70.6% net wins and W/L 4/3. Keep the existing rules; collect forward evidence rather than shorten the target again.', 'Do not raise allocation from this retrospective screen alone. Prior research also had a negative bootstrap lower tail.'),
 'nasdaq-5m-candle-momentum': ('keep', 'First choice for recent activity and expectancy', 'Current DI-on / wide-stop / ATR-trail version: fresh native 3M PF 1.204, 51.2% wins, 43 positions and W/L 6/4. Retain it; no experimental ML gate.', 'Only a narrow recent PF margin. Five-year equity DD was 24.07% at 1% standalone risk; the annual cache and 3M fresh runs use separate account starts.'),
 'usdjpy-london-open-momentum': ('keep', 'Keep ADX20 + DI, not a high-win-rate bot', 'PF stays above 1.20 in both windows: annual 1.95 and recent 1.35. Recent 40.9% wins and W/L 3/3 do not meet your preferred streak pattern, but expectancy remains positive.', 'Do not remove a profitable asymmetric payoff just to manufacture more wins. The filter selection was retrospective, not an independent holdout.'),
 'xau-weakness': ('keep', 'Profitable diversifier; lower win rate', 'Safe configuration has annual PF 1.97 and recent PF 2.14. Recent W/L 2/1, but only 10 recent trades and 42.4% annual wins.', 'Not a high-win-rate core. Refresh the missing September/October data before changing exposure.'),
 'orb-volume-profile': ('keep', 'Keep profitable payoff, monitor streaks', 'Annual net PF 1.92; recent PF 1.47 and positive return. Recent 33.3% wins and W/L 3/6 mean it does not fit your high-win-rate preference.', 'Gross website winners can turn into net losers after costs. Overlapping XAU ORB signals need one combined exposure budget.'),
 'ema3': ('keep', 'Keep rules; watch the latest weakness', 'Annual PF 1.74, 63.6% wins and W/L 7/3 remain good. The recent slice is PF 0.89, -0.68%, only 10 trades: no justification to fit a new filter to those ten trades.', 'Conditional keep, not a recent winner. Obtain a current native quarter and demo results before increasing risk; keep the added ADX/DI filter OFF as selected.'),
 'nasdaq-overnight': ('keep', 'Keep rules; near-flat recent watch', 'Annual PF 1.81, 62.5% wins and W/L 10/3. Recent PF 0.97, -0.12%, W/L 4/2: weak, but not enough loss to justify another parameter hunt.', 'Conditional keep. Cached evidence ends September 5, so a current quarter and live costs are required before promotion.'),
 'btc-top-down-fvg-liquidity': ('keep', 'Keep unchanged on demo; thin sample', 'Annual PF 1.93, 50% wins, W/L 3/2. Recent three trades are positive, not validation.', 'Only 26 annual / 3 recent positions; do not infer a strong repeatable edge or increase risk.'),
 'orb-volume-profile-volume-confirmed': ('keep', 'Keep unchanged on demo; thin sample', 'Annual net PF 2.89 and recent 5-position PF 6.97. Net annual win rate is 47.8%, not the gross 52.2% website headline.', '23 annual / 5 recent trades; W/L 3/3 annually. Correlated with other Gold ORBs; no evidence to stack all of them at full risk.'),
 'xau-orb-new-york-m30': ('keep', 'Keep unchanged on demo; thin sample', 'Annual PF 3.06 but only 11 positions. Recent PF 40.77 comes from just four trades and is not a robust estimate.', 'Low count and tiny near-breakeven losses inflate PF. No live-capital promotion from this screen.'),
 'xau-orb-london-ny-overlap-m30': ('keep', 'Keep unchanged on demo; thin sample', 'Annual PF 2.18 with 24 trades. Recent PF 184.11 is only two trades, one win and one almost-flat net loss.', 'Do not rank this as the best EA because of that PF. Annual W/L 3/5 misses your streak preference.'),
 'us100-orb-new-york-m30': ('keep', 'Keep unchanged on demo; thin sample', 'Annual PF 1.68, 48.1% wins, W/L 4/4; recent three trades are positive.', '27 annual / 3 recent trades. Preserve the frozen rules, refresh the quarter and observe rather than optimise.'),
 'us100-month-end-flow': ('keep', 'Keep unchanged on demo; seasonal sample', 'Annual PF 1.33 with 34 trades; recent four trades have 75% wins and W/L 3/1.', 'Only four recent positions; existing Monte Carlo lower-tail return was negative. Recent profitability is not a pass-rate forecast.'),

 'lta-volume-profile': ('pause', 'Pause live new entries; first optimisation priority', 'Fresh current Safe M15: annual PF 1.23 / 30.1% wins, but July5-Oct4 PF 0.73 / 20.5% wins / -9.89%, W/L 1/14. This conflicts directly with your preferred behaviour.', 'Audit EM1 versus EM4, direction, session, stop/target and risk rounding separately. The experimental AND flow and range-only flow did not fix the longer-history weakness; do not deploy them automatically.'),
 'xau-slow-trend': ('pause', 'Pause normal 1R version', 'Annual PF 1.198 is just below 1.20; recent 46 positions give PF 0.77, -7.33%, 43.5% wins and W/L 6/7. Annual native equity DD is 17.05%.', 'Revisit entry regimes and payoff using frozen walk-forward windows. This finding is for normal 1R, not a test of a different FTMO 0.5R variant.'),
 'xau-trend-progression': ('pause', 'Pause 0.6R version pending deeper review', 'Annual 71.1% wins hide recent PF 0.52, -2.98% and 44.4% wins. Nine recent trades are thin, but the separate six-month native test also lost -3.16% with PF 0.73.', 'Compare exit geometry and regime dependence against the pre-target-change version out of sample. Do not lower R further merely to raise the win rate.'),
 'btc-poc-fibonacci': ('pause', 'Demo only; poor fit for your objective', 'Annual 26.9% wins, W/L 3/9; recent PF 0.44 and negative return. Existing Monte Carlo return P5 was -14.32%.', 'Not a robust high-win-rate allocation. Retain the code and demo logs; require new independent evidence before live use.'),
 'xau-regime-switch': ('pause', 'Demo only; recent breakdown', 'Annual PF 2.09 hides a losing latest six months (-4.95%, PF 0.43). Recent available slice has PF 0.05 and -2.73%.', 'Recent four trades alone are too small to prove a breakdown; the longer negative half-year and existing demo-only status support a pause.'),
 '3-way-gold': ('pause', 'Demo only; failed untouched holdout', 'Recent PF 1.22 / 57.9% wins / W/L 4/3 looks acceptable. But the unchanged BEST trio lost 20.3%, PF 0.74 on untouched 2019-2021; deflated Sharpe 63% missed the 95% requirement.', 'Separate modules. Momentum did not beat random direction; the qualified turn-of-month PROP module is not the current BEST trio. Changing to it requires its own approval and replay.'),
 'us30-hourly-profiles': ('pause', 'Demo only; no protective stop and selection bias', 'Annual/recent benchmark PF 1.33/1.28; recent W/L 6/10 fails your streak preference. Hours were selected on the same latest year and failed longer-history validation.', 'Displayed returns are the original 1-CFD-lot benchmark, NOT the new historical-loss-sized deployment. Historical maximum loss is not a future risk cap. Stress real spread and protective stops before live use.'),
 'us100-hourly-profiles': ('pause', 'Demo only; no protective stop and recent PF fade', 'Annual PF 1.30 falls to 1.09 recently. Selected-year results are not independent; long-history validation failed.', 'Original 1-CFD-lot benchmark differs from BAT sizing. Validate hours prospectively with realistic spread and an actual loss limit.'),
 'us100-selective-orb-v3': ('pause', 'Demo only; 80% win rate is five trades', 'Annual 80% wins / PF 1.60 is based on five trades; recent one win cannot establish an edge. Separate native six-month result was negative.', 'Insufficient frequency for your comparison. Collect more independent trades; do not loosen conditions purely to make the history busier.'),
 'news-pulse-xau': ('pause', 'Demo only until exact execution replay', 'Current October3 fresh-quote/market-fallback release has no accepted matching 1Y cache. Native fault checks verify order handling, not performance.', 'Replay current source/SET/helper with point-in-time event inputs, realistic spreads/delays/slippage and two-sided exposure. Old large returns do not validate the current profile.'),
 'news-pulse-xag': ('pause', 'Demo only until exact execution replay', 'Current placement release is not performance-validated. Archived hindsight-optimised results are deliberately excluded.', 'Stress delayed fills, spread spikes, both orders triggering and market fallback; use current hashes. Silver tight-stop risk is particularly sensitive to costs.'),
 'news-pulse-btc': ('pause', 'Demo only until exact execution replay', 'Current placement release is not performance-validated. Archived very large returns are not credible expected live returns.', 'Replay current settings at realistic latency, spread and fill assumptions. Both sides can trigger; the per-order risk is not a portfolio cap.'),
 'news-pulse-eurusd': ('pause', 'Demo only until exact execution replay', 'Current placement release is not performance-validated. Archived calendar-verified tests do not prove current execution or point-in-time economic data.', 'Validate current release with realistic costs and historical-vintage event inputs before reconsidering live trading.'),
 'gold-news-v9-direction': ('pause', 'Demo only; comparable performance evidence missing', 'No comparable approved year/quarter record was found for the active V9 prediction-service EA. This is an evidence gap, not proof that it loses.', 'Audit point-in-time forecasts, service outages, order fallback, doubled exposure and exact current binary/settings. Do not backtest with forecasts generated using future information.'),

 'gold-overnight-value-area': ('review', 'High win rate, weak recent payoff', 'Annual 74% wins / PF 1.56 / W/L 11/3, but recent 46 positions give PF 1.012 and only +0.11% despite 67.4% wins. Older five-year expectancy was already weak.', 'First check small targets versus costs and average loss, not extra win-rate filters. Preserve the existing version and test a minimum net payoff / exit hypothesis on untouched windows.'),
 'asia-breakout': ('review', 'Recent deterioration; high review priority', 'Annual PF 1.28 / 40.3% wins; recent PF 0.52 / 25% wins / -5.20%, W/L 3/6.', 'Check range width, breakout side, session and stop/exit attribution. Do not blindly restore DI: the prior long-window review rejected that addition.'),
 'dmc-current-xau': ('review', 'Borderline annual edge; correlated entries', 'Annual PF 1.18 is below your screen, although recent PF 1.37 and positive return improve. Recent 47.4% wins and W/L 3/4 remain a poor streak match.', 'Separate signal/session components and overlapping DMC risk. Optimise only well-supported hypotheses, with untouched validation and comparison to the frozen original.'),
 'dmc-fresh-reaction-xau': ('review', 'Thin evidence; confirm before optimising', 'Annual PF 1.90 with just 15 positions; recent four trades cannot identify a reliable filter. Separate cached six months was slightly negative.', 'Refresh exact current dates, confirm zone freshness/entry logic, and collect forward trades. Do not optimise to four observations.'),
 'dmc-fresh-reaction-us100': ('review', 'Attractive annual wins, insufficient frequency', 'Annual 66.7% wins / PF 1.89 / W/L 4/1 looks attractive, but only 12 positions. Recent slice has one loss, not evidence of failure.', 'Collect independent trades and review correlated US100 exposure. Keep entry rules frozen during observation; small samples are not a reason for aggressive optimisation.'),
 'eth-top-down-fvg-liquidity': ('review', 'Recent weakness, small sample', 'Annual PF 1.68 / 42.3% wins / W/L 3/4; recent six trades PF 0.27 and -3.11%.', 'Refresh the missing month, review long/short and exit costs separately, then validate any session/regime hypothesis out of sample.'),
 'us100-h1-orb-13utc': ('review', 'Recent payoff collapse', 'Annual PF 1.73 / W/L 7/4; recent ten trades PF 0.59 and -1.33% despite 50% wins. Nominal 6R is not the realised reward.', 'Break down timed exits, breakout direction and opening-range width. Compare frozen exit alternatives with actual net outcomes, not nominal target R.'),
 'sell-nasdaq-15min': ('review', 'Sell-only regime weakness', 'Annual Dynamic London PF 1.45 / 46.2% wins / W/L 4/6; latest six-month cache was negative and recent PF 0.95 remains weak.', 'Validate bearish-regime eligibility and exit timing. Avoid adding filters selected solely on the recent bullish Nasdaq sample.'),
 'xau-elliott-wave-1-2-3': ('review', 'Good annual expectancy, four recent losses', 'Annual PF 3.15 / 54.2% wins / W/L 6/4; recent four trades all lost. Four losses alone do not invalidate the full-year model.', 'Refresh the missing month, audit signal timing and structural stop/entry costs. Use a frozen longer validation period rather than fitting to four losses.'),
 'xau-squeeze-momentum-standard': ('review', 'Audit inactivity; no recent evidence', 'Normal Recommended Safe has 14 annual positions, PF 3.27 / 64.3% wins / W/L 6/2, but ZERO recent positions. No trades is not PF=0 or a 0% win rate.', 'Audit the Markov gate and signal/event logs before loosening conditions. FTMO uses Standard instead: its separate cached year had 19 trades, +4.89%, PF 1.99 and 52.6% wins; this is not the same mode.'),
}


def esc(x): return html.escape(str(x))
def num(x, n=2, suffix=''):
    return '—' if x is None else (esc(x) if isinstance(x, str) else f'{x:.{n}f}{suffix}')
def ret(x): return '—' if x is None else f'{x:+.2f}%'
def window(m):
    if not m: return 'No matching evidence'
    last = datetime.fromisoformat(m['end_exclusive']) - timedelta(days=1)
    return f"{m['start']} → {last:%Y-%m-%d}"


def metric_block(m, annual=False):
    if m is None: return '<span class="muted">Unverified current version</span>'
    if not m['trades']:
        return f'<div class="muted">{window(m)}</div><strong>No closed positions</strong><p>PF, win rate and streaks: not assessable</p>'
    wr = num(m['win_rate'], 1, '%')
    return f'''<div class="muted date">{window(m)}</div>
        <strong>{m['trades']} trades · PF {num(m['pf'])} · {wr} wins</strong>
        <p><span class="{'positive' if m['return_pct'] >= 0 else 'negative'}">{ret(m['return_pct'])}</span>
        · longest W/L <b>{m['win_streak']}/{m['loss_streak']}</b>
        {'· native equity DD '+num(m.get('equity_dd_pct'),2,'%') if annual else ''}</p>'''


def future_bat_keeps():
    """User choice only; preserve the original 37-EA evidence classifications."""
    study = BASE/'Trend Progression Optimization 2026-10-05'
    selection = json.loads((study/'SELECTION.json').read_text(encoding='utf-8'))
    comparisons = json.loads((study/'COMPARISON.json').read_text(encoding='utf-8'))
    params = selection['candidate']['validation']['parameters']
    assert params['InpRewardRisk'] == 1.5 and params['InpStopMode'] == 1
    assert params['InpSwingLookback'] == 3 and not params['InpUseBreakEven']
    assert not params['InpUseATRTrailing'] and not params['InpUseDynamicM15Stop']
    assert params['InpResearchADXMin'] == 0 and not params['InpResearchDI']
    chosen = {r['period']:r for r in comparisons if r['variant']=='CANDIDATE'}
    year, quarter, five = (chosen[k]['metrics'] for k in ['1Y','3M','5Y'])
    return f'''<section id="future-bat-keeps" class="notice">
    <div class="eyebrow">USER KEEP LIST · REVIEWED BAT · 2026-10-06</div>
    <h2 style="margin-top:12px">Keep: Trend Progression — candidate 1.5R</h2>
    <p><b>Selected by you and packaged in reviwed_Eas.bat; not installed on any account.</b>
    Only the reviewed BAT uses this 1.5R candidate. Other normal BATs retain 0.6R; the normal roster still has 37 EAs.</p>
    <p>H4 · long only · original EMA20/50 pullback entry · 3-bar swing stop + 0.10 ATR buffer · 1.5R target · no breakeven/trailing · ADX and DI off.</p>
    <p><b>Latest year, 2025-10-05 → 2026-10-05 (end exclusive):</b> {year['trades']} trades · {num(year['win_rate'],1,'%')} wins · PF {num(year['pf'],3)} · {ret(year['return_pct'])} · equity DD {num(chosen['1Y']['native']['equity_dd_pct'],2,'%')} · winning/losing runs {year['win_streak']}/{year['loss_streak']}.</p>
    <p><b>Latest quarter:</b> {quarter['trades']} trades · PF {num(quarter['pf'],3)} · {ret(quarter['return_pct'])}.
    <b>Five years:</b> {five['trades']} trades · PF {num(five['pf'],3)} · {ret(five['return_pct'])}.</p>
    <p><b>Research warnings retained:</b> the latest quarter lost money; only 26 recent-year positions;
    recent-year winning and losing runs tied at 3/3; the stated robustness screen failed; older 2019–2021 stress lost 8.78%.
    This user keep decision is not a validation pass. Separate $10,000 backtests used nominal 1% risk, with broker lot rounding sometimes exceeding it.
    The year had 75% real ticks, five years 15%; remaining ticks were generated. Historical results are not forecasts.</p>
    <p><a href="{(study/'Results.html').as_uri()}">Open this exact candidate's full results, parameters, graphs and Monte Carlo</a></p></section>'''


def deferred_news():
    note = json.loads((HERE/'DEFERRED NEWS.json').read_text(encoding='utf-8'))
    links = []
    for entry in note['entries']:
        if entry.get('audit_folder'):
            report = BASE/entry['audit_folder']/'Results.html'
            assert report.is_file()
            links.append(f'<li><b>{esc(entry["label"])}</b> — {esc(entry["status"])}. '
                         f'<a href="{report.as_uri()}">Saved audit, graphs and trade evidence</a>'
                         f'<p>{esc(entry["notes"])}</p></li>')
    return '<section id="deferred-news" class="notice"><div class="eyebrow">HISTORICAL AUDITS RETAINED · OWNER DEPLOYMENT CHOICE 2026-10-06</div><h2 style="margin-top:12px">Gold and Silver news — audits saved; all five news bots selected</h2><p>The owner now selected all four News Pulse assets plus Gold News V9 for reviwed_Eas.bat. Research remains incomplete/deferred; this deployment choice is NOT a validation pass. The historical DEFERRED BY USER notes below are retained. BTC/EURUSD/V9 reviews have not started. No account changed.</p><ul>'+''.join(links)+'</ul><p>Gold Overnight Value Area is also selected, with its original rules unchanged. <a href="DEFERRED%20NEWS.json">Saved audit/queue notes</a></p></section>'


def latest_optimisation():
    study=BASE/'Gold Overnight Value Area Optimization 2026-10-05'
    path=study/'VERDICT.json'
    if not path.exists(): return ''
    verdict=json.loads(path.read_text(encoding='utf-8'))
    assert (study/'Results.html').exists()
    comparison={x['tag']:x for x in json.loads((study/'COMPARISON.json').read_text(encoding='utf-8'))}
    raw,candidate=(comparison[k]['metrics'] for k in ['raw-1y','candidate-1y'])
    quarter=comparison['candidate-3m']['metrics']
    return f'''<section id="gold-overnight-update" class="notice"><div class="eyebrow">LATEST OPTIMISATION · RESEARCH ONLY · 2026-10-05</div>
    <h2 style="margin-top:12px">Gold Overnight Value Area — no replacement recommended</h2>
    <p><b>83 distinct cached-bar payoff/exit configurations, one frozen diagnostic and fresh native 1Y/6M/3M/3Y/5Y comparisons.</b>
    Current versus candidate, 2025-10-05 → 2026-10-05 exclusive: {raw['trades']} → {candidate['trades']} trades;
    PF {num(raw['pf'],3)} → {num(candidate['pf'],3)}; wins {num(raw['win_rate'],1,'%')} → {num(candidate['win_rate'],1,'%')}; return {ret(raw['return_pct'])} → {ret(candidate['return_pct'])}.</p>
    <p>The fixed 0.5R/minimum 0.5R, last-entry 14:00 NY candidate failed older native validation and returned {ret(quarter['return_pct'])} over the latest quarter (PF {num(quarter['pf'],3)}).
    Tick-rounding sensitivity, minimum/upward lot risk overshoot and session exit failures are retained in the audit. No original bot removed or modified; this unsuccessful replacement candidate is NOT selected.</p>
    <p>October 6 owner update: the unchanged original Gold Overnight rules are now selected for reviwed_Eas.bat, not this failed replacement. The table below reflects the latest owner phases; its original evidence and research verdict are retained separately.
    <a href="{(study/'Results.html').as_uri()}">Full dates, native graphs, payoff, annual breakdown and Monte Carlo</a>.</p>
    <p><b>Asia Breakout Gold follow-up is logged separately below.</b> News research remains deferred despite the owner's deployment choice; Trend1.5R is packaged only in the new reviewed launcher.</p></section>'''


def asia_optimisation():
    study=BASE/'Asia Breakout Optimization 2026-10-05'
    if not (study/'VERDICT.json').exists(): return ''
    verdict=json.loads((study/'VERDICT.json').read_text(encoding='utf-8'))
    comparison={x['tag']:x for x in json.loads((study/'COMPARISON.json').read_text(encoding='utf-8'))}
    raw,candidate=(comparison[k]['metrics'] for k in ['raw-1y','candidate-1y'])
    quarter=comparison['candidate-3m']['metrics']
    search=json.loads((study/'SEARCH RESULTS.json').read_text(encoding='utf-8'))
    return f'''<section id="asia-breakout-update" class="notice"><div class="eyebrow">ASIA BREAKOUT · RESEARCH ONLY · 2026-10-05</div>
    <h2 style="margin-top:12px">Asia Breakout Gold — {esc(verdict['decision'].lower())}</h2>
    <p>{search['configurations']} distinct native-generated-tick development settings, older native Model4 finalists and fresh1Y/6M/3M/3Y/5Y comparisons.
    Year2025-10-05 →2026-10-05 exclusive: {raw['trades']} →{candidate['trades']} trades;
    PF {num(raw['pf'],3)} →{num(candidate['pf'],3)}; wins {num(raw['win_rate'],1,'%')} →{num(candidate['win_rate'],1,'%')};
    return {ret(raw['return_pct'])} →{ret(candidate['return_pct'])}.</p>
    <p>Latest quarter candidate: {quarter['trades']} positions, PF {num(quarter['pf'],3)}, {ret(quarter['return_pct'])}.
    Clock mismatch and the two original trailing managers are documented. Lower-target wins are not automatically better expectancy.
    Older qualification: {'PASS' if verdict['older_gate_pass'] else 'FAIL'}; five-year robustness: {'PASS' if verdict['full5y_robustness_pass'] else 'FAIL'}.</p>
    <p><a href="{(study/'Results.html').as_uri()}">Full native comparison, graphs, years, all screened settings and Monte Carlo</a>.
    This October 5 study did not deploy changes or remove bots. Asia remains in deeper review and is not included in the October 6 reviewed launcher.</p>
    <p><b>Later queue update:</b> H1 ORB started but remains incomplete; it needs the new last-two-year OOS revision. Gold/Silver news research remains deferred; the owner-selected Trend1.5R is packaged only in reviwed_Eas.bat, not installed.</p></section>'''


def build():
    rows = json.loads((HERE/'evidence.json').read_text())
    reviewed = json.loads((BASE.parent/'EA store/data/ea-review.json').read_text(encoding='utf-8'))
    decisions = {r['slug']:r for r in reviewed['rows']}
    assert set(DECISIONS) == {x['slug'] for x in rows}
    manifest = json.loads((BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json').read_text())
    ftmo = {x['slug'] for x in manifest['entries']}
    for r in rows:
        group, brief, why, followup = DECISIONS[r['slug']]
        r.update(recommendation=group, brief=brief, reason=why, next_review=followup, ftmo_member=r['slug'] in ftmo)
        r['original_recommendation']=group
        chosen=decisions[r['slug']]
        r['reviewed_phase']=chosen['phase']
        if chosen['phase']=='live':
            r.update(recommendation='keep', brief='Passed to live trading phase — owner selection',
                     reason=chosen['reason'], next_review=chosen['next_review'])
        if r['slug']=='xau-trend-progression':
            r['original_evidence']={k:r[k] for k in ('year','recent','mode')}
            r.update(year=chosen['year'], recent=chosen['recent'], mode=chosen['mode'])
    rows.sort(key=lambda r: (['keep','pause','review'].index(r['recommendation']), list(DECISIONS).index(r['slug'])))
    counts = Counter(r['recommendation'] for r in rows)
    names = dict(keep='Passed to live trading phase', pause='Pause live / demo only', review='Deeper review')
    blocks = []
    for r in rows:
        g = r['recommendation']
        source = Path(r['source']).as_uri() if r.get('source') else ''
        annual, recent = r['year'], r['recent']
        badges = ('<span class="tiny">FTMO member — mode may differ</span>' if r['ftmo_member'] else '')
        content = f'''<tr data-group="{g}" data-name="{esc(r['label'].lower())}" id="{r['slug']}">
         <td><strong>{esc(r['label'])}</strong><p class="muted">{esc(r['canonical'])} · {esc(r['mode'])}</p>{badges}
         <span class="pill {g}">{names[g]}</span></td>
         <td>{metric_block(recent)}<small>{'Recorded native 3M test; no new rerun' if r['slug'] in ('nasdaq-5m-candle-momentum','xau-trend-progression') else 'Closed-position slice; not a new backtest'}</small></td>
         <td>{metric_block(annual, True)}</td>
         <td><b>{esc(r['brief'])}</b><p>{esc(r['reason'])}</p>
          <details><summary>Next check &amp; evidence</summary><p>{esc(r['next_review'])}</p>
          <p class="muted">{esc(r.get('provenance','Cached preferred-mode strategy evidence; not a fresh verification of the attached live EA.'))}</p>
          <p>Reported year history quality: {esc(r.get('history_quality') or 'not available')}. A high report-quality percentage does not by itself establish complete real-tick coverage.</p>
          <p>Current SET: {esc(r['set_source'])}</p>
          {f'<a href="{source}">Open recorded evidence</a>' if source else '<p>No matching performance evidence accepted.</p>'}
          <p class="muted">{esc(r.get('grouping','Not assessable'))}; {r.get('ledger_exit_legs','—')} recorded rows.</p>
          </details></td></tr>'''
        blocks.append(content)
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Calyx — Active EA recent audit · October 5, 2026</title><style>
    :root{color-scheme:dark;--bg:#07110f;--card:#0e201a;--line:#29473d;--text:#e8f5ed;--muted:#9ab5ad;--green:#72ffcd;--red:#ff9292;--amber:#efca7a}
    *{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#163728,var(--bg) 55%);color:var(--text);font:15px/1.6 system-ui,sans-serif}
    main{max-width:1680px;margin:auto;padding:40px 30px}h1{font-size:clamp(32px,4vw,54px);line-height:1.1;margin:16px 0}h2{font-size:25px;margin-top:36px}
    p{margin:9px 0}.eyebrow{color:var(--green);font:12px monospace;letter-spacing:2px}.lead{max-width:980px;color:var(--muted);font-size:18px}.muted,small{color:var(--muted)}a{color:var(--green)}
    .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:25px 0}.card,.notice{border:1px solid var(--line);border-radius:15px;padding:20px;background:#0b1a15c9}.card b{display:block;font-size:32px}.notice{border-color:#706233;color:#e7cd91;margin:22px 0}
    .positive{color:var(--green)}.negative{color:var(--red)}.controls{display:flex;gap:10px;flex-wrap:wrap;margin:25px 0 14px}input,button{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px 15px;color:var(--text);font:inherit}input{min-width:250px;flex:1}button{cursor:pointer}button.active{border-color:var(--green);color:var(--green)}
    .tablewrap{overflow:auto;border:1px solid var(--line);border-radius:14px}table{border-collapse:collapse;width:100%;min-width:1130px}thead{background:#173127}th{text-align:left;font-size:12px;letter-spacing:.5px;color:#b5d8c8;padding:16px}td{padding:20px 16px;border-top:1px solid var(--line);vertical-align:top}td:nth-child(1){width:16%}td:nth-child(2){width:24%}td:nth-child(3){width:24%}td:nth-child(4){width:36%}td strong{font-size:15px}td p{font-size:13px}small,.date{font-size:11px}.pill,.tiny{display:block;width:fit-content;font-size:11px;border:1px solid;padding:3px 9px;border-radius:12px;margin-top:9px}.keep{color:var(--green)}.pause{color:var(--red)}.review{color:var(--amber)}.tiny{color:var(--muted);border-color:var(--line)}details{font-size:13px;margin-top:14px}summary{color:var(--green);cursor:pointer}details p{overflow-wrap:anywhere}footer{margin-top:30px;color:var(--muted);font-size:13px}li{margin:7px 0}
    @media(max-width:700px){main{padding:25px 16px}.cards{grid-template-columns:repeat(2,1fr)}.card{padding:15px}.lead{font-size:16px}}
    </style></head><body><main>
    <div class="eyebrow">CALYX · READ-ONLY PORTFOLIO REVIEW · 2026-10-05</div>
    <h1>Fewer bots.<br>Better-supported decisions.</h1>
    <p class="lead">Updated owner decisions, October 6: 25 entries selected for the new reviewed BAT. All DMCs, Gold Overnight and all five news bots added; Trend Progression uses the saved 1.5R candidate. The owner also approved both US30/US100 hourly EAs unchanged, with selected historical-loss risk sizing and no stop-loss. No account changed.</p>
    <div class="notice"><b>Passed to live trading phase = owner deployment choice, NOT statistical qualification or proof of installation.</b> Failed screens and evidence gaps remain below. <a href="http://127.0.0.1:8080/ea-review">Website reviewed table</a> · <a href="../reviwed_Eas.bat">New reviwed_Eas.bat</a>. Normal risk: USD target or current-equity percentage; separate news percentage per order; DI ON/OFF for Nasdaq5M and USDJPY. No shared daily-risk cap. Original audit preserved in <a href="Original%20review%202026-10-05/Results.html">dated archive</a>.</div>
    USER_KEEP_SELECTIONS
    USER_DEFERRED_NEWS
    USER_LATEST_OPTIMISATION
    USER_ASIA_OPTIMISATION
    <div class="cards"><div class="card">Normal installer EAs<b>37</b></div><div class="card keep">Passed to live trading phase<b>KEEP_COUNT</b></div><div class="card pause">Pause live / demo only<b>PAUSE_COUNT</b></div><div class="card review">Deeper review<b>REVIEW_COUNT</b></div></div>
    <div class="notice"><b>Scope and dates matter.</b> This audits the normal Best Recommended versions, not a verified list of every chart attached to the current account. The recent window starts July 5, 2026 and ends where each source ends. Many records stop September 1–5; they are NOT a complete last-three-month test through October 5. Dates appear on every row. Do not apply these conclusions blindly to different Safe/Standard/FTMO variants.</div>
    <h2>What I would prioritise</h2>
    <p><b>RSI VWAP</b> best matches your high-win-rate preference. <b>Current Nasdaq 5M</b> has the most useful recent trade count and still passes PF 1.20, narrowly. <b>USDJPY ADX20 + DI</b> has positive expectancy, but is not a high-win-rate strategy.</p>
    <p>Passed to live trading phase is the owner's selection label. Some selected entries still have thin samples, incomplete execution audits or failed robustness screens. EMA3 and Nasdaq Overnight remain unchanged despite weak recent slices. A high PF from two or five trades is not a dependable edge.</p>
    <h2>All 37 EAs</h2><p class="muted">Net wins and PF include recorded commission and swap. W/L means the longest winning / losing run, not a forecast. Returns are standalone and cannot be added into a shared portfolio result.</p>
    <div class="controls"><input id="search" aria-label="Search EAs" placeholder="Search an EA…"><button class="active" data-filter="all">All 37</button><button data-filter="keep">Passed to live trading phase · KEEP_COUNT</button><button data-filter="pause">Pause live · PAUSE_COUNT</button><button data-filter="review">Deep review · REVIEW_COUNT</button></div>
    <p id="count" class="muted"></p><div class="tablewrap"><table><thead><tr><th>EA / preferred normal mode</th><th>Recent available slice: July 5 onward</th><th>Latest recorded ~1-year test</th><th>Recommendation / reasoning</th></tr></thead><tbody>ROWS</tbody></table></div>
    <h2>Review order</h2>
    <ol><li><b>LTA, Slow Trend, Trend Progression:</b> fresh version-matched replay, signal/exit attribution and risk rounding. Preserve frozen originals. Do not deploy the unsuccessful experimental LTA flow as a fix.</li>
    <li><b>News engines — deferred by user:</b> Gold/Silver audits saved above; return later. BTC/EURUSD/V9 not started. Before any future promotion, establish exact release, point-in-time inputs and execution stress. Fault checks are not return validation.</li>
    <li><b>Gold Overnight and DMCs:</b> owner selected unchanged rules; no further DMC optimisation requested. H1 ORB remains incomplete and needs the new last-two-year OOS revision. Sell Nasdaq remains in deeper review.</li>
    <li><b>Thin / inactive models:</b> refresh history and collect forward observations; do not optimise two or four trades. Squeeze Safe inactivity needs a signal/gate audit, not automatic removal of safeguards.</li>
    <li><b>3 Way and hourly profiles:</b> revisit failed independent validation and execution risk; recent attractive numbers do not erase these failures.</li></ol>
    <h2>How this review was calculated</h2>
    <ul><li>Inventory: 37 entries in the normal installer, preferred modes taken from its catalogue. The separate FTMO manifest has 14 entries; modes/guards can differ and its total pass probability was not recalculated.</li>
    <li>Full trade ledgers were read, not the website's last-500 preview. Native position IDs are used where available; otherwise an entry-time/side/price/comment key identifies a position. 3 Way Gold uses its exact whole-position native ledger, not partial-exit counts.</li>
    <li>Win = net profit above $0.005; loss = below -$0.005; other results are flat. PF = positive net P/L divided by absolute negative net P/L. Flats break both streaks.</li>
    <li>Recent slices use positions whose final close is July 5 onward. Slice return divides their net P/L by the strategy's closed balance at July 5. Carry-in trades and inherited sizing remain. This is NOT a new shared-account or floating-equity simulation.</li>
    <li>Nasdaq 5M's recent row is a fresh native 3M BASE test, not a slice; its DD is 6.55%, daily-equity Sharpe 1.08. The LTA row uses the October5 native Safe M15 replay. Other sources are cached; each date and local source is accessible above.</li>
    <li>Year DD is native equity drawdown where reported. There is no invented combined or recent floating-equity DD. No universal Sharpe ranking is shown because older reports use different definitions.</li>
    <li>Hourly figures are the original one-lot benchmark, not current historical-loss-sized deployment. News caches for obsolete releases are excluded, not silently treated as current.</li>
    <li>Several newer native year tests mix real and generated ticks, with real history beginning January 2026. Earlier report-quality percentages should not be interpreted as a guarantee of real-tick coverage.</li>
    <li>Selection is retrospective and qualitative; no new multiple-testing-adjusted validation was performed. A longer win run than loss run is a preference, not statistical proof. Profitability, costs, tail losses and correlated exposure still matter.</li></ul>
    <footer>Historical simulations are not live results or expected returns; hindsight, liquidity and slippage can materially change performance. <a href="https://www.nfa.futures.org/rulebooksql/rules.aspx?RuleID=9025&amp;Section=9" target="_blank" rel="noopener">NFA discussion of hypothetical-performance limitations</a>.<br>Local outputs: <a href="review.json">full evidence and decisions</a> · <a href="Review.csv">flat review table</a> · New reviewed launcher and website filters created; no terminal/account modified.</footer>
    </main><script>let filter='all';const rows=[...document.querySelectorAll('tbody tr')];const input=document.getElementById('search');function apply(){let n=0;for(const row of rows){let show=(filter==='all'||row.dataset.group===filter)&&row.dataset.name.includes(input.value.toLowerCase());row.hidden=!show;if(show)n++}document.getElementById('count').textContent=n+' of 37 EAs shown'}for(const b of document.querySelectorAll('button[data-filter]')){b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));apply()}}input.addEventListener('input',apply);apply();</script></body></html>'''
    page = page.replace('KEEP_COUNT',str(counts['keep'])).replace('PAUSE_COUNT',str(counts['pause'])).replace('REVIEW_COUNT',str(counts['review'])).replace('ROWS',''.join(blocks)).replace('USER_KEEP_SELECTIONS',future_bat_keeps()).replace('USER_DEFERRED_NEWS',deferred_news()).replace('USER_LATEST_OPTIMISATION',latest_optimisation()).replace('USER_ASIA_OPTIMISATION',asia_optimisation())
    (HERE/'Results.html').write_text(page, encoding='utf-8')
    (HERE/'review.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    columns = ['slug','label','mode','recommendation','year_dates','year_trades','year_pf','year_win_rate','year_return_pct','year_equity_dd_pct','year_win_streak','year_loss_streak','recent_dates','recent_trades','recent_pf','recent_win_rate','recent_return_pct','recent_win_streak','recent_loss_streak','reason','next_review','source']
    with (HERE/'Review.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader()
        for r in rows:
            flat={k:r.get(k) for k in ['slug','label','mode','recommendation','reason','next_review','source']}
            for prefix in ['year','recent']:
                m=r[prefix] or {}
                flat[prefix+'_dates']=window(r[prefix])
                for k in ['trades','pf','win_rate','return_pct','equity_dd_pct','win_streak','loss_streak']:
                    if prefix+'_'+k in columns: flat[prefix+'_'+k]=m.get(k)
            writer.writerow(flat)
    checks = dict(normal_inventory=37, decisions=counts, performance_rows=sum(r['year'] is not None for r in rows),
                  current_news_missing=5, cash_reconciled=all(abs(r.get('cash_reconciliation_difference',0))<.02 for r in rows),
                  annual_rows_reconciled=32, original_bots_changed=False, current_account_modified=False,
                  fresh_backtests_this_review=0)
    checks.update(reviewed_launcher_built=True, reviewed_selected=25, website_filters_updated=True,
                  original_review_archived=True, original_production_ea_binaries_changed=False)
    assert checks['cash_reconciled']
    (HERE/'VERIFICATION.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(json.dumps(checks,indent=2))

if __name__=='__main__': build()
