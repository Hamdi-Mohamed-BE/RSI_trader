"""Generate a self-contained research report from the frozen native ledgers."""
import html, json, math
from datetime import datetime, timezone
import audit as a

def esc(v): return html.escape(str(v))
def num(v, places=2): return '—' if v is None else f'{float(v):.{places}f}'
def pct(v): return '—' if v is None else f'{v:+.2f}%'
def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def chart(first, second, symbol):
    w,h,left,top=760,260,62,22
    series=[first['daily_curve'],second['daily_curve']]
    vals=[(p['balance']/10000-1)*100 for s in series for p in s]
    lo,hi=min(min(vals),0)-1,max(max(vals),0)+1
    width,height=w-left-22,h-top-45
    def y(v): return top+(hi-v)/(hi-lo)*height
    parts=[f'<svg role="img" aria-label="{symbol} daily closing balance returns" viewBox="0 0 {w} {h}">']
    for i in range(5):
        v=lo+(hi-lo)*i/4
        parts.append(f'<line x1="{left}" x2="{w-22}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#254238"/><text x="{left-8}" y="{y(v)+4:.1f}" text-anchor="end">{v:.1f}%</text>')
    for s,color in zip(series,['#7dffd0','#ffd17c']):
        points=' '.join(f'{left+i/(len(s)-1)*width:.1f},{y((p["balance"]/10000-1)*100):.1f}' for i,p in enumerate(s))
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/>')
    parts.append(f'<text x="{left}" y="{h-8}">{series[0][0]["date"]}</text><text text-anchor="end" x="{w-22}" y="{h-8}">{series[0][-1]["date"]}</text></svg>')
    return ''.join(parts)

