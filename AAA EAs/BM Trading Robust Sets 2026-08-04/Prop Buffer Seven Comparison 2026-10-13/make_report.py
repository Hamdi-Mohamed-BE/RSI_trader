"""Build a self-contained research report from frozen, offline results."""
from pathlib import Path
import hashlib, json, math

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'RESULTS.json').read_text())
assert len(data['results'])==360 and len(data['histories'])==108
assert data['code_sha256']==hashlib.sha256((ROOT/'run.py').read_bytes()).hexdigest()
for r in data['results']:
    s=r['summary'];n=s['paths']
    assert n==(2000 if r['method']=='bootstrap' else 27 if r['task']=='challenge_180d' else 40)
    if r['task']=='challenge_180d':
        assert abs(s['pass_rate_pct']+s['failure_rate_pct']+s['unresolved_rate_pct']-100)<1e-8
    assert abs(sum(s['failure_causes'].values())-s['failure_rate_pct'])<1e-8
for h in data['histories']:
    assert math.isclose(h['stats']['final_balance'],h['engine']['final_balance'],rel_tol=1e-10,abs_tol=1e-5)
    assert h['stats']['trades']==h['engine']['trades']
    assert h['end_exclusive']=='2026-10-06'
validation=dict(synthetic_tests=12,scenario_summaries=360,historical_replays=108,
    bootstrap_paths_per_scenario=2000,rolling_challenge_starts=27,rolling_funded_starts=40,
    report_control_combinations=72,report_date_views=12,
    arithmetic_and_cash_conservation='passed',source_hash=data['plan']['ledger_sha256'],
    code_hash=data['code_sha256'],live_changes=False)
