"""Render the root driver's FINAL.json; no statistics, account access or tests run.

Only build_report(root) writes Results.html. Importing this module does not read
evidence, launch processes, or access any terminal, INI or journal.
"""
from __future__ import annotations

from html import escape
import json
import math
from pathlib import Path
from urllib.parse import quote


def h(value):
    return escape(str(value), quote=True)


def label(value):
    return str(value).replace("_", " ").strip()


def pick(data, *keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def number(value, suffix="", places=2, signed=False):
    if value is None or isinstance(value, bool):
        return '<span class="muted">Unavailable</span>'
    try:
        value = float(value)
    except (TypeError, ValueError):
        return h(value)
    if not math.isfinite(value):
        return '<span class="muted">Undefined</span>'
    text = f"{value:+,.{places}f}" if signed else f"{value:,.{places}f}"
    return h(text + suffix)


def simple(value):
    if value is None:
        return '<span class="muted">Unavailable</span>'
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return '<pre>' + h(json.dumps(value, indent=2, ensure_ascii=False, default=str)) + '</pre>'
    return h(value)


def details(title, value, opened=False):
    if value is None:
        return '<p class="muted">No ' + h(title.lower()) + ' supplied.</p>'
    return '<details' + (' open' if opened else '') + '><summary>' + h(title) + '</summary><div class="detail-body">' + simple(value) + '</div></details>'


def table(headers, rows, caption=None):
    if not rows:
        return '<p class="muted">No matching evidence supplied.</p>'
    title = '<caption>' + h(caption) + '</caption>' if caption else ''
    return '<div class="table-scroll" tabindex="0"><table>' + title + '<thead><tr>' + ''.join('<th scope="col">' + h(x) + '</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + str(cell) + '</td>' for cell in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def _metrics(value):
    return value.get("metrics", value) if isinstance(value, dict) else {}


def period_table(periods):
    rows = []
    for period in periods or []:
        for name in ("baseline", "selected"):
            version = period.get(name, {})
            metrics = _metrics(version)
            missing_ids = version.get("missing_week_ids") if isinstance(version, dict) else None
            missing_count = len(missing_ids) if isinstance(missing_ids, list) else metrics.get("missing_week_count")
            if missing_count is None:
                coverage = '<span class="pill unavailable">Coverage unavailable</span><small>Descriptive only</small>'
            elif missing_count > 0 or metrics.get("coverage_evidence_pass") is False:
                coverage = '<span class="pill fail">Incomplete evidence · ' + h(missing_count) + ' weeks</span><small>Descriptive only; missing history not certified</small>'
            else:
                coverage = '<span class="pill neutral">0 missing weeks reported</span><small>Bar surrogate only, not native execution</small>'
            title = h(period.get("label", "Period"))
            dates = h(str(period.get("start", "")) + " → " + str(period.get("end", period.get("end_exclusive", ""))))
            basis = pick(metrics, "cost_basis", "basis") or "Gross offline surrogate unless explicitly identified otherwise"
            rows.append([
                '<strong>' + title + '</strong><small>' + dates + '</small>',
                '<span class="variant ' + name + '">' + name.title() + '</span>',
                number(pick(metrics, "trades", "closed_positions"), places=0),
                coverage,
                number(pick(metrics, "win_rate_pct", "win_rate"), "%"),
                number(pick(metrics, "profit_factor", "pf")),
                number(pick(metrics, "return_pct", "return_percent"), "%", signed=True),
                number(pick(metrics, "closed_dd_pct", "max_closed_dd_pct"), "%"),
                number(pick(metrics, "weekly_sharpe", "weekly_return_sharpe", "annualized_weekly_sharpe")),
                number(pick(metrics, "max_win_streak", "max_winning_streak"), places=0) + ' / ' + number(pick(metrics, "max_loss_streak", "max_losing_streak"), places=0),
                '<small class="basis">' + h(basis) + '</small>',
            ])
    return table(["Period · start inclusive / end exclusive", "Version", "Trades", "Missing weeks / bar evidence", "Win rate", "PF", "Return", "Closed DD", "Weekly Sharpe ×√52", "Max W / L streak", "Evidence basis"], rows)


def _time(value):
    try:
        value = int(value)
    except (ValueError, TypeError):
        return None
    return f"{value // 60:02d}:{value % 60:02d}"


def selected_rules(selection):
    if not isinstance(selection, dict):
        return '<p class="muted">No selected configuration supplied.</p>'
    config = pick(selection, "selected_config", "parameters", "config", "selected_parameters")
    if not isinstance(config, dict):
        return details("Selection evidence", selection)
    entry = {0: "Scheduled clock entry", 1: "Clock entry + last completed candle bullish", 2: "Clock entry + last completed close above its predecessor"}
    stop = {0: "None", 1: "ATR multiple", 2: "Percent of entry price", 3: "Previous completed candle low minus 0.1 ATR"}
    management = {0: "None", 1: "Break-even at the configured R trigger", 2: "ATR trailing", 3: "Percentage trailing", 4: "Chandelier", 5: "Lock 50% of maximum favorable profit after +1R"}
    filters = {0: "None", 1: "EMA50 trend", 2: "EMA200 trend", 3: "ADX20", 4: "ADX25", 5: "ADX20 + DI agreement", 6: "Causal ATR-percentile band", 7: "Recorded positive-spread cap"}
    rows = []
    for key, text in [("entry_mode", entry), ("stop_mode", stop), ("management_mode", management), ("filter_mode", filters)]:
        value = config.get(key)
        if value is not None:
            try:
                meaning = text.get(int(value), "Unrecognized mode")
            except (ValueError, TypeError):
                meaning = "Unrecognized mode"
            rows.append([h(label(key)), h(meaning), simple(value)])
    for key in ("timeframe_minutes", "stop_value", "target_rr", "management_value", "filter_value"):
        if key in config:
            rows.append([h(label(key)), simple(config[key]), ''])
    for key, day in (("entry_minute_ny", "Friday"), ("exit_minute_ny", "Sunday")):
        if key in config:
            clock = _time(config[key])
            rows.append([h(label(key)), h(day + ' ' + str(clock) + ' America/New_York'), simple(config[key])])
    identity = pick(selection, "selected_config_id", "config_id", "selected_id")
    status = pick(selection, "selection_status", "status")
    return '<p><span class="tag">' + h(identity or "Configuration ID unavailable") + '</span></p><p>' + h(label(status or "Selection status unavailable")) + '</p>' + table(["Rule", "Selected setting", "Exact mode / value"], rows) + '<p class="muted">Mode values are shown exactly. Zero target R means no fixed target; the scheduled Sunday deadline remains. Conditional switches only operate where the frozen rule permits them.</p>' + details("Full selection and frozen inputs", selection)


def date_cards(split):
    if not isinstance(split, dict):
        return '<p class="muted">Frozen split unavailable.</p>'
    rows = []
    for key, title in [("development", "Development"), ("validation", "Older validation"), ("oos", "Final two-year OOS")]:
        value = split.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            start, end = value[0], value[1]
        elif isinstance(value, dict):
            start, end = value.get("start"), pick(value, "end_exclusive", "end")
        else:
            start, end = None, None
        rows.append('<article class="split-card"><span>' + h(title) + '</span><strong>' + h(start or "Unavailable") + '</strong><small>to ' + h(end or "Unavailable") + ' exclusive</small></article>')
    return '<div class="split-grid">' + ''.join(rows) + '</div>'


def _gate_state(value):
    if isinstance(value, dict):
        for key in ("passed", "pass", "gate", "ok"):
            if key in value:
                return _gate_state(value[key])
        return _gate_state(value.get("status"))
    if value is True:
        return "pass", "Pass"
    if value is False:
        return "fail", "Fail"
    if value is None:
        return "unavailable", "Unavailable"
    text = str(value)
    lower = text.lower()
    if any(word in lower for word in ("unavailable", "not_run", "not run", "missing", "insufficient", "unknown")):
        return "unavailable", label(text)
    if any(word in lower for word in ("fail", "reject", "not_validated", "not validated")):
        return "fail", label(text)
    if lower in ("pass", "passed", "true", "complete", "verified"):
        return "pass", label(text)
    return "neutral", label(text)


def gate_table(gates):
    if not isinstance(gates, dict):
        return details("Gate evidence", gates)
    rows = []
    for key, value in gates.items():
        kind, text = _gate_state(value)
        reason = pick(value, "reason", "scope", "note", "details") if isinstance(value, dict) else None
        rows.append([h(label(key)), '<span class="pill ' + kind + '">' + h(text) + '</span>', simple(reason) if reason is not None else ''])
    return table(["Registered check", "Recorded result", "Reason / scope"], rows)


def source_section(source):
    rows = []
    coverage = source.get("coverage", []) if isinstance(source, dict) else []
    if isinstance(coverage, dict):
        coverage = [dict(v, timeframe=k) if isinstance(v, dict) else {"timeframe": k, "value": v} for k, v in coverage.items()]
    for row in coverage:
        if not isinstance(row, dict):
            continue
        rows.append([simple(pick(row, "timeframe", "label")), number(pick(row, "rows", "bars"), places=0),
                     simple(pick(row, "first_utc", "first")), simple(pick(row, "last_bar_open_utc", "last_utc", "last")),
                     number(pick(row, "gaps", "gap_count"), places=0), number(pick(row, "nonpositive_spread_bars", "zero_spread_bars"), places=0),
                     simple(row.get("start_covered")), simple(row.get("end_covered"))])
    return table(["Timeframe", "Bars", "First captured bar", "Last captured bar OPEN", "Gaps", "Unknown / nonpositive spreads", "Start covered", "End covered"], rows) + details("Source provenance, actual coverage and gaps", source)


def native_section(audit):
    """Only RECORDED cases enter the performance table; failed runs are not zeroes."""
    audit = audit if isinstance(audit, dict) else {}
    cases = audit.get("cases") or []
    if isinstance(cases, dict):
        cases = [dict(value, tag=value.get("tag", key)) for key, value in cases.items() if isinstance(value, dict)]
    recorded = [case for case in cases if isinstance(case, dict) and str(case.get("status", "")).upper() == "RECORDED"]
    failures = [case for case in cases if isinstance(case, dict) and str(case.get("status", "")).upper() != "RECORDED"]
    rows = []
    for case in recorded:
        metrics = _metrics(case)
        native_report = metrics.get("native_report") or {}
        closed_dd = metrics.get("closed_position_dd") or {}
        rows.append([
            '<strong>' + h(case.get("tag", "Case tag unavailable")) + '</strong><small>' + h(case.get("scope", "Native tester evidence")) + '</small>',
            simple(case.get("start")), simple(pick(case, "end_exclusive", "end")),
            number(case.get("model"), places=0), number(pick(metrics, "trades", "closed_positions"), places=0),
            number(pick(metrics, "win_rate_pct", "win_rate"), "%"), number(pick(metrics, "profit_factor", "pf")),
            number(pick(metrics, "return_pct", "return_percent"), "%", signed=True),
            number(closed_dd.get("pct"), "%"), number(native_report.get("max_drawdown_pct"), "%"),
            number(metrics.get("max_win_streak"), places=0) + ' / ' + number(metrics.get("max_loss_streak"), places=0),
            number(native_report.get("sharpe_ratio")), simple(native_report.get("history_quality")),
        ])
    explanation = '<div class="notice"><strong>Read native costs separately from the gross search.</strong><br>These cases use the present tester contract/account cost settings, including applicable commission and swap. They are not a reconstruction of historical financing. Gross surrogate results below are not promoted to executable net results. <strong>100% report history quality does not mean 100% real ticks.</strong> Check each case\'s real/generated tick notes.</div>'
    return '<section id="native" class="native-primary"><h2>Native broker-cost comparison · read first</h2>' + explanation + table([
        "Case / scope", "Start inclusive", "End exclusive", "Model", "Trades", "Win rate", "PF", "Native return", "Closed-position DD", "MT5 equity DD", "Max W / L streak", "MT5 Sharpe", "Report history quality"
    ], rows) + '<p class="muted">Closed-position DD and MT5 equity DD are different measures. MT5 Sharpe is the native report value, not the weekly closed-return Sharpe in the offline table. Missing or failed runs are never assigned zero performance.</p>' + details("Failed or unavailable native cases · not replaced", failures) + details("Complete native audit, tick quality and case provenance", audit) + '</section>'


def native_oos_section(comparison, audit):
    """Present supplied cases, or resolve explicit tags without deriving results."""
    if not isinstance(comparison, dict):
        return ''
    available = audit.get("cases", []) if isinstance(audit, dict) else []
    if isinstance(available, dict):
        available = [dict(value, tag=value.get("tag", key)) for key, value in available.items() if isinstance(value, dict)]
    by_tag = {case.get("tag"): case for case in available if isinstance(case, dict)}
    supplied = comparison.get("cases") or []
    if isinstance(supplied, dict):
        supplied = [dict(value, tag=value.get("tag", key)) for key, value in supplied.items() if isinstance(value, dict)]
    rows = []
    for value in supplied:
        case = by_tag.get(value, {"tag": value, "status": "Unavailable"}) if isinstance(value, str) else value
        if not isinstance(case, dict):
            continue
        recorded = str(case.get("status", "")).upper() == "RECORDED"
        metrics = _metrics(case) if recorded else {}
        dd = metrics.get("closed_position_dd") or {}
        native = metrics.get("native_report") or {}
        rows.append([
            '<strong>' + h(case.get("tag", "Unavailable case")) + '</strong><small>' + h(label(case.get("status", "Unavailable"))) + '</small>',
            simple(case.get("start")) + '<small>to ' + h(pick(case, "end_exclusive", "end") or "Unavailable") + ' exclusive</small>',
            number(case.get("model"), places=0), number(metrics.get("trades"), places=0),
            number(metrics.get("win_rate_pct"), "%"), number(metrics.get("profit_factor")),
            number(metrics.get("return_pct"), "%", signed=True), number(dd.get("pct"), "%"),
            number(native.get("max_drawdown_pct"), "%"),
        ])
    return '<section id="native-oos" class="native-primary"><h2>Two-year native OOS · baseline vs frozen selection</h2><p class="muted">The supplied native cases include present tester costs. This is retrospective evaluation, not untouched OOS; the selected strategy remains the same frozen research candidate.</p>' + table([
        "Native case / status", "Date range", "Model", "Trades", "Win rate", "PF", "Net native return", "Closed-position DD", "MT5 equity DD"
    ], rows) + details("Supplied native OOS comparison", comparison) + '</section>'


def cash_only_monte_carlo_section(native_robustness):
    """Expose native closed-cash resampling with its own coverage, not a forecast."""
    supplement = native_robustness.get("closed_cash_only_supplement") if isinstance(native_robustness, dict) else None
    if not isinstance(supplement, dict):
        return ''
    cases = supplement.get("cases") or {}
    if isinstance(cases, list):
        cases = {case.get("tag", "Case " + str(i + 1)): case for i, case in enumerate(cases) if isinstance(case, dict)}
    if not isinstance(cases, dict):
        cases = {}
    rows = []
    for tag, case in cases.items():
        if not isinstance(case, dict):
            continue
        coverage = case.get("coverage") or {}
        scheduled = coverage.get("scheduled_weeks")
        if scheduled is None and isinstance(coverage.get("scheduled_week_ids"), list):
            scheduled = len(coverage["scheduled_week_ids"])
        missing = coverage.get("missing_week_ids")
        known = scheduled - len(missing) if isinstance(scheduled, int) and not isinstance(scheduled, bool) and isinstance(missing, list) else None
        diagnostics = case.get("diagnostics") or {}
        primary = diagnostics.get("block_bootstrap") or {}
        run = primary.get("5", primary.get(5)) if isinstance(primary, dict) else None
        conditional = False
        if not isinstance(run, dict) or not isinstance(run.get("distributions"), dict):
            sensitivity = case.get("conditional_complete_cash_week_sensitivity") or {}
            diagnostics = sensitivity.get("diagnostics") or {}
            blocks = diagnostics.get("block_bootstrap") or {}
            run = blocks.get("5", blocks.get(5)) if isinstance(blocks, dict) else None
            conditional = isinstance(run, dict) and isinstance(run.get("distributions"), dict)
        usable = isinstance(run, dict) and isinstance(run.get("distributions"), dict)
        if not usable:
            run = {}
        distributions = run.get("distributions") or {}
        def q(metric, percentile):
            values = distributions.get(metric) or {}
            return values.get(percentile) if isinstance(values, dict) else None
        count_text = (str(known) if known is not None else "Unavailable") + ' known / ' + (str(scheduled) if scheduled is not None else "Unavailable") + ' scheduled weeks'
        if conditional:
            scope = '<span class="pill unavailable">CONDITIONAL · ' + h(count_text) + '</span><small>Calendar compression: missing/unexplained weeks removed. Not full-window evidence.</small>'
        elif usable:
            scope = '<span class="pill neutral">Full supplied cash-week history</span><small>' + h(count_text) + '; closed-balance only</small>'
        else:
            scope = '<span class="pill unavailable">Unavailable · ' + h(count_text) + '</span><small>' + h(label(case.get("status", "No scoped five-week MC supplied"))) + '</small>'
        rows.append([
            '<strong>' + h(tag) + '</strong>', scope, number(run.get("paths"), places=0),
            number(q("return_pct", "p05"), "%", signed=True), number(q("return_pct", "p50"), "%", signed=True),
            number(q("return_pct", "p95"), "%", signed=True), number(q("pf", "p05")),
            number(q("max_closed_dd_pct", "p95"), "%"), number(run.get("probability_profit_pct"), "%"),
        ])
    return '<h3>Native cash-only Monte Carlo · five-week blocks</h3><div class="notice"><strong>Closed-balance evidence only—not a funding forecast.</strong><br>Each row displays the supplied simulation path count. Empirical profitable paths are resampled outcomes, not a predicted chance of profit. Conditional rows omit missing weeks and compress the calendar. <strong>Floating-equity DD, daily-equity loss and prop-account pass probabilities remain unavailable.</strong> This post-freeze supplement does not waive failed validation or promotion gates.</div>' + table([
        "Native case", "Evidence scope", "Paths", "Return p05", "Return p50", "Return p95", "PF p05", "Closed-balance DD p95", "Empirical profitable paths"
    ], rows) + details("Complete closed-cash supplement and coverage receipts", supplement)


def _robustness_runs(value):
    if not isinstance(value, dict):
        return []
    if "block_bootstrap" in value:
        return [("Selected", value)]
    result = []
    for key, child in value.items():
        if isinstance(child, dict) and "block_bootstrap" in child:
            result.append((label(key), child))
    return result


def monte_carlo_section(robustness):
    rows, extras = [], []
    for name, result in _robustness_runs(robustness):
        samples = []
        for block, value in result.get("block_bootstrap", {}).items():
            samples.append(("Block " + str(block) + ' weeks' + (' · primary' if str(block) == '5' else ' · sensitivity'), value))
        if isinstance(result.get("trade_order_reshuffle"), dict):
            samples.append(("Trade-order reshuffle", result["trade_order_reshuffle"]))
        for fraction, value in result.get("trade_removal", {}).items():
            samples.append(("Trade removal · probability " + str(fraction), value))
        for method, value in samples:
            if not isinstance(value, dict):
                continue
            distributions = value.get("distributions", {})
            def q(metric, percentile):
                return distributions.get(metric, {}).get(percentile)
            rows.append([h(name), h(method), number(value.get("paths"), places=0), h(label(value.get("status", "Unavailable"))),
                         number(value.get("probability_profit_pct"), "%"), number(q("return_pct", "p05"), "%", signed=True),
                         number(q("return_pct", "p50"), "%", signed=True), number(q("pf", "p05")),
                         number(q("max_closed_dd_pct", "p95"), "%"), number(q("max_sampled_equity_dd_pct", "p95"), "%"),
                         number(q("max_loss_streak", "p95"), places=0)])
        extras.append(details(name + " · DSR, chronology and unavailable requirements", {k: v for k, v in result.items() if k not in ("block_bootstrap", "trade_order_reshuffle", "trade_removal")}))
    return '<p class="muted">Empirical resampling distributions are not forecasts. Return, PF, closed DD and sampled-path DD must come from the same simulated record sequence. Weekly annualization is 52; separately reported daily calendar Sharpe uses 365.</p>' + table(["Version", "Method", "Paths", "Status", "Paths profitable", "Return p05", "Return p50", "PF p05", "Closed DD p95", "Sampled equity DD p95", "Loss streak p95"], rows) + ''.join(extras) + details("Complete Monte Carlo, family-null and neighbourhood evidence", robustness)


def _cautions(value):
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, dict):
        values = [str(k) + ": " + str(v) for k, v in value.items()]
    else:
        values = value or []
    return '<ul class="cautions">' + ''.join('<li>' + h(v) + '</li>' for v in values) + '</ul>' if values else '<p class="muted">No additional cautions supplied.</p>'


STYLE = """
:root{color-scheme:dark;--bg:#06120f;--panel:#0b1c17;--line:#25493d;--text:#edf7f2;--muted:#9cb7ac;--mint:#70ffd1;--amber:#ffd889;--red:#ff9797}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 90% 0,#12392b 0,transparent 42%),var(--bg);color:var(--text);font:15px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1500px;margin:auto;padding:36px 28px 70px}a{color:var(--mint)}header{border-bottom:1px solid var(--line);padding-bottom:27px;margin-bottom:26px}.eyebrow{font:11px/1.5 ui-monospace,Consolas,monospace;letter-spacing:.19em;color:var(--mint);text-transform:uppercase}h1{font-size:clamp(31px,4.6vw,58px);line-height:1.08;letter-spacing:-.045em;margin:12px 0 17px}h2{font-size:24px;letter-spacing:-.025em;line-height:1.2;margin:0 0 15px}p{margin:10px 0}.lede{max-width:920px;color:var(--muted);font-size:16px}.status{display:inline-block;max-width:100%;overflow-wrap:anywhere;padding:7px 13px;border:1px solid #725b29;background:#302a16;border-radius:99px;color:var(--amber);font-size:12px}.notice{border:1px solid #705c2c;background:#292617;border-radius:12px;padding:16px 20px;margin:18px 0;color:#ffe6a9}.notice strong{color:#fff0cb}.split-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:21px}.split-card{padding:18px 20px;border:1px solid var(--line);border-radius:12px;background:#0b2019}.split-card span,.split-card small{display:block;font-size:12px;color:var(--muted)}.split-card strong{display:block;font-size:21px;margin:5px 0}section{background:linear-gradient(120deg,#0b1b17,#091713);border:1px solid var(--line);padding:25px;border-radius:16px;margin:20px 0}.muted{color:var(--muted)}.table-scroll{overflow-x:auto;max-width:100%;border:1px solid var(--line);border-radius:10px;margin:17px 0;scrollbar-color:#35644f #0a1b14}.table-scroll:focus{outline:2px solid var(--mint);outline-offset:2px}table{border-collapse:collapse;width:100%;min-width:700px;font-size:13px}th{text-align:left;white-space:nowrap;font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);padding:13px 14px;background:#10251c}td{padding:13px 14px;border-top:1px solid #1d3b30;vertical-align:top;font-variant-numeric:tabular-nums}tbody tr:hover{background:#10261d}td small{display:block;color:var(--muted);font-size:11px;line-height:1.5;min-width:170px}td strong{font-size:13px}caption{text-align:left;padding:12px;color:var(--muted)}.variant,.pill,.tag{display:inline-block;border:1px solid #355d4d;border-radius:7px;padding:3px 8px;font-size:11px;white-space:normal;overflow-wrap:anywhere}.variant.selected,.pass{color:var(--mint);background:#123225}.variant.baseline,.neutral{color:#dcece3;background:#172b22}.fail{color:var(--red);border-color:#754343;background:#321d1d}.unavailable{color:var(--amber);border-color:#6d592e;background:#2c2718}.tag{font-family:ui-monospace,Consolas,monospace;color:var(--mint)}details{border-top:1px solid var(--line);margin-top:15px;padding-top:13px}summary{cursor:pointer;color:var(--mint);font-size:13px;font-weight:600}.detail-body{margin-top:12px}pre{background:#06120d;border:1px solid #1c392b;border-radius:9px;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;max-height:520px;overflow:auto;color:#b6d2c2;font:11px/1.65 ui-monospace,Consolas,monospace}.cautions{padding-left:20px;color:var(--muted)}.cautions li+li{margin-top:9px}.evidence-links{display:flex;flex-wrap:wrap;gap:8px;margin:15px 0}.evidence-links a{font-size:12px;padding:6px 10px;border:1px solid var(--line);border-radius:7px;text-decoration:none}footer{padding:20px 2px;color:var(--muted);font-size:12px}nav{display:flex;flex-wrap:wrap;gap:9px;margin:18px 0}nav a{font-size:12px;text-decoration:none;border-bottom:1px solid var(--line)}@media(max-width:700px){main{padding:24px 12px 45px}.split-grid{grid-template-columns:1fr;gap:8px}.split-card{padding:12px 15px}section{padding:18px 13px;border-radius:12px}h2{font-size:21px}.notice{padding:13px 15px}td,th{padding:10px 11px}.lede{font-size:14px}pre{font-size:10px}}
 .native-primary{border-color:#947237;background:linear-gradient(120deg,#17251a,#171d13)}.native-primary h2{color:#ffe3a0}.native-primary td:first-child{min-width:245px;max-width:330px;overflow-wrap:anywhere}
"""


def build_report(root):
    """Read FINAL.json and render only Results.html; return its absolute Path."""
    root = Path(root).resolve()
    source = root / "FINAL.json"
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("FINAL.json must contain an evidence object")
    selection = data.get("selection", {})
    sections = [
        native_oos_section(data.get("native_oos_comparison"), data.get("native_audit")),
        native_section(data.get("native_audit")),
        '<section id="performance"><h2>Baseline vs frozen selection</h2><p class="muted">Each row keeps its supplied date range and cost basis. Recent periods are diagnostics, not selection windows. PF is undefined when no loss denominator exists; missing values are never substituted with zero.</p>' + period_table(data.get("periods")) + '</section>',
        '<section id="rules"><h2>Selected rules</h2>' + selected_rules(selection) + '</section>',
        '<section id="raw"><h2>Raw gates · before optimisation</h2><p class="muted">Exploratory permission does not convert a failed or unavailable raw gate into a pass.</p>' + gate_table(data.get("raw_gates")) + details("Raw gate details", data.get("raw_gates")) + '</section>',
        '<section id="monte-carlo"><h2>Robustness & Monte Carlo</h2>' + cash_only_monte_carlo_section(data.get("native_robustness")) + '<h3>Offline surrogate robustness · separate evidence</h3>' + monte_carlo_section(data.get("robustness")) + details("Native-trade robustness · separate evidence", data.get("native_robustness")) + '</section>',
        '<section id="source"><h2>Source coverage & chronology</h2><p class="muted">The final two-year window is retrospective: recent history was already inspected in the raw study. Export endpoints do not establish continuous usable history. Gaps, simulated ticks and unknown spreads remain limitations.</p>' + source_section(data.get("source_summary")) + '</section>',
        '<section id="costs"><h2>Costs & financing scenarios</h2><p class="muted">Measured broker costs, recorded-bar spread proxies, assumed financing and unknown extra slippage are different evidence types. No assumption is presented as a verified historical fee.</p>' + details("Supplied cost scenarios", data.get("cost_scenarios"), opened=True) + '</section>',
        '<section id="gates"><h2>Promotion gates</h2><p class="muted">Fail and unavailable are both visible. This report does not approve production, a prop-account pass rate or live deployment.</p>' + gate_table(data.get("promotion_gates")) + '</section>',
        '<section id="limitations"><h2>Limitations & cautions</h2>' + _cautions(data.get("cautions")) + '</section>',
    ]
    evidence_names = ["FINAL.json", "PLAN.json", "data-split.json", "DATA.json", "RAW-GATES.json", "SEARCH RESULTS.json", "DEVELOPMENT-STAGES.json", "PLATEAU.json", "SELECTION.json", "FROZEN.json", "OOS.json", "ROBUSTNESS.json", "NATIVE AUDIT.json", "AUDIT.json", "audit.py"]
    links = ''.join('<a href="' + quote(name) + '">' + h(name) + '</a>' for name in evidence_names if (root / name).is_file())
    sections.append('<section id="evidence"><h2>Evidence & reproducibility</h2><div class="evidence-links">' + links + '</div>' + details("Full canonical FINAL.json payload", data) + '</section>')
    verdict = data.get("verdict")
    verdict_html = '<div class="notice"><strong>Final research verdict</strong><p>' + h(verdict) + '</p></div>' if isinstance(verdict, str) and verdict.strip() else ''
    body = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>BTC Weekend Hold · Full Research Pipeline</title><style>' + STYLE + '</style></head><body><main><header><div class="eyebrow">Calyx research · BTCUSD weekend hold</div><h1>A weekend idea.<br>A full evidence trail.</h1><span class="status">' + h(label(data.get("study_status", "Status unavailable"))) + '</span><p class="lede">Original: buy Friday 17:00 New York, close Sunday 17:00. This report compares the original rule with one frozen research selection—not a promise of future returns.</p>' + verdict_html + '<div class="notice"><strong>RESEARCH ONLY · NO LIVE CHANGES</strong><br>Gross bar-surrogate results are not measured all-in net returns. The reference allocates one times current cash; a no-stop position is not 1% stop risk. No EA, BAT, website or active account is changed by generating this report.</div>' + date_cards(data.get("date_split")) + '<nav aria-label="Report sections"><a href="#performance">Periods</a><a href="#rules">Rules</a><a href="#monte-carlo">Monte Carlo</a><a href="#source">Coverage</a><a href="#native">Native audit</a><a href="#gates">Gates</a><a href="#evidence">Evidence</a></nav></header>' + ''.join(sections) + '<footer>Recorded research evidence, not a forecast or investment advice. Native MT5 results, offline overlays and resampling are separate evidence. No live changes.</footer></main></body></html>'
    destination = root / "Results.html"
    destination.write_text(body, encoding="utf-8")
    return destination


if __name__ == "__main__":
    print(build_report(Path(__file__).resolve().parent))