def main():
    s=a.build_summary()
    bits=['''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CPI / NFP / FOMC — News Reversion Raw Results</title><style>
    :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#07130f;color:#e9fff5;font:16px/1.55 system-ui,Segoe UI,sans-serif}main{max-width:1280px;margin:auto;padding:36px 24px 80px}h1{font-size:clamp(27px,4vw,44px);line-height:1.15}h2{margin-top:36px}h3{margin-top:22px}p{max-width:1050px;color:#b8d4c9}a{color:#7dffd0}.tag{display:inline-block;padding:5px 12px;border:1px solid #39634f;border-radius:20px;font-size:12px;letter-spacing:1px;color:#7dffd0}.notice{border:1px solid #a98530;background:#302810;padding:18px;border-radius:12px;color:#ffe7a3;margin:18px 0}.panel{border:1px solid #274d3f;background:#0c2118;border-radius:14px;padding:20px;margin:20px 0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;white-space:nowrap}td,th{text-align:right;padding:12px 14px;border-bottom:1px solid #254238}th{color:#99c4b3;font-size:12px}td:first-child,th:first-child{text-align:left}tbody tr:hover{background:#143526}details{margin:14px 0}summary{cursor:pointer;color:#7dffd0;padding:8px 0}.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}svg{width:100%;display:block}svg text{fill:#a6cdbc;font:12px system-ui}.legend{font-size:13px}.muted{color:#a6c3b8;font-size:14px}.good{color:#7dffd0}.bad{color:#ff9a9a}li{margin:8px 0}@media(max-width:850px){.two{grid-template-columns:1fr}main{padding:20px 12px}td,th{padding:9px}}
    </style></head><body><main><span class="tag">RESEARCH ONLY · NO LIVE CHANGES</span><h1>News fair-price reversion<br>CPI, NFP and FOMC</h1>''']
    bits.append('<p>Requested: <strong>8 October 2025–7 October 2026</strong>. Actual price archive ends <strong>6 October 2026, 23:59 UTC</strong>. The last event is 2 October 2026; the calendar has 31 releases (11 CPI, 12 NFP, 8 FOMC decisions). Each asset/version starts independently with $10,000 and targets 1% current equity per trade. These are broker CFDs; US100 is USTEC, not NQ futures.</p>')
    bits.append('<div class="notice"><strong>Important execution caveat:</strong> all recorded 2026 entry quotes for EURUSD and BTCUSD have zero bid/ask spread. Most US100 entry quotes also have zero spread (7/11 short-only entries and 11/16 mirrored entries); gold has one such entry in each version. The real-tick archive starts 1 January 2026; the 2025 segment uses generated ticks. These are preliminary simulation results, not proof of executable news profits. Native commissions, recorded spreads and swap are included, but missing realistic news spreads/slippage can overstate returns.</div>')
    bits.append('<p><strong>Conclusion:</strong> US100 is the strongest candidate for further research. BTC short-only has just nine trades; gold is modest and EURUSD short-only loses. No configuration is ready for live promotion from this test. The 31-event sample is small, parameters are assumptions, and this year is not untouched out-of-sample validation.</p>')
    headers=['Asset','Trades','Return','Net $','PF','Win rate','Floating DD','Daily Sharpe','Win / loss streak']
    for variant,title in [('short_only','Main test — short only, as described in the clip'),('mirrored_both_sides','Separate sensitivity — buys after downward spikes too')]:
        rows=[]
        for symbol in a.C['symbols']:
            m=s[f'{symbol} {variant}']['metrics']
            rows.append(['US100 (USTEC)' if symbol=='USTEC' else symbol,m['trades'],pct(m['return_pct']),num(m['net_usd']),num(m['pf']),num(m['win_rate_pct'],1)+'%',num(m['max_floating_dd_pct'])+'%',num(m['daily_equity_sharpe']),f'{m["win_streak"]} / {m["loss_streak"]}'])
        bits.append('<h2>'+title+'</h2>'+table(headers,rows))
    bits.append('<p class="muted">DD is native maximum floating-equity drawdown over every simulated tick. Sharpe uses UTC calendar-day closing equity returns with √365 annualisation and zero risk-free rate; it is not MT5’s trade-level Sharpe. Streaks count net-of-cost wins/losses; a flat trade resets a streak.</p>')
    bits.append('<h2>Equity curves — separate accounts, not a shared portfolio</h2><div class="two">')
    for symbol in a.C['symbols']:
        bits.append('<section class="panel"><h3>'+('US100 (USTEC)' if symbol=='USTEC' else symbol)+'</h3>'+chart(s[f'{symbol} short_only'],s[f'{symbol} mirrored_both_sides'],symbol)+'<p class="legend"><span style="color:#7dffd0">● Short only</span> &nbsp; <span style="color:#ffd17c">● Mirrored both sides</span></p><p class="muted">Daily closing balance, % of the initial $10,000. Intraday floating drawdown is retained separately in the table.</p></section>')
    bits.append('</div><h2>Frozen rules and what was assumed</h2><div class="panel"><ol>')
    rules=[
        'At each CPI, NFP or FOMC policy decision, save the bid close of the completed M1 candle immediately before the release. This is a reference price, not a verified economic fair value.',
        'Freeze ATR(14) from the completed pre-news M5 candle. The first release M1 candle must close at least 1 ATR beyond the reference price. Main version only accepts upward spikes; mirrored version also accepts downward spikes.',
        'On subsequent completed M1 candles, wait for reversal displacement OR a close through a confirmed three-bar swing pivot. Displacement body ≥0.5 pre-news ATR, body/range ≥60%, and close in the outer 25% in the reversal direction. The pivot is not usable until its right-hand neighbour closes.',
        'Sell the upward spike (or buy the downward spike in the mirrored test) only while price remains beyond the reference. Entry window: first 30 minutes, earliest after two completed release candles. At most one trade per event.',
        'Target the frozen pre-news reference price. Set a non-trailing stop 2× pre-news M5 ATR from the entry request price. RR varies by the distance back to the reference; it is not a fixed RR target.',
        'Size down to the broker lot step for 1% current equity planned price-to-stop loss; skip below minimum lot. Fees, execution movement and gaps can exceed that target. No minimum-lot override.',
        'Close after 60 minutes from the fill or 90 minutes from the release, whichever comes first. There is no trailing or partial exit. Native Model 4 with 150 ms execution delay; only two predeclared cases enumerated, no parameter search.'
    ]
    bits.extend('<li>'+esc(rule)+'</li>' for rule in rules)
    bits.append('</ol><p><strong>Not recovered from the clip:</strong> timeframe, impulse threshold, exact reversal/pivot definition, stop multiplier and time windows. Those were frozen before seeing these results. A complete historical market-consensus archive was not retrieved, so there is <strong>no “priced-in news” or surprise filter</strong>. The source-claim itself is not validated.</p></div>')
    bits.append('<h2>By release type — all four assets</h2>')
    for variant in a.C['variants']:
        rows=[]
        for symbol in a.C['symbols']:
            for kind,m in s[f'{symbol} {variant}']['event_groups'].items():
                rows.append([('US100' if symbol=='USTEC' else symbol)+' · '+kind,m['trades'],num(m['net_usd']),pct(m['contribution_to_starting_balance_pct']),num(m['pf']),num(m['win_rate_pct'],1)+'%' if m['win_rate_pct'] is not None else '—'])
        bits.append('<details open><summary>'+esc(variant.replace('_',' '))+'</summary>'+table(['Asset · event','Trades','Net $','Contribution %','PF','Win rate'],rows)+'</details>')
    bits.append('<p class="muted">Release-type and subperiod percentage figures are cash-P&amp;L contributions to the original $10,000, not independently compounded reruns. The NFP label covers the whole Employment Situation release, not an isolated headline number; FOMC is the decision release, not a separate press-conference entry.</p>')
    bits.append('<h2>Recent results and annual contributions</h2>')
    periodrows=[]
    for key, item in s.items():
        for period,m in item['period_groups'].items():
            periodrows.append([esc(key.replace('USTEC','US100')),period,m['trades'],num(m['net_usd']),pct(m['contribution_to_starting_balance_pct']),num(m['pf']),num(m['win_rate_pct'],1)+'%' if m['win_rate_pct'] is not None else '—'])
    bits.append(table(['Variant','Period','Trades','Net $','Contribution %','PF','Win rate'],periodrows))
    bits.append('<p class="muted">Recent windows end 7 October 2026 exclusive (actual archive end); last 3 months begin 7 July 2026 and last 6 months begin 7 April 2026. The 2025 contribution starts 8 October. No new sizing reset is applied for these breakdowns.</p>')
    bits.append('<h2>Added-cost sensitivity — illustrative, not an execution validation</h2><p>A zero-spread quote cannot provide a credible spread-widening test. Below, each recorded trade is charged an additional 0.025R, 0.05R, 0.10R or 0.20R (R = its intended cash-risk budget). Lots remain frozen. These are explicit hypothetical penalties, not measured broker costs or tick-level reruns.</p>')
    costrows=[]
    for key,item in s.items():
        for m in item['cost_sensitivity']:
            costrows.append([esc(key.replace('USTEC','US100')),num(m['extra_cost_r_per_trade'],3)+'R',pct(m['return_pct']),num(m['pf']),num(m['win_rate_pct'],1)+'%'])
    bits.append(table(['Variant','Extra cost / trade','Return','PF','Win rate'],costrows))
    bits.append('<h2>Sample uncertainty, holding time and execution checks</h2>')
    rows=[]
    for key,item in s.items():
        m=item['metrics'];q=item['quality'];ci=m['win_rate_wilson95_pct']
        rows.append([esc(key.replace('USTEC','US100')),num(ci[0],1)+'–'+num(ci[1],1)+'%',num(m['average_win_usd']),num(m['average_loss_usd']),num(m['mean_hold_minutes'],1),num(m['maximum_hold_minutes'],1),m['stop_losses_exceeding_budget'],f'{q["zero_spread_entry_quotes_2026"]}/{q["entry_quotes_2026"]}'])
    bits.append(table(['Variant','Win rate 95% interval','Avg win $','Avg loss $','Mean hold min','Max hold min','SL losses > budget','Zero-spread 2026 entries'],rows))
    bits.append('<p class="muted">Wilson intervals are marginal descriptive intervals under independent Bernoulli outcomes, not corrections for correlated event types or multiple research choices. All variants have fewer than 30 trades. Stops do not guarantee 1% realised loss. Native tests finished with zero open positions, zero rejected entries and zero rejected time-close requests. Gold had no tradable window for the 3 April 2026 NFP release; its 30 started events plus one explicitly skipped event reconcile to the 31-event calendar.</p>')
    bits.append('<h2>Full trade and skipped-event breakdowns</h2>')
    for key,item in s.items():
        rows=[]
        for t in item['trades']:
            rows.append([esc(t['open_time_ny'].replace('T',' ')),t['event'],t['side'],t['signal'],num(t['open_price'],5),num(t['initial_sl'],5),num(t['initial_tp'],5),num(t['volume']),num(t['fill_to_target_rr']),num(t['hold_minutes'],1),t['exit_label'],num(t['net_profit']),num(t['realised_r'])])
        bits.append('<details><summary>'+esc(key.replace('USTEC','US100'))+' · '+str(len(rows))+' trades</summary>'+table(['Entry New York (offset)','Event','Side','Signal','Entry','SL','Reference TP','Lots','Initial RR','Hold min','Exit','Net $','Net R'],rows)+'</details>')
        bits.append('<details><summary>'+esc(key.replace('USTEC','US100'))+' · all 31 event dispositions</summary>'+table(['Release New York','Event','Disposition','Trades','Net $'],[[esc(e['release_ny']),e['event'],esc(e['disposition']),e['trades'],num(e['net_usd'])] for e in item['events']])+'</details>')
    bits.append('<h2>Reproducibility and source coverage</h2><p>Frozen source/settings/calendar hashes, compiled binaries, native fixed-case XML, deal ledgers, quote samples, equity samples and journals are retained alongside this report. The private tester configuration is excluded from Git. No active terminal, live BAT, website preset or trading rule was changed. Verification checks are documented in <a href="VERIFICATION.json">VERIFICATION.json</a>; the raw summary is in <a href="SUMMARY.json">SUMMARY.json</a>.</p><p>The calendar uses cached official receipts and current official schedules plus the 2 October NFP provider receipt. Current schedules are not independently archived pre-release calendar vintages. Retrospective release timestamps are used only for event chronology; no economic outcome or later surprise value enters the signal. Official HTTP extraction returned 403; browser research and saved official receipts were used. The public calendar connector alone was history-truncated and was not treated as a full-year archive.</p><p>Primary sources: <a href="https://www.bls.gov/schedule/2025/home.htm">BLS 2025 schedule</a>, <a href="https://www.bls.gov/schedule/2026/home.htm">BLS 2026 schedule</a>, <a href="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm">Federal Reserve FOMC calendars</a>, <a href="https://www.federalreserve.gov/newsevents/pressreleases/monetary20251029a.htm">October 2025 decision receipt</a>, <a href="https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm">September 2026 decision receipt</a>. Exact per-event sources and receipts are saved in calendar.json.</p>')
    bits.append('<p class="muted">Generated '+esc(datetime.now(timezone.utc).isoformat())+'. Source code and assumptions were frozen before the runs. This is a raw price-pattern adaptation, not a reproduction of disclosed proprietary settings and not a full two-year out-of-sample pipeline. Historical simulated results do not guarantee future performance.</p></main></body></html>')
    (a.R/'Results.html').write_text('\n'.join(bits),encoding='utf-8')
    print(json.dumps({k:{'trades':v['metrics']['trades'],'return_pct':v['metrics']['return_pct'],'pf':v['metrics']['pf'],'sharpe':v['metrics']['daily_equity_sharpe'],'event_groups':v['event_groups']} for k,v in s.items()},indent=2))

if __name__=='__main__': main()
