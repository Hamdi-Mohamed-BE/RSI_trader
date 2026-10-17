"""Read the independent audit and render the frozen exploratory pipeline.

Presentation only: no MT5 access, no selection, no recomputation of audited
performance, no optimization, and no changes to installers or live settings.
Run after audit.py has written AUDIT.json and VERIFICATION.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import json
import math
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
UTC = timezone.utc
PARAMETERS = ("target_r", "hold_minutes", "impulse_mult", "entry_window_minutes", "close_fraction")
PARAMETER_LABELS = {"target_r":"Target (R)", "hold_minutes":"Maximum hold (minutes)",
                    "impulse_mult":"Initial displacement / pre-event ATR", "entry_window_minutes":"Entry window (minutes)",
                    "close_fraction":"Directional close fraction"}


def load(path, default=None):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def h(value):
    return html.escape(str(value), quote=True)


def numeric(value):
    return isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value)


def fmt(value, places=2, signed=False, suffix=""):
    if not numeric(value):
        return "—"
    return (f"{value:+,.{places}f}" if signed else f"{value:,.{places}f}") + suffix


def nice(key):
    return str(key).replace("_", " ").strip()


def compact(value, limit=120):
    """Make exact audit summaries readable without embedding simulated paths."""
    if isinstance(value,dict):
        return {k:compact(v,limit) for k,v in value.items()}
    if isinstance(value,list):
        if len(value)>limit:
            return {"array_length":len(value), "first_records":compact(value[:10],limit),
                    "note":"Full array remains in linked audit artifact; not all paths rendered in HTML."}
        return [compact(v,limit) for v in value]
    return value


def exact(value):
    return f'<pre>{h(json.dumps(compact(value),indent=2,ensure_ascii=False))}</pre>'


def local_link(path, label=None, css="pill"):
    path = Path(path)
    if not path.exists():
        return ""
    relative = path.relative_to(ROOT).as_posix()
    return f'<a class="{css}" href="{quote(relative,safe="/")}">{h(label or relative)}</a>'


def artifact_links():
    links = [local_link(p) for p in sorted(ROOT.iterdir(),key=lambda p:p.name.lower()) if p.is_file() and p.suffix.lower() in (".json",".jsonl")]
    for name in ("native/ARTIFACTS.json", "native/manifest.json", "SEARCHPLAN.json", "DATASPLIT.json"):
        path = ROOT/name
        link = local_link(path)
        if link and link not in links:
            links.append(link)
    raw = ROOT.parent / "US500 CPI Continuation vs Reversion Raw 2026-10-16" / "Results.html"
    if raw.exists():
        relative = "../" + raw.parent.name + "/Results.html"
        links.append(f'<a class="pill" href="{quote(relative,safe="/")}">Earlier US500 raw comparison</a>')
    return "".join(links)


def metric(row, key):
    return row.get("metrics",{}).get(key) if isinstance(row,dict) else None


def row_dates(row):
    start = row.get("start") if isinstance(row,dict) else None
    end = row.get("end_exclusive",row.get("end")) if isinstance(row,dict) else None
    return f'{h(start or "—")} → {h(end or "—")} (end exclusive)'


def pf(row):
    value = metric(row,"pf")
    if numeric(value):
        return fmt(value)
    if metric(row,"wins") and not metric(row,"losses"):
        return "∞ · no losses"
    return "—"


def ci_text(row):
    ci = metric(row,"win_rate_wilson_95_pct")
    return f'{ci[0]:.1f}–{ci[1]:.1f}%' if isinstance(ci,list) and len(ci)==2 and all(numeric(x) for x in ci) else "—"


def comparison_table(pair, title=None):
    if not isinstance(pair,dict):
        return '<p class="muted">No comparison record is available in this audit.</p>'
    rows=[]
    for role in ("baseline","selected"):
        row=pair.get(role)
        if not isinstance(row,dict):
            continue
        m=row.get("metrics",{})
        net=m.get("net_profit")
        tone="positive" if numeric(net) and net>0 else "negative" if numeric(net) and net<0 else ""
        n=m.get("trades",0)
        rows.append(f'<tr><td>{"Baseline" if role=="baseline" else "Development-selected candidate"}<small>{row_dates(row)}<br>Start ${fmt(m.get("starting_balance"))}</small></td>'
                    f'<td>{h(n)}</td><td>{fmt(m.get("win_rate_pct"),1,suffix="%")}<small>Wilson 95%: {ci_text(row)}</small></td>'
                    f'<td>{pf(row)}</td><td class="{tone}">{fmt(m.get("return_pct"),2,True,"%")}<small>${fmt(net,2,True)}</small></td>'
                    f'<td>{fmt(m.get("max_closed_dd_pct"),2,suffix="%")}<small>${fmt(m.get("max_closed_dd_usd"))}</small></td>'
                    f'<td>{fmt(m.get("native_equity_dd_pct"),2,suffix="%")}<small>Native replay only; no segment proxy</small></td>'
                    f'<td>{fmt(m.get("daily_closed_sharpe"))}</td><td>{h(m.get("max_win_streak","—"))} / {h(m.get("max_loss_streak","—"))}</td>'
                    f'<td>${fmt(m.get("average_trade"))}<small>{fmt(m.get("avg_realised_r"),3)}R</small></td>'
                    f'<td>{fmt(m.get("max_daily_closed_dd_pct"),2,suffix="%")}<small>${fmt(m.get("max_daily_closed_dd_usd"))}</small></td></tr>')
    intro=f'<h3>{h(title)}</h3>' if title else ""
    return intro+'<div class="scroll"><table><thead><tr><th>Role / dates</th><th>Trades</th><th>Win rate</th><th>PF</th><th>Return / net</th><th>Closed DD</th><th>Floating equity DD</th><th>Daily Sharpe</th><th>Win / loss streak</th><th>Avg trade</th><th>Daily closed DD</th></tr></thead><tbody>'+"".join(rows)+'</tbody></table></div>'


def parameter_table(full_pair):
    baseline=full_pair.get("baseline",{}).get("parameters",{})
    selected=full_pair.get("selected",{}).get("parameters",{})
    rows=[]
    for key in PARAMETERS:
        a,b=baseline.get(key),selected.get(key)
        rows.append(f'<tr><td>{h(PARAMETER_LABELS[key])}</td><td>{h(a if a is not None else "—")}</td><td>{h(b if b is not None else "—")}</td><td>{"Unchanged" if a==b else "Changed before final selection freeze"}</td></tr>')
    same=bool(baseline) and baseline==selected
    note='<p class="muted">The development selection equals the baseline. The two roles are intentionally shown, not represented as two different strategies.</p>' if same else ""
    return '<div class="scroll"><table><thead><tr><th>Setting</th><th>Original baseline</th><th>Development-selected</th><th>Status</th></tr></thead><tbody>'+"".join(rows)+'</tbody></table></div>'+note


def curve_svg(row, title, color="#70e9b9", width=850, height=240):
    curve=row.get("daily_curve",[])
    points=[]
    for item in curve:
        if not isinstance(item,dict) or not numeric(item.get("balance")):
            continue
        try:
            stamp=datetime.fromisoformat(str(item["date"]).replace("Z","+00:00")).replace(tzinfo=UTC).timestamp()
        except (ValueError,KeyError):
            continue
        points.append((stamp,item["balance"]))
    if not points:
        return '<p class="muted">No audited daily closed-balance curve available.</p>'
    start_balance=metric(row,"starting_balance")
    if numeric(start_balance) and row.get("start"):
        stamp=datetime.fromisoformat(row["start"]).replace(tzinfo=UTC).timestamp()
        points.insert(0,(stamp,start_balance))
    left,right,top,bottom=66,15,20,30
    xmin,xmax=min(p[0] for p in points),max(p[0] for p in points)
    ymin,ymax=min(p[1] for p in points),max(p[1] for p in points)
    pad=max(1,(ymax-ymin)*.12)
    ymin,ymax=ymin-pad,ymax+pad
    def xy(point):
        return left+(point[0]-xmin)/max(1,xmax-xmin)*(width-left-right),top+(ymax-point[1])/(ymax-ymin)*(height-top-bottom)
    coords=" ".join(f'{xy(p)[0]:.2f},{xy(p)[1]:.2f}' for p in points)
    lines=[]
    for fraction in (0,.5,1):
        value=ymin+(ymax-ymin)*fraction
        _,y=xy((xmin,value))
        lines.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.2f}" y2="{y:.2f}" stroke="#274d3c"/><text x="{left-8}" y="{y+4:.2f}" text-anchor="end">${value:,.0f}</text>')
    a=datetime.fromtimestamp(xmin,UTC).strftime("%Y-%m-%d")
    b=datetime.fromtimestamp(xmax,UTC).strftime("%Y-%m-%d")
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{h(title)}"><title>{h(title)}</title>{"".join(lines)}<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{coords}"/><text x="{left}" y="{height-7}">{a}</text><text x="{width-right}" y="{height-7}" text-anchor="end">{b}</text></svg>'


def curves(pair,title):
    blocks=[]
    for role,color in (("baseline","#97b9ac"),("selected","#70e9b9")):
        row=pair.get(role)
        if not isinstance(row,dict):
            continue
        blocks.append(f'<div class="chart"><h3>{"Baseline" if role=="baseline" else "Development-selected candidate"}</h3><p class="muted">{row_dates(row)}</p>{curve_svg(row,title+" "+role,color)}</div>')
    return '<div class="two">'+"".join(blocks)+'</div>'


def flatten_summary(value,prefix=""):
    rows=[]
    if isinstance(value,dict):
        for key,child in value.items():
            label=(prefix+" · " if prefix else "")+nice(key)
            if isinstance(child,dict):
                rows.extend(flatten_summary(child,label))
            elif isinstance(child,list):
                if len(child)<=8 and all(not isinstance(x,(dict,list)) for x in child):
                    rows.append((label,", ".join(str(x) for x in child)))
                else:
                    rows.append((label,f'{len(child)} records; full detail below / in audit'))
            else:
                rows.append((label,child))
    else:
        rows.append((prefix or "Value",value))
    return rows


def summary_grid(value):
    rows=flatten_summary(value)
    return '<div class="scroll"><table><tbody>'+"".join(f'<tr><td>{h(label)}</td><td>{h(item if item is not None else "Unavailable")}</td></tr>' for label,item in rows)+'</tbody></table></div>'


def evidence_section(title,value,description="",expanded=False):
    if value is None:
        return f'<section class="panel"><h2>{h(title)}</h2><p class="muted">No matching audit output is available. This check is not claimed complete.</p></section>'
    return f'<section class="panel"><h2>{h(title)}</h2><p>{description}</p>{summary_grid(value)}<details {"open" if expanded else ""}><summary>Exact audited detail</summary>{exact(value)}</details></section>'


def trade_table(row):
    rows=[]
    for trade in row.get("trades",[]):
        def time_text(key,alternative):
            value=trade.get(key)
            if value:
                return str(value)
            value=trade.get(alternative)
            return datetime.fromtimestamp(value,UTC).isoformat().replace("+00:00","Z") if numeric(value) else "—"
        side=trade.get("side","—")
        op,sl,tp=trade.get("open_price"),trade.get("initial_sl"),trade.get("initial_tp")
        risk=abs(op-sl) if numeric(op) and numeric(sl) else None
        rr=abs(tp-op)/risk if numeric(tp) and numeric(op) and risk else None
        net=trade.get("net_profit")
        tone="positive" if numeric(net) and net>0 else "negative" if numeric(net) and net<0 else ""
        rows.append(f'<tr><td>{h(trade.get("release_utc",trade.get("event_epoch","—")))}<small>{h(trade.get("release_ny",""))}</small></td>'
                    f'<td>{h(time_text("open_time","open_epoch"))}<small>Exit {h(time_text("close_time","close_epoch"))}<br>{fmt(trade.get("hold_minutes"),2)} minutes</small></td>'
                    f'<td>{h(side)}<small>{fmt(trade.get("volume"))} lots</small></td><td>{fmt(op,3)}</td><td>{fmt(sl,3)}</td><td>{fmt(tp,3)}<small>{fmt(rr,3)}R at fill</small></td>'
                    f'<td>{fmt(trade.get("close_price"),3)}<small>{h(trade.get("exit_label",trade.get("exit_reason","—")))}</small></td>'
                    f'<td class="{tone}">${fmt(net,2,True)}<small>{fmt(trade.get("realised_r"),3,True)}R net</small></td>'
                    f'<td>${fmt(trade.get("risk_budget"))}<small>Planned ${fmt(trade.get("planned_risk_cash"))}<br>Filled-stop ${fmt(trade.get("filled_initial_risk_cash"))}</small></td>'
                    f'<td>{fmt(trade.get("entry_spread_points"),3)} pts<small>Request bid {fmt(trade.get("request_bid"),3)}<br>ask {fmt(trade.get("request_ask"),3)}</small></td>'
                    f'<td>${fmt(trade.get("commission"))} / ${fmt(trade.get("swap"))} / ${fmt(trade.get("fee"))}</td></tr>')
    if not rows:
        rows=['<tr><td colspan="11">No trades in this audited segment; no win-rate or risk-return inference is made.</td></tr>']
    return '<div class="scroll"><table><thead><tr><th>CPI release</th><th>UTC entry / exit</th><th>Side / size</th><th>Entry</th><th>Initial stop</th><th>Initial target</th><th>Exit / reason</th><th>Net / realized R</th><th>Risk cash</th><th>Entry spread</th><th>Commission / swap / fee</th></tr></thead><tbody>'+"".join(rows)+'</tbody></table></div>'


def stage_table(audit):
    rows=[]
    for alias, analyses in audit.get("stages",{}).items():
        if isinstance(analyses,dict):
            analyses=[analyses]
        for row in analyses:
            if not isinstance(row,dict):
                continue
            m=row.get("metrics",{})
            p=row.get("parameters",{})
            params=" · ".join(f'{nice(k)}={v}' for k,v in p.items())
            rows.append(f'<tr><td>{h(alias)}<small>{h(row.get("label",row.get("stage","")))}<br>Case {h(row.get("index","—"))}</small></td>'
                        f'<td>{row_dates(row)}</td><td>{h(params)}</td><td>{h(m.get("trades","—"))}</td><td>{fmt(m.get("win_rate_pct"),1,suffix="%")}</td>'
                        f'<td>{pf(row)}</td><td>{fmt(m.get("return_pct"),2,True,"%")}</td><td>{fmt(m.get("max_closed_dd_pct"),2,suffix="%")}</td>'
                        f'<td>{fmt(m.get("daily_closed_sharpe"))}</td></tr>')
    return '<div class="scroll"><table><thead><tr><th>Stage / case</th><th>Exact dates</th><th>Frozen parameters</th><th>Trades</th><th>Win rate</th><th>PF</th><th>Return</th><th>Closed DD</th><th>Daily Sharpe</th></tr></thead><tbody>'+"".join(rows)+'</tbody></table></div>'


def trial_register():
    trials=load(ROOT/"trials.json",[])
    if isinstance(trials,dict):
        trials=trials.get("trials",trials.get("records",[]))
    if not isinstance(trials,list) or not trials:
        return '<p class="muted">No saved trial-register records are present. Full-search completion is not implied.</p>'
    rows=[]
    for sequence,trial in enumerate(trials,1):
        if not isinstance(trial,dict):
            continue
        m=trial.get("metrics",{})
        n=m.get("trades",0)
        p=trial.get("parameters",{})
        params=" · ".join(f'{nice(k)}={v}' for k,v in p.items())
        score=next((trial[k] for k in ("score","selection_score","rank_score","development_score") if k in trial),m.get("score"))
        rows.append(f'<tr><td>{sequence}<small>{h(trial.get("phase",trial.get("stage","—")))}<br>{h(trial.get("stage",""))} · local case {h(trial.get("index","—"))}</small></td>'
                    f'<td>{row_dates(trial)}</td><td>{h(params)}</td><td>{h(n)}</td><td>{fmt(m.get("win_rate_pct") if n else None,1,suffix="%")}</td>'
                    f'<td>{fmt(m.get("pf"))}</td><td>{fmt(m.get("return_pct"),2,True,"%")}<small>${fmt(m.get("net",m.get("net_profit")),2,True)}</small></td>'
                    f'<td>{fmt(m.get("balance_dd",m.get("max_closed_dd_pct")),2,suffix="%")}</td>'
                    f'<td>{fmt(m.get("daily_closed_balance_sharpe",m.get("daily_closed_sharpe")) if n else None)}</td><td>{h(score) if score is not None else "Not stored in this row"}</td></tr>')
    return f'<p class="muted">All {len(trials)} recorded native evaluations from trials.json, in register order. Saved metrics are displayed without reading native CSVs or recomputing training results. Reused configurations and different date windows remain separate evaluations; they are not all unique parameter trials. Non-finite PF is shown as unavailable rather than assigned a made-up value. Selection scores are displayed only when explicitly stored in the row.</p><div class="scroll"><table><thead><tr><th>Register # / phase</th><th>Exact dates</th><th>Parameters</th><th>Trades</th><th>Win rate</th><th>Finite PF</th><th>Return / net</th><th>Closed DD</th><th>Daily closed Sharpe</th><th>Stored score</th></tr></thead><tbody>'+"".join(rows)+'</tbody></table></div>'


def display_search_plan():
    plan=load(ROOT/"SEARCH-PLAN.json",load(ROOT/"SEARCHPLAN.json",{}))
    split=load(ROOT/"DATA-SPLIT.json",load(ROOT/"DATASPLIT.json",{}))
    selection=load(ROOT/"SELECTION.json",{})
    # Names and numbers below describe the predeclared protocol, not fitted
    # outcomes. Exact generated ledgers/selection remain linked and displayed.
    return f'''<section class="panel"><h2>Predeclared search and data splits</h2><div class="two"><div><h3>One factor at a time · beam width one</h3><ol><li>Target candidates: 0.5R, 1R, 1.5R, 2R.</li><li>Maximum hold: 5, 15, 30 minutes.</li><li>Initial displacement threshold: 0.75, 1.0, 1.25 × pre-event ATR.</li><li>Probe the selected centre and original baseline neighbours: target ±0.25R, hold ±5 minutes, impulse ±0.25 ATR within frozen bounds.</li></ol><p>At most two finalists—the development plateau and unchanged baseline—reach the predeclared validation selection. Validation eligibility requires at least six trades, positive net, PF &gt;1, and a profitable development-neighbour majority. If neither qualifies, retain the development fallback and explicitly fail validation; do not choose a new final-evaluation winner.</p><p>No search on the final evaluation period. Actual unique and reused trials are counted in the audited register, not estimated from Cartesian combinations.</p></div><div><h3>Chronological boundaries</h3><ul><li>Development: 2020-01-01 through 2023-10-15.</li><li>Validation: 2023-10-16 → 2024-10-16 exclusive.</li><li>Final retrospective evaluation: 2024-10-16 → 2026-10-16 exclusive.</li><li>Raw three-year gate: 2020-10-16 → 2023-10-16 exclusive.</li><li>The mandatory five-year pre-evaluation raw gate needs unavailable 2018 history; it cannot be marked passed.</li></ul></div></div><details><summary>Exact SEARCH-PLAN.json</summary>{exact(plan)}</details><details><summary>Exact DATA-SPLIT.json</summary>{exact(split)}</details><details><summary>Exact SELECTION.json and freeze timestamp</summary>{exact(selection)}</details></section>'''


def selected_diagnostics(comparisons):
    sections=[]
    for key,label in (("full","Full historical native replay"),("holdout","Last two-year retrospective evaluation")):
        row=comparisons.get(key,{}).get("selected",{})
        if not row:
            continue
        for field,title,description in (
            ("monte_carlo", "Event-block Monte Carlo · "+label,
             "10,000 event-block resamples are uncertainty diagnostics conditional on this small historical sample. Resampling is not new market history, does not repair execution data, and cannot establish a future account-blowup probability."),
            ("cost_stress", "Additional-cost sensitivity · "+label,
             "Extra quote-cost sensitivity is a cash adjustment to recorded trades, not a bid/ask tick re-execution. It does not reproduce different stop/target ordering, missed fills, widened live news spreads or latency-dependent entry decisions."),
            ("sharpe", "Sharpe / deflated Sharpe diagnostics · "+label,
             "Read the tested-family count, benchmark and small-sample assumptions in the audit. Any deflated-Sharpe probability remains an approximation under dependent, sparse event returns; it is not independent proof of an edge."),
            ("calendar_thirds", "Chronological thirds · "+label,
             "Stability across chronological segments, without choosing the best segment after seeing its return."),
            ("concentration", "Profit concentration · "+label,
             "Shows dependence on a small number of events; a strong headline result dominated by one release is fragile.")):
            sections.append(evidence_section(title,row.get(field),description))
        sections.append(evidence_section("Recent-half PF · "+label,row.get("recent_half_pf"),"Recent-half results are reported, not used to retune the final evaluation period."))
    return "".join(sections)


def render(audit,verification,config):
    comparisons=audit.get("comparisons",{})
    full=comparisons.get("full",{})
    holdout=comparisons.get("holdout",{})
    validation=comparisons.get("validation",{})
    periods=comparisons.get("periods",{})
    yearly=periods.get("yearly",comparisons.get("yearly",{}))
    selected=holdout.get("selected",{})
    sm=selected.get("metrics",{})
    tiles=[("Retrospective evaluation trades",str(sm.get("trades","—"))),
           ("Win rate",fmt(sm.get("win_rate_pct"),1,suffix="%")),("Profit factor",pf(selected)),
           ("Return",fmt(sm.get("return_pct"),2,True,"%")),("Closed drawdown",fmt(sm.get("max_closed_dd_pct"),2,suffix="%")),
           ("Daily closed Sharpe",fmt(sm.get("daily_closed_sharpe")))]
    tiles_html="".join(f'<div><span>{h(label)}</span><strong>{h(value)}</strong></div>' for label,value in tiles)
    period_parts=[]
    period_options=[]
    for key,label in (("3m","3 months"),("6m","6 months"),("1y","1 year"),("3y","3 years"),("5y","5 years · descriptive history")):
        if key not in periods:
            continue
        period_options.append(f'<option value="{key}" {"selected" if key=="1y" else ""}>{label}</option>')
        period_parts.append(f'<div class="period {"selected" if key=="1y" else ""}" id="period-{key}">{comparison_table(periods[key],label)}</div>')
    yearly_html="".join(comparison_table(pair,str(year)) for year,pair in sorted(yearly.items())) if isinstance(yearly,dict) else exact(yearly)
    latency={key:value for key,value in audit.get("stages",{}).items() if "delay" in key.lower() or "latency" in key.lower()}
    latency_html="".join(comparison_table({"selected":row},key) for key,values in latency.items() for row in (values if isinstance(values,list) else [values]))
    if not latency_html:
        latency_html='<p class="muted">No 500/1,000 ms native stress outputs are present in this audit; completion is not implied.</p>'
    generated={key:value for key,value in audit.get("stages",{}).items() if "generated" in key.lower()}
    generated_html="".join(comparison_table({"selected":row},key) for key,values in generated.items() for row in (values if isinstance(values,list) else [values]))
    if not generated_html:
        generated_html='<p class="muted">No generated-tick diagnostic output is present in this audit.</p>'
    limit_html="".join(f'<li>{h(item)}</li>' for item in audit.get("limitations",[]) if isinstance(item,(str,int,float)))
    verdict=audit.get("verdict",{})
    metadata=audit.get("metadata",{})
    freeze_proof={key:metadata.get(key) for key in ("selection_freeze_utc","freeze_precedes_selected_holdout","launch_order_proof","validation_gate_scope") if key in metadata}
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>US500 CPI continuation — exploratory full pipeline</title><style>
:root{{--bg:#07130f;--panel:#0d2019;--text:#e7fff3;--muted:#a0b8af;--line:#2a4b3c;--green:#72efb9;--red:#ff9794;--gold:#f4cd7c}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at top right,#143c2b,var(--bg) 65%);color:var(--text);font:15px/1.6 system-ui,Segoe UI,sans-serif}}main{{max-width:1560px;margin:auto;padding:46px 26px 90px}}h1{{font-size:clamp(32px,4vw,49px);line-height:1.15;margin:16px 0;max-width:1100px}}h2{{font-size:26px;margin:8px 0 15px}}h3{{font-size:19px;margin:16px 0 8px}}a{{color:var(--green)}}p{{max-width:1220px}}.eyebrow{{font:12px ui-monospace,monospace;letter-spacing:2px;color:var(--green)}}.muted,small{{color:var(--muted)}}small{{display:block;font-size:11px;font-weight:400;max-width:270px}}.badge{{display:inline-block;padding:5px 12px;border:1px solid #876c33;color:var(--gold);border-radius:50px;font-size:11px;letter-spacing:1px}}.warning{{border:1px solid #8c7135;background:#2b2514b5;color:#f6dfa7;border-radius:14px;padding:20px;margin:24px 0}}.panel{{background:#0a1c15e3;border:1px solid var(--line);border-radius:18px;padding:26px;margin:25px 0}}.pills{{display:flex;gap:7px;flex-wrap:wrap}}.pill{{display:inline-block;padding:7px 11px;border:1px solid var(--line);border-radius:8px;text-decoration:none;font-size:12px}}.tiles{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:24px 0}}.tiles>div{{border:1px solid var(--line);background:#0d251ac9;border-radius:12px;padding:17px}}.tiles span{{font-size:11px;color:var(--muted)}}strong{{display:block;font-size:27px;color:var(--text);line-height:1.4;margin-top:6px}}.scroll{{overflow:auto;border:1px solid var(--line);border-radius:12px;margin:18px 0}}table{{border-collapse:collapse;width:100%;text-align:left;font-size:13px}}td,th{{padding:13px 12px;border-bottom:1px solid #254334;vertical-align:top}}th{{color:var(--muted);font-size:11px;background:#0c251a;white-space:nowrap}}td{{font-variant-numeric:tabular-nums}}tr:last-child td{{border-bottom:0}}.positive{{color:var(--green)}}.negative{{color:var(--red)}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.chart{{min-width:0}}svg{{display:block;width:100%;margin:15px 0}}svg text{{font:11px system-ui;fill:var(--muted)}}details{{border-top:1px solid var(--line);padding:15px 0;margin-top:10px}}summary{{cursor:pointer;color:var(--green);font-weight:600}}pre{{white-space:pre-wrap;overflow:auto;max-height:550px;font:11px/1.55 ui-monospace,monospace}}li{{margin:7px 0}}select{{padding:10px 14px;border:1px solid var(--green);background:#102b1e;color:var(--text);border-radius:8px;font:inherit}}.period{{display:none}}.period.selected{{display:block}}@media(max-width:1000px){{.tiles{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:720px){{main{{padding:28px 14px}}.panel{{padding:18px}}.tiles{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}td,th{{padding:10px}}}}@media print{{body{{background:white;color:black}}.period{{display:block}}.scroll{{overflow:visible}}.muted,small,a{{color:#333}}}}
</style></head><body><main>
<p class="eyebrow">CALYX RESEARCH · US500 / S&amp;P 500 CFD · 16 OCTOBER 2026</p><h1>CPI continuation: exploratory full pipeline</h1><p>Development-only bounded search, predeclared validation selection, neighbourhood checks, walk-forward probes and a final two-year retrospective evaluation. Exness US500 CFD—not ES futures. $10,000 initial deposit per replay, 0.25% dynamic planned initial-stop risk; baseline delay 150 ms.</p><span class="badge">NON-PROMOTABLE · RESEARCH ONLY · NO LIVE CHANGES</span>
<div class="warning"><b>A better-looking selected result cannot override missing mandatory evidence.</b> The required five-year pre-evaluation raw window needs unavailable 2018 history. The last two years contain at most 23 scheduled CPI events, so the minimum 30-trade evaluation gate cannot be met with one trade per event. The latest two years were already inspected in the earlier raw study and are retrospective—not genuinely untouched. Historical generated ticks and uncertain event spreads remain material limitations.</div>
<div class="pills">{artifact_links()}</div>
<div class="tiles">{tiles_html}</div>
<section class="panel"><h2>Final decision</h2><p>This run continues exploratory research despite raw-gate limitations, as authorized. Selection means selected by the frozen development protocol—not approved for deployment.</p>{summary_grid(verdict)}<details><summary>Exact final verdict</summary>{exact(verdict)}</details>{summary_grid(audit.get("gates",{}))}</section>
{evidence_section("Unchanged promotion requirements",config.get("promotion_rules_unchanged"),"The raw gates also require at least 30 trades and PF ≥1.15, including the unavailable five-year raw window. Monte Carlo must have at least 95% positive-profit probability, positive fifth-percentile return and fifth-percentile PF above one; OOS requires at least 30 trades, DSR ≥95% and reliable event bid/ask evidence. Permission to explore does not relax these requirements.")}
<section class="panel"><h2>Baseline versus development-selected candidate</h2>{parameter_table(full)}{comparison_table(full,"Full historical replay")}{comparison_table(validation,"Validation segment")}{comparison_table(holdout,"Last two-year retrospective evaluation")}<p class="muted">Each row shows its audited replay/window starting balance. Returns are net profit ÷ that balance. Continuous-account subperiods are not reset arbitrarily; a separately launched holdout starts from its explicitly recorded native deposit. Different replays are alternatives, not one combined portfolio.</p></section>
<section class="panel"><h2>Native-ledger closed-balance paths</h2><p class="muted">Daily closed-balance curves from audited native fills, including no-trade calendar days. These are not intraday floating-equity paths. Full native equity DD is listed only where a matching native replay provides it; no segment equity-DD proxy is invented.</p><h3>Full replay</h3>{curves(full,"Full native closed balance")}<h3>Latest two-year retrospective evaluation</h3>{curves(holdout,"Retrospective evaluation native closed balance")}</section>
<section class="panel"><h2>Recent and yearly breakdowns</h2><label for="period">Window </label><select id="period">{"".join(period_options)}</select>{"".join(period_parts)}<p class="muted">The five-year descriptive slice is 2021-10-16 → 2026-10-16 exclusive, using the continuous full-account history. It mixes development, validation and retrospective evaluation dates. It is NOT the unavailable five-year PRE-evaluation raw gate (2018-10-16 → 2023-10-16), does not replace that gate, and is not used to retune the selected model.</p><details><summary>All calendar years · exact dates and starting balances</summary>{yearly_html}</details><p class="muted">Win rate and PF use net position cash including recorded commission/swap/fees. Sharpe uses daily closed-balance returns × √365, including no-trade calendar days. Closed DD includes the window-start balance; daily closed DD resets at UTC midnight. Wilson intervals describe the observed sample, not an independent-event or multiple-testing-corrected guarantee.</p></section>
<section class="panel"><h2>Trading rules held fixed</h2><ol><li>Use the documented CPI schedule at 08:30 New York, DST aware. Headline/core releases are one event. No actual-versus-consensus filter: no verified point-in-time consensus archive is assumed.</li><li>Pre-event reference: exact last completed M1 close. ATR uses 14 true ranges from 15 consecutive M1 bars strictly before the release.</li><li>Only the fixed first release-aligned minute defines the impulse. Require sufficient close displacement versus the pre-event ATR and a close in the directional outer quartile.</li><li>Enter a continuation only on an executable breakout of that first candle’s extreme after its close and within the entry deadline. Stop beyond its opposite extreme plus 0.1 pre-event ATR and one tick.</li><li>Selected target/holding/impulse settings are displayed above. One signal attempt per event; quote freshness ≤2 seconds, positive entry spread, spread ≤10% of stop distance, downward-rounded broker lot sizing. No forced fallback entry.</li><li>No trailing, partials or break-even. Time-close at the configured holding deadline; hard-flat by release +60 minutes at an executable quote. Tester-only guard; no live operation.</li></ol></section>
{display_search_plan()}
{evidence_section("Trial family and multiple-testing register",audit.get("trial_count"),"The correction must count unique development configurations, reused baseline trials, neighbourhood probes and walk-forward searches as disclosed—not just the ultimately selected candidate.")}
<section class="panel"><h2>Full recorded native trial register</h2>{trial_register()}</section>
<section class="panel"><h2>Audited replay summary</h2><p class="muted">Audit stage aliases and their recorded cases are summarized here; the complete saved evaluation register is above. Development rankings are not replaced with final-evaluation rankings.</p>{stage_table(audit)}</section>
{evidence_section("Raw mandatory gates",audit.get("raw_gates"),"Raw gates remain recorded as failed or unavailable even when exploratory work is allowed to continue. A missing five-year raw window is not substituted with a shorter window.")}
{evidence_section("Walk-forward probes",audit.get("walk_forward"),"Predeclared 3×3 grid: target [0.5, 1.5, 2]R × hold [5, 15, 30] minutes, impulse fixed at 1 ATR. Fold one trains on 2020–2021 and tests 2022; fold two trains on 2020–2022 and tests January–15 October 2023. Test periods are chronological probes, not extra untouched final data.")}
{evidence_section("Limited searched-family null diagnostic",audit.get("null_family"),"This is a centred-P&L sign-flip diagnostic for the searched family—not a strategy rerun on fully reconstructed fake bid/ask markets. It does not preserve every market dependence, volatility cluster, execution interaction or data defect, and cannot substitute for a full price-path null experiment. The full family count and assumptions remain visible.")}
{selected_diagnostics(comparisons)}
<section class="panel"><h2>Native latency stress · 500 and 1,000 ms</h2><p>These are separately replayed native delay scenarios, not a fixed cash subtraction. They still inherit the available historical tick/spread limitations; simulated delay does not reconstruct missing live event liquidity.</p>{latency_html}</section>
<section class="panel"><h2>Generated-tick model diagnostic</h2><p>The frozen selected model is replayed under an explicitly generated-tick model as an engine/data sensitivity check, not a selectable alternative. Agreement would not prove realistic news execution; disagreement is a warning about intrabar path dependence.</p>{generated_html}</section>
<section class="panel"><h2>Every selected-candidate evaluation trade</h2><p class="muted">Latest two-year evaluation only. Entry target R uses the actual fill and initial stop/target. Realized net R and filled-stop cash risk are the audit’s estimates, not a promise that slippage cannot exceed planned loss.</p>{trade_table(selected)}</section>
{evidence_section("Selection freeze and run chronology",audit.get("selection"),"The exact selection freeze timestamp must precede the first selected final-evaluation launch. This proves the recorded run sequence only; it does not make previously inspected history untouched.",True)}
{evidence_section("Owned launch-order evidence",freeze_proof,"Recorded selection-freeze UTC, first selected evaluation launch UTC and owned-process receipt hashes. This is chronological evidence, not a claim of an untouched market sample.",True)}
{evidence_section("Source / cash / elementary causality reconciliation",audit.get("verification"),"Passed reconciliation means the frozen source, native artifacts, cash ledgers and basic chronology agree. It is NOT a strategy-validation pass and NOT a certificate of real historical event quotes.")}
<section class="panel"><h2>Independent verification receipt</h2>{summary_grid(verification)}<details><summary>Exact verification receipt</summary>{exact(verification)}</details></section>
<section class="panel"><h2>Limitations and what is not changed</h2><ul>{limit_html}<li>Measured live news-cost evidence remains insufficient; the 2026 baseline contains only one entry. A positive bid/ask spread is not proof of authentic or representative tick coverage.</li><li>Monte Carlo paths, DSR and small out-of-sample samples cannot establish a reliable sub-1% chance of account failure.</li><li>No live EA, BAT, website, profile, account setting or GitHub state is changed by this report. No next asset is started by the renderer.</li></ul><p class="muted">Presentation generated {datetime.now(UTC).isoformat()}. Performance and gate decisions are read from AUDIT.json; the renderer does not optimize, select or retest anything.</p></section>
</main><script>const selector=document.getElementById('period');if(selector)selector.addEventListener('change',function(){{document.querySelectorAll('.period').forEach(x=>x.classList.remove('selected'));const p=document.getElementById('period-'+this.value);if(p)p.classList.add('selected')}});</script></body></html>'''


def main():
    audit_path=ROOT/"AUDIT.json"
    verification_path=ROOT/"VERIFICATION.json"
    assert audit_path.exists() and verification_path.exists(), "Run the independent audit before rendering"
    audit=load(audit_path)
    verification=load(verification_path)
    config=load(ROOT/"config.json",{})
    assert isinstance(audit.get("comparisons"),dict), "Missing audited comparisons"
    assert all(role in audit["comparisons"].get("full",{}) for role in ("baseline","selected")), "Full baseline / selected comparison missing"
    assert all(role in audit["comparisons"].get("holdout",{}) for role in ("baseline","selected")), "Final evaluation comparison missing"
    report=ROOT/"Results.html"
    report.write_text(render(audit,verification,config),encoding="utf-8")
    print(json.dumps({"report":str(report), "sha256":hashlib.sha256(report.read_bytes()).hexdigest(),
                      "source_audit_sha256":hashlib.sha256(audit_path.read_bytes()).hexdigest(),
                      "research_only":True,"live_changes":False,"strategy_validated":False},indent=2))


if __name__=="__main__":
    main()