(ROOT/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')

TEMPLATE=r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Calyx · Prop loss-buffer ÷ 7 research</title>
<style>
:root{--bg:#06120f;--panel:#0b211a;--edge:#254c3e;--text:#ecfff7;--muted:#9ec8ba;--green:#68ffcb;--amber:#f5ce6b;--red:#ff908c}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#113326,var(--bg) 65%);color:var(--text);font:15px/1.65 system-ui,sans-serif}main{max-width:1450px;margin:auto;padding:42px 26px}h1{font-size:clamp(28px,4vw,48px);line-height:1.15;margin:12px 0 18px}h2{font-size:25px;margin:0 0 12px}h3{font-size:18px;margin:0 0 10px}p{margin:10px 0;color:var(--muted)}a{color:var(--green)}section{margin-top:34px}.eyebrow{font-size:12px;letter-spacing:2px;color:var(--green)}.banner,.box,.card{background:var(--panel);border:1px solid var(--edge);border-radius:16px;padding:22px}.banner{border-color:#927534;background:#292b14;margin:20px 0}.banner p{color:#f2df9d}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.controls{display:flex;flex-wrap:wrap;gap:14px;align-items:end;margin:20px 0}.controls label{display:block;color:var(--muted);font-size:13px}select{display:block;background:#071b13;color:var(--text);border:1px solid #46715e;border-radius:8px;padding:11px;min-width:155px}input[type=checkbox]{width:18px;height:18px;accent-color:var(--green)}.pill{display:inline-block;border:1px solid var(--edge);border-radius:25px;padding:4px 12px;font-size:12px;color:var(--green);margin:4px 4px 4px 0}.scroll{overflow:auto;border:1px solid var(--edge);border-radius:12px}table{border-collapse:collapse;width:100%;font-size:13px;text-align:left;white-space:nowrap}th,td{padding:12px 14px;border-bottom:1px solid #1e3e30}th{color:var(--muted);background:#0b211a;position:sticky;top:0}td{font-variant-numeric:tabular-nums}td.wrap{white-space:normal;min-width:230px}tbody tr:nth-child(even){background:#0b1b14}.good{color:var(--green)}.warn{color:var(--amber)}.bad{color:var(--red)}.small{font-size:12px;color:var(--muted)}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}.metric{border:1px solid var(--edge);border-radius:10px;padding:11px}.metric span{display:block;color:var(--muted);font-size:10px;letter-spacing:1px}.metric b{font-size:19px}svg{width:100%;height:155px;background:#071910;border-radius:9px}details{margin-top:14px}summary{cursor:pointer;color:var(--green)}ul{color:var(--muted);padding-left:22px}li{margin-bottom:9px}.foot{padding:28px 0;color:var(--muted);font-size:12px}button{background:#153b2a;border:1px solid #3b7357;color:var(--green);padding:10px 18px;border-radius:8px;cursor:pointer}.hidden{display:none}
@media(max-width:900px){.grid,.cards{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}main{padding:24px 14px}}
</style></head><body><main>
<div class="eyebrow">CALYX · RESEARCH ONLY · 13 OCTOBER 2026</div>
<h1>Prop-firm risk: remaining loss buffer ÷ 7</h1>
<p>Four saved portfolios · three two-step programmes · three risk policies. Signals, targets and exits unchanged. No live deployment, BAT, website or account changes.</p>
<span class="pill">$25,000 common reference</span><span class="pill">2,000 correlated-block paths per scenario</span><span class="pill">2025-10-06 → 2026-10-06 exclusive</span><span class="pill">12 synthetic tests passed</span>
<div class="banner"><h3>This does not certify a &lt;1% real-world account-loss probability.</h3><p>We have closed-trade cash and initial-stop references, not true floating equity. The open-stop mode is a reserve stress test, not a measured equity curve or a guaranteed upper bound. A numerical challenge pass is not firm approval. Full portfolio coverage is 36/37; hourly bots have no stop.</p></div>
<section class="grid">
<div class="box"><h3>What the video changes</h3><p>A standard 10% loss allowance gives an initial <strong>1.43% of the account per position</strong>. On $25k that is $357.14 before lot rounding. On $50k it is $714.29—not $285.71, which assumes only $2k of loss allowance.</p><p>Open trades do not shrink the literal closed-balance buffer. Profits can therefore enlarge sizing faster than the daily limit permits.</p></div>
<div class="box"><h3>Most useful comparison</h3><p><strong>Retain the existing FTMO guard.</strong> Its 0.5% initial-capital ceiling already prevents literal ÷7 sizing from expanding normally.</p><p>The combined 17-EA roster benefits from a shared cap: 0.5% per trade, 2% open risk, 1% per symbol and a 2% daily admission reserve. This is a tested candidate—not installed.</p></div>
<div class="box"><h3>Costs matter more than the headline</h3><p>Stress each positive gross trade by −10%, each negative gross trade by +10%, then charge another 0.05R. Under this deliberately adverse execution scenario, the 17-EA portfolios lose much of their challenge-passing edge.</p><p>Do not choose the highest modelled return without checking this sensitivity.</p></div>
</section>
<section><h2>Verified rules & operational eligibility</h2>
<div id="rules" class="grid"></div><p class="small">Current rules applied retrospectively to saved history. Programmes have no overall challenge deadline; 180 days is our observation horizon, not a firm deadline. KYC/review time and fees are excluded. Funded profit is retained; withdrawals and payout/fee ROI are not modelled.</p></section>
<section><h2>Simulated challenges and funded-account survival</h2>
<div class="controls">
<label>Risk policy<select id="policy"><option value="current_defaults">Current portfolio defaults</option><option value="literal_buffer_7">Literal loss buffer ÷ 7</option><option value="guarded_buffer_7" selected>Buffer ÷ 7 + shared caps</option></select></label>
<label>Evidence method<select id="method"><option value="bootstrap">2,000 correlated-block simulations</option><option value="rolling">Actual historical starting dates</option></select></label>
<label>Loss check<select id="floating"><option value="full_stop_reserve_stress">Closed cash minus open-stop reserve</option><option value="closed_only">Closed cash only (optimistic)</option></select></label>
<label><input id="cost" type="checkbox"> Worse-cost + reserve stress</label>
</div><p id="policy-note"></p><p id="mode-note" class="small"></p>
<div class="scroll"><table><thead><tr><th>Portfolio / firm</th><th>Both phases pass<br>within 180d</th><th>Failure<br>within 180d</th><th>Unresolved<br>at 180d</th><th>Median pass<br>calendar days*</th><th>Funded failure<br>within 90d</th><th>90d closed return<br>median [P10, P90]</th><th>Eligibility</th></tr></thead><tbody id="challenge-table"></tbody></table></div>
<p class="small">*Median includes only successful paths; a low pass rate can have a deceptively fast conditional median. Funded trials start fresh, separately from challenge trials. Return includes failed paths up to failure and excludes unrealised cash in positions still open at the horizon. All figures are conditional model outputs, not forecasts or confirmed payouts.</p>
<details><summary>Failure causes, intervals and exposure diagnostics</summary><div class="scroll"><table><thead><tr><th>Portfolio / firm</th><th>Challenge daily / total / inactivity</th><th>Funded daily / total / inactivity / quick</th><th>Funded failure MC95 interval</th><th>Funded 3% exposure flags</th><th>Opposite-side overlap</th><th>Open positions at 90d</th></tr></thead><tbody id="diagnostics"></tbody></table></div><p class="small">MC95 is a Wilson interval for Monte Carlo sampling noise only. It does not include future-market uncertainty, source selection, execution error or omitted firm rules. FundedNext's warning, profit deduction and permanent 1% reclassification mechanics are not replayed; exposure flags are not counted as hard account failure here. Hedging acceptance requires written firm clarification.</p></details>
<details><summary>All risk policies side by side</summary><div class="scroll"><table><thead><tr><th>Portfolio / firm</th><th>Current pass / funded failure</th><th>Literal pass / funded failure</th><th>Guarded pass / funded failure</th></tr></thead><tbody id="comparison"></tbody></table></div></details>
</section>
<section><h2>Actual closed-cash replay: recent portfolio performance</h2>
<div class="controls"><label>Period<select id="period"><option value="3m">3 months</option><option value="6m">6 months</option><option value="1y" selected>1 year</option></select></label></div>
<p>Uses the FTMO daily-reset convention for an apples-to-apples risk-schedule illustration. It does <strong>not</strong> stop the annual replay on a challenge breach or reset capital after a target. Native historical costs retained; no funded reward split. Margin, broker volume caps and true equity remain unverified.</p>
<p id="literal-warning" class="warn hidden">Literal annual compounding is unrestricted by firm breach stopping, margin and maximum broker volume. Its very large return figures are mathematically unconstrained illustrations, not executable account returns. Use the challenge/survival table to evaluate it.</p>
<div id="history-cards" class="cards"></div></section>
<section><h2>Historical trial dates</h2><p>Non-wrapping 180-calendar-day trials, starting every Monday. Dates below are real historical origins and replayed outcomes—not future dates promised by the model. The actual source date controls the firm's daily reset.</p>
<div class="controls"><label>Portfolio<select id="date-portfolio"></select></label><label>Firm<select id="date-firm"></select></label></div>
<div class="scroll"><table><thead><tr><th>Start</th><th>End exclusive</th><th>Both phases passed UTC</th><th>Failed UTC</th><th>Reason</th><th>Closed trades</th><th>Open at horizon</th></tr></thead><tbody id="dates"></tbody></table></div></section>
<section><h2>Portfolio membership · rules retained</h2><div id="membership" class="cards"></div></section>
<section><h2>Method, limits & audit</h2><div class="box"><p>Freeze inputs and policies first, replay entries and exits chronologically, size only from cash known at entry, round lots down, then resample whole 28-day Monday-start blocks. Concurrent source signals stay together; original holding durations carry across blocks. Whole-block seams can distort correlations and flat-account eligibility, especially for long-holding bots.</p><ul id="limits"></ul>
<p>360 scenario summaries · 108 historical portfolio replays · 2,000 paths per bootstrap scenario · 27 actual challenge origins · 40 funded origins. A portfolio entry skipped by shared limits is not replaced with a newly regenerated strategy signal.</p>
<p class="small">Source ledger SHA256: <span id="source-hash"></span><br>Engine SHA256: <span id="engine-hash"></span></p>
<p><a href="PLAN.json">Frozen plan</a> · <a href="RESULTS.json">Full numerical evidence</a> · <a href="VALIDATION.json">Validation</a></p></div></section>
<div class="foot">Research-only. No signal or exit optimisation, no OOS certification, no promised account survival or payouts. Latest common coverage ends October 6, 2026—not today.</div>
</main><script id="research-data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('research-data').textContent), P=D.plan;
const labels={'ftmo':'FTMO guarded (17)','current14-orb05':'Combined + five ORBs (17)','orbs-only':'ORBs only (5)','full-eas':'Full roster (36/37)'}, keys=Object.keys(labels);
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $=id=>document.getElementById(id), fmt=(v,n=1)=>v==null?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:n,minimumFractionDigits:n}), pct=v=>fmt(v)+'%', med=q=>q?fmt(q.median):'—', date=v=>v?E(v.slice(0,19).replace('T',' ')):'—';
const firmLabel=id=>P.firms.find(f=>f.id===id).label;
const elig=(p,f)=>f==='fundingpips'?(p==='full-eas'?'Not eligible: intentional news':p==='orbs-only'?'Own-EA approval + conduct review':'Own-EA approval + hedging review'):f==='fundednext'?'Below $50k + EA add-on; risk review':'Swing; source/broker verification still needed';
function config(){let stress=$('cost').checked;if(stress){$('method').value='bootstrap';$('floating').value='full_stop_reserve_stress'}return{method:$('method').value,float_mode:$('floating').value,cost_stress:stress}}
function get(p,f,policy,task,cfg){return D.results.find(r=>r.portfolio===p&&r.firm===f&&r.policy===policy&&r.task===task&&r.method===cfg.method&&r.float_mode===cfg.float_mode&&r.cost_stress===cfg.cost_stress)?.summary}
function range(q){return q?`${pct(q.median)} [${pct(q.p10)}, ${pct(q.p90)}]`:'—'}
function causes(s,funded=false){return (funded?['daily_loss','total_loss','inactivity','quick_strike']:['daily_loss','total_loss','inactivity']).map(k=>pct(s.failure_causes[k])).join(' / ')}
function curve(points){let vals=points.map(x=>x.balance),lo=Math.min(...vals),hi=Math.max(...vals),span=hi-lo||1;let xy=vals.map((v,i)=>`${8+i/Math.max(1,vals.length-1)*684},${140-(v-lo)/span*125}`).join(' ');return `<svg viewBox="0 0 700 155" role="img" aria-label="Closed balance curve"><polyline points="${xy}" fill="none" stroke="#68ffcb" stroke-width="2" vector-effect="non-scaling-stroke"/><text x="10" y="151" fill="#9ec8ba" font-size="10">Closed cash only · $${fmt(lo,0)} to $${fmt(hi,0)}</text></svg>`}
function metric(label,val){return `<div class="metric"><span>${E(label)}</span><b>${val}</b></div>`}
function render(){const cfg=config(),policy=$('policy').value;
 $('policy-note').textContent=P.policy_details[policy];$('mode-note').textContent=cfg.cost_stress?'Worse-cost stress enabled; reserve = 1.25× stop reference. Bootstrap only.':cfg.float_mode==='closed_only'?'Optimistic: losses between entry and exit are unseen.':'Reserve stress: all open initial-stop references deducted simultaneously; not measured floating equity.';
 let rows='',diag='',compare='';for(const p of keys)for(const f of P.firms){let s=get(p,f.id,policy,'challenge_180d',cfg),u=get(p,f.id,policy,'fresh_funded_90d',cfg);if(!s||!u)continue;
 let title=`${E(labels[p])}<br><span class="small">${E(f.label)}</span>`;
 rows+=`<tr><td class="wrap">${title}</td><td>${pct(s.pass_rate_pct)}</td><td class="${s.failure_rate_pct>5?'bad':'warn'}">${pct(s.failure_rate_pct)}</td><td>${pct(s.unresolved_rate_pct)}</td><td>${med(s.median_calendar_days_to_pass)}</td><td class="${u.failure_rate_pct>5?'bad':'warn'}">${pct(u.failure_rate_pct)}</td><td>${range(u.closed_return_pct)}</td><td class="wrap small ${p==='full-eas'||f.id==='fundingpips'?'warn':''}">${E(elig(p,f.id))}${p==='full-eas'?'<br>No-stop risk proxy; incomplete coverage':''}</td></tr>`;
 diag+=`<tr><td class="wrap">${title}</td><td>${causes(s)}</td><td>${causes(u,true)}</td><td>${u.failure_rate_mc95_pct.map(v=>pct(v)).join(' – ')}</td><td>${f.id==='fundednext'?pct(u.risk_ceiling_flags_path_pct):'n/a'}</td><td>${pct(u.hedge_overlap_path_pct)}</td><td>${pct(u.positions_left_open_path_pct)}</td></tr>`;
 compare+=`<tr><td class="wrap">${title}</td>${P.policies.map(pol=>{const a=get(p,f.id,pol,'challenge_180d',cfg),b=get(p,f.id,pol,'fresh_funded_90d',cfg);return `<td>${pct(a.pass_rate_pct)} / ${pct(b.failure_rate_pct)}</td>`}).join('')}</tr>`}
 $('challenge-table').innerHTML=rows;$('diagnostics').innerHTML=diag;$('comparison').innerHTML=compare;
 $('literal-warning').classList.toggle('hidden',policy!=='literal_buffer_7');
 let cards='';for(const p of keys){let h=D.histories.find(h=>h.portfolio===p&&h.firm==='ftmo'&&h.policy===policy&&h.period===$('period').value),s=h.stats;
 cards+=`<article class="card"><h3>${E(labels[p])}</h3><div class="small">${E(h.start)} → ${E(h.end_exclusive)} exclusive · ${h.coverage.covered_members} covered members</div><div class="metrics">${metric('RETURN',pct(s.return_pct))}${metric('PROFIT FACTOR',fmt(s.profit_factor,2))}${metric('WIN RATE',pct(s.win_rate_pct))}${metric('CLOSED MAX DD',pct(s.max_drawdown_pct))}${metric('TRADES',fmt(s.trades,0))}${metric('SHARPE · DAILY',fmt(s.sharpe_ratio,2))}${metric('WIN / LOSS STREAK',fmt(s.max_win_streak,0)+' / '+fmt(s.max_loss_streak,0))}${metric('TRADES / WEEKDAY',fmt(s.trades_per_weekday,2))}</div>${curve(h.curve)}<p class="small">Max daily closed DD (UTC peak/trough): ${pct(s.max_daily_closed_drawdown_pct)}. Payoff ${fmt(s.payoff_ratio,2)}. True equity DD unavailable.${p==='full-eas'?' Historical-loss-sized no-stop positions included; not bounded risk.':''}</p><details><summary>Monthly closed cash</summary><div class="scroll"><table><thead><tr><th>Month</th><th>Trades</th><th>Net cash</th></tr></thead><tbody>${h.months.map(m=>`<tr><td>${E(m.month)}</td><td>${m.trades}</td><td>$${fmt(m.net_profit,2)}</td></tr>`).join('')}</tbody></table></div></details></article>`}
 $('history-cards').innerHTML=cards;renderDates();
}
function renderDates(){const p=$('date-portfolio').value,f=$('date-firm').value,pol=$('policy').value,mode=$('floating').value;
const r=D.results.find(r=>r.portfolio===p&&r.firm===f&&r.policy===pol&&r.method==='rolling'&&r.float_mode===mode&&r.task==='challenge_180d'&&!r.cost_stress);
const reasons=['—','Daily loss','Total loss','30-day inactivity','Quick Strike'];$('dates').innerHTML=r.rolling_dates.map(d=>`<tr><td>${E(d.start)}</td><td>${E(d.end_exclusive)}</td><td>${date(d.both_phases_pass)}</td><td>${date(d.failure)}</td><td>${reasons[d.failure_cause]}${!d.both_phases_pass&&!d.failure?'Unresolved':''}</td><td>${d.trades}</td><td>${d.positions_left_open}</td></tr>`).join('');}
$('rules').innerHTML=P.firms.map(f=>`<article class="box"><h3>${E(f.label)}</h3><span class="pill">${f.targets.map(v=>pct(v*100)).join(' / ')} targets</span><span class="pill">5% daily / 10% static total</span><p>${f.days} minimum trading days per phase. Daily reset: ${E(f.zone)}.</p><p>${E(f.status)}</p><details><summary>Official sources</summary><ul>${f.sources.map((s,i)=>`<li><a href="${E(s)}" target="_blank" rel="noopener">${i+1}. Official rule source</a></li>`).join('')}</ul></details></article>`).join('');
$('date-portfolio').innerHTML=keys.map(k=>`<option value="${k}">${E(labels[k])}</option>`).join('');$('date-firm').innerHTML=P.firms.map(f=>`<option value="${f.id}">${E(f.label)}</option>`).join('');
$('membership').innerHTML=keys.map(k=>`<div class="box"><h3>${E(labels[k])}</h3><p>${k==='ftmo'?'Existing guarded roster, cash/risk ceilings normalized to $25k. Not the account-bound $10k executable.':k==='current14-orb05'?'Same 17 source EAs, without the existing FTMO admission guard.':k==='orbs-only'?'All five ORBs retain the saved 0.5R targets.':'Missing gold-news-v9-direction. Hourly profiles use historical maximum-loss sizing, not a stop.'}</p><details><summary>${P.members[k].length} selected EAs</summary><ul>${P.members[k].map(m=>`<li>${E(m)}</li>`).join('')}</ul></details></div>`).join('');
$('limits').innerHTML=P.limitations.map(s=>`<li>${E(s)}</li>`).join('');$('source-hash').textContent=P.ledger_sha256;$('engine-hash').textContent=D.code_sha256;
for(const id of ['policy','method','floating','cost','period'])$(id).addEventListener('change',render);for(const id of ['date-portfolio','date-firm'])$(id).addEventListener('change',renderDates);render();
</script></body></html>'''
(ROOT/'Results.html').write_text(TEMPLATE.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\u003c')),encoding='utf-8')
print('Report and validation saved:',ROOT/'Results.html')
