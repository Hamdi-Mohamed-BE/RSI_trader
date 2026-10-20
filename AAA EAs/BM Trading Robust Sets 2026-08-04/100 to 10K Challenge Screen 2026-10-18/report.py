"""Render saved challenge results only. Never searches, simulates, or trades."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter
import hashlib
import html
import json

ROOT = Path(__file__).resolve().parent
DAY = 86400


def read(root, name):
    return json.loads((root / name).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def esc(value):
    return html.escape(str(value), quote=True)


def number(value, digits=2):
    return "—" if value is None else f"{value:,.{digits}f}"


def money(value):
    return "—" if value is None else "$" + number(value)


def pct(value):
    return "—" if value is None else number(value) + "%"


def utc(value):
    if value is None:
        return "—"
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def expected_starts(window, horizon):
    t, end = [datetime.fromisoformat(x).replace(tzinfo=timezone.utc) for x in window]
    while t.weekday() != 0:
        t += timedelta(days=1)
    out = []
    while t + timedelta(days=horizon) <= end:
        out.append(t.timestamp())
        t += timedelta(days=7)
    return out


def validate(root, plan, source, development, selection, results):
    """Reject stale selections, missing costs, starts or display records."""
    frozen = read(root, "FROZEN.json")
    assert frozen.get("before_challenge_outcomes") is True
    for path, digest in frozen["files"].items():
        assert sha(path) == digest, "Frozen input changed: " + path
    for path, digest in source.get("source_hashes", {}).items():
        assert sha(path) == digest, "Source evidence changed: " + path
    assert results["historical_fraction_not_future_probability"] is True
    assert results["no_live_changes"] is True
    assert results["plan_sha256"] == sha(root / "PLAN.json")
    assert results["inputs_sha256"] == sha(root / "INPUTS.json")
    assert results["selection_sha256"] == sha(root / "SELECTION.json")
    assert results["frozen_sha256"] == sha(root / "FROZEN.json")
    assert selection["frozen_sha256"] == sha(root / "FROZEN.json")
    assert selection["development_sha256"] == sha(root / "DEVELOPMENT.json")
    assert development["frozen_sha256"] == sha(root / "FROZEN.json")
    assert selection["status"] == "LOCKED before evaluation"
    dev_starts = expected_starts(plan["development"], plan["horizon_days"])
    eval_starts = expected_starts(plan["evaluation"], plan["horizon_days"])
    assert development["starts"] == dev_starts and dev_starts and eval_starts
    configs = development["singles"] + development["combos"]
    assert development["configuration_count"] == len(configs)
    assert len({x["id"] for x in configs}) == len(configs)
    assert len(selection["locked"]) == 6
    assert {(x["kind"], x["role"]) for x in selection["locked"]} == {
        (kind, role) for kind in ("single", "combo")
        for role in ("primary", "highest_hit_rate", "fastest_observed")}
    by_config = {c["id"]: c for c in configs}
    for locked in selection["locked"]:
        c = by_config[locked["id"]]
        assert locked["development"] == c["summary"]
        assert locked["keys"] == c["keys"] and locked["risk_pct"] == c["risk_pct"]
    expected = {(c["id"], cost) for c in selection["locked"] for cost in ("recorded", "stress")}
    observed = [(r["id"], r["cost"]) for r in results["results"]]
    assert len(observed) == len(set(observed)) and set(observed) == expected
    for c in configs + results["results"]:
        starts = eval_starts if "cost" in c else dev_starts
        assert [a["start"] for a in c["attempts"]] == starts
        assert c["summary"]["starts"] == len(starts)
        assert c["summary"]["hits"] == sum(a["status"] == "hit" for a in c["attempts"])
        for a in c["attempts"]:
            assert a["end_exclusive"] == a["start"] + plan["horizon_days"] * DAY
            assert a["status"] in ("hit", "floor", "timeout")
    assert len(source["metadata"]["excluded"]) == 7


def receipt(root):
    path = root / "VERIFICATION.json"
    if not path.exists():
        return "PENDING", "Independent verification receipt not present."
    try:
        r = read(root, path.name)
        bindings = {
            "results_sha256": "RESULTS.json",
            "selection_sha256": "SELECTION.json",
            "frozen_sha256": "FROZEN.json",
        }
        if r.get("status") == "PASS" and all(r.get(k) == sha(root / name) for k, name in bindings.items()):
            count = r.get("checks", r.get("verification_checks", r.get("check_count")))
            return "PASS", "Hash-bound independent verification" + (f" · {number(count, 0)} checks" if isinstance(count, (int, float)) else "")
        return "NOT VERIFIED", "Independent receipt is not PASS or does not match these exact result, selection and frozen files."
    except (ValueError, OSError, TypeError):
        return "NOT VERIFIED", "Independent receipt could not be validated."


def recent_receipt(root):
    path = root / "RECENT-VERIFICATION.json"
    if not path.exists():
        return "PENDING", "Supplemental independent verification receipt not present."
    try:
        r = read(root, path.name)
        bindings = {"recent_sha256": "RECENT.json", "recent_frozen_sha256": "RECENT-FROZEN.json",
                    "original_results_sha256": "RESULTS.json"}
        if r.get("status") == "PASS" and all(r.get(k) == sha(root / n) for k, n in bindings.items()):
            count = r.get("checks")
            return "PASS", "Hash-bound supplemental verification" + (f" · {number(count, 0)} checks" if isinstance(count, (int, float)) else "")
        return "NOT VERIFIED", "Supplemental receipt is not PASS or does not match the exact scoreboard, frozen declaration and original results."
    except (ValueError, OSError, TypeError):
        return "NOT VERIFIED", "Supplemental independent receipt could not be validated."


def validate_recent(root, plan, development, recent):
    assert recent["status"] == "RETROSPECTIVE, NOT VALIDATION"
    assert recent["original_results_sha256"] == sha(root / "RESULTS.json")
    assert recent["recent_frozen_sha256"] == sha(root / "RECENT-FROZEN.json")
    frozen = read(root, "RECENT-FROZEN.json")
    assert frozen["before_full_recent_ranking"] is True
    for path, digest in frozen["files"].items():
        assert sha(path) == digest, "Supplemental frozen evidence changed: " + path
    assert read(root, "RECENT-PLAN.json")["window"] == plan["evaluation"]
    original = {c["id"]: c for c in development["singles"] + development["combos"]}
    configs = {c["id"]: c for c in recent["configurations"]}
    assert len(configs) == len(recent["configurations"]) and configs.keys() == original.keys()
    starts = expected_starts(plan["evaluation"], plan["horizon_days"])
    selected = recent["selected"]
    assert len(selected) == 4 and {(c["kind"], c["role"]) for c in selected} == {
        (kind, role) for kind in ("single", "combo") for role in ("primary", "fastest_observed")}
    for c in configs.values():
        assert c["keys"] == original[c["id"]]["keys"] and c["risk_pct"] == original[c["id"]]["risk_pct"]
    for c in selected:
        assert c["keys"] == configs[c["id"]]["keys"] and c["risk_pct"] == configs[c["id"]]["risk_pct"]
        assert (len(c["keys"]) == 1) == (c["kind"] == "single")
    expected = {(c["id"], cost) for c in selected for cost in ("recorded", "stress")}
    observed = [(c["id"], c["cost"]) for c in recent["sensitivity"]]
    assert len(observed) == len(set(observed)) and set(observed) == expected
    for c in list(configs.values()) + recent["sensitivity"]:
        assert [a["start"] for a in c["attempts"]] == starts
        assert c["summary"]["starts"] == len(starts)
        assert c["summary"]["hits"] == sum(a["status"] == "hit" for a in c["attempts"])
        if c.get("cost") == "recorded":
            assert c["summary"] == configs[c["id"]]["summary"]
            assert c["attempts"] == configs[c["id"]]["attempts"]
        for a in c["attempts"]:
            assert a["end_exclusive"] == a["start"] + plan["horizon_days"] * DAY
            assert a["status"] in ("hit", "floor", "timeout")


def risk_receipt(root):
    if not (root / "RISK-VERIFICATION.json").exists():
        return "PENDING", "Risk-ladder independent verification receipt not present."
    try:
        r = read(root, "RISK-VERIFICATION.json")
        bindings = {"risk_sha256": "RISK-SENSITIVITY.json", "protocol_sha256": "RISK-SENSITIVITY-PLAN.json", "recent_sha256": "RECENT.json"}
        if r.get("status") == "PASS" and all(r.get(k) == sha(root / n) for k, n in bindings.items()):
            count = r.get("checks")
            return "PASS", "Hash-bound risk-ladder verification" + (f" · {number(count, 0)} checks" if isinstance(count, (int, float)) else "")
        return "NOT VERIFIED", "Risk-ladder receipt does not match the exact data, protocol and retrospective scoreboard."
    except (ValueError, OSError, TypeError):
        return "NOT VERIFIED", "Risk-ladder receipt could not be validated."


def validate_risk(root, plan, recent, risk):
    protocol = read(root, "RISK-SENSITIVITY-PLAN.json")
    assert risk["status"] == protocol["status"] == "RETROSPECTIVE SAME-PERIOD SENSITIVITY, NOT VALIDATION"
    assert risk["protocol_sha256"] == sha(root / "RISK-SENSITIVITY-PLAN.json")
    assert protocol["recent_sha256"] == sha(root / "RECENT.json")
    assert protocol["original_frozen_sha256"] == sha(root / "FROZEN.json")
    assert protocol["script_sha256"] == sha(root / "risk_sensitivity.py")
    assert protocol["before_ladder_stress_outcomes"] is True
    assert protocol["risks"] == plan["risk_percentages"] and protocol["window"] == plan["evaluation"]
    families = [c for c in recent["selected"] if c["role"] == "primary"]
    assert protocol["families"] == families
    expected = {(c["kind"], tuple(c["keys"]), level, cost) for c in families
                for level in plan["risk_percentages"] for cost in ("recorded", "stress")}
    observed = [(c["kind"], tuple(c["keys"]), c["risk_pct"], c["cost"]) for c in risk["results"]]
    assert len(observed) == len(set(observed)) and set(observed) == expected
    base = {(tuple(c["keys"]), c["risk_pct"]): c for c in recent["configurations"]}
    starts = expected_starts(plan["evaluation"], plan["horizon_days"])
    for c in risk["results"]:
        assert [a["start"] for a in c["attempts"]] == starts
        assert c["summary"]["starts"] == len(starts)
        assert c["summary"]["hits"] == sum(a["status"] == "hit" for a in c["attempts"])
        if c["cost"] == "recorded":
            b = base[tuple(c["keys"]), c["risk_pct"]]
            assert c["summary"] == b["summary"] and c["attempts"] == b["attempts"]
        for a in c["attempts"]:
            assert a["end_exclusive"] == a["start"] + plan["horizon_days"] * DAY
            assert a["status"] in ("hit", "floor", "timeout")


def table(headers, rows, *, cls="", row_ids=None):
    rows = list(rows)
    ids = row_ids or [None] * len(rows)
    assert len(ids) == len(rows)
    head = "".join("<th>" + esc(x) + "</th>" for x in headers)
    body = "".join(
        '<tr' + (f' id="{esc(ident)}"' if ident else "") + ">" +
        "".join("<td>" + str(cell) + "</td>" for cell in row) + "</tr>"
        for row, ident in zip(rows, ids))
    return f'<div class="scroll {esc(cls)}"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def label(keys, labels):
    return " + ".join(esc(labels.get(k, k)) for k in keys)


def ranking(c):
    s = c["summary"]
    if s["hit_pct"] >= 50:
        return (0, s["median_hit_days"], -s["hit_pct"], s["median_closed_dd_pct"], c["id"])
    return (1, -s["hit_pct"], s["mean_capped_days"], -s["ending_cash_median"], c["id"])


def summary_cells(c):
    s = c["summary"]
    return [pct(c["risk_pct"]), f'{s["hits"]}/{s["starts"]} · {pct(s["hit_pct"])}',
            number(s["median_hit_days"]), number(s["all_start_median_days"]),
            pct(s["floor_pct"]), pct(s["timeout_pct"]), money(s["ending_cash_median"]),
            pct(s["median_closed_dd_pct"]), pct(s["worst_closed_dd_pct"])]


SUMMARY_HEADERS = ["Requested risk / trade", "Historical hits / starts", "Median days among hits",
                   "All-start median days¹", "Research-floor %", "Timeout %", "Median ending cash",
                   "Median closed DD", "Worst closed DD"]


def development_table(configs, labels):
    return table(["Rank", "EA configuration", *SUMMARY_HEADERS, "Opened / candidates", "Minimum-lot skips", "Margin skips", "Zero-trade starts"],
        ([str(i), label(c["keys"], labels), *summary_cells(c),
          f'{c["summary"]["total_counts"].get("opened", 0):,}/{c["summary"]["total_counts"].get("candidates", 0):,}',
          number(c["summary"]["total_counts"].get("minimum_lot", 0), 0),
          number(c["summary"]["total_counts"].get("margin_proxy", 0), 0), pct(c["summary"]["no_trade_pct"])]
          for i, c in enumerate(sorted(configs, key=ranking), 1)))


def attempts_table(attempts):
    return table(["Fresh start UTC", "365-day end (exclusive)", "Outcome", "Target confirmed flat UTC",
                  "Days to hit", "Research-floor latch UTC", "Ending closed cash", "Open positions at end",
                  "Max closed DD", "Opened / candidates", "Minimum-lot skips", "Margin skips", "Other skips"],
        ([utc(a["start"]), utc(a["end_exclusive"]), esc(a["status"]), utc(a["hit_epoch"]), number(a["hit_days"]),
          utc(a["floor_epoch"]), money(a["ending_closed_cash"]), str(a["open_positions"]), pct(a["max_closed_dd_pct"]),
          f'{a["counts"].get("opened", 0)}/{a["counts"].get("candidates", 0)}',
          str(a["counts"].get("minimum_lot", 0)), str(a["counts"].get("margin_proxy", 0)),
          esc(", ".join(f"{k}: {v}" for k, v in sorted(a["counts"].items()) if k not in {
              "opened", "candidates", "minimum_lot", "margin_proxy", "closed_positions"}) or "—")]
          for a in attempts))


def detail_html(r, detail, labels):
    s = detail["trade_stats"]
    fastest = r["summary"].get("fastest")
    roles = []
    if fastest and detail["start"] == fastest["start"]:
        roles.append("retrospectively fastest hit")
    middle = sorted(r["attempts"], key=lambda a: a["ending_closed_cash"])[len(r["attempts"]) // 2]
    if middle["start"] == detail["start"]:
        roles.append("middle-ranked ending cash start")
    heading = utc(detail["start"]) + " · " + "; ".join(roles)
    out = [f'<details class="path"><summary>{esc(heading)}</summary>',
           '<p>These paths were selected after evaluation for illustration, not as a representative success probability. '
           'The middle-ranked endpoint uses the upper middle start when the count is even. Trade PF and win rate use completed positions only; '
           'the cash ledger also includes entry fees and partial cashflows.</p>',
           table(["Closed positions", "Win rate", "PF", "Max win / loss streak", "Ending closed cash", "Max closed DD"],
                 [[str(s["trades"]), pct(s["win_rate_pct"]), number(s["profit_factor"]),
                   f'{s["max_win_streak"]} / {s["max_loss_streak"]}', money(detail["ending_closed_cash"]), pct(detail["max_closed_dd_pct"])]]),
           '<h4>Every completed position</h4>',
           table(["Position", "EA", "Entry UTC", "Final exit UTC", "Initial lots", "Initial planned risk", "Net cash"],
                 ([esc(p["id"]), esc(labels.get(p["key"], p["key"])), utc(p["op"]), utc(p["cl"]), number(p["lots"], 4), money(p["risk"]), money(p["net"])]
                  for p in detail["closed_positions"])),
           '<details><summary>Every entry admission or rejection decision</summary>',
           table(["UTC", "Position", "EA", "Decision", "Risk budget", "Floored lots", "Planned stop risk", "Margin proxy"],
                 ([utc(d["epoch"]), esc(d["id"]), esc(labels.get(d["key"], d["key"])), esc(d["decision"]),
                   money(d["budget"]), number(d["volume"], 4), money(d["planned_stop_risk"]), money(d["margin_proxy"])]
                  for d in detail["decisions"])), '</details>',
           '<details><summary>Every saved event-level closed-cash observation</summary>',
           '<p>Observations follow chronological admission and genuine deal events. Repeated timestamps/balances are intentional; '
           'this is not a floating-equity curve. Native same-second ordering can include a publisher 1ms sorting epsilon; '
           'timestamps below display whole seconds, not measured subsecond execution precision.</p>',
           table(["Observation", "UTC", "Closed cash", "Owned open positions"],
                 ([str(i), utc(p["epoch"]), money(p["balance"]), str(p["open_positions"])]
                  for i, p in enumerate(detail["curve"], 1))), '</details></details>']
    return "\n".join(out)


def recent_html(root, plan, development, recent, labels):
    validate_recent(root, plan, development, recent)
    status, text = recent_receipt(root)
    configs = {c["id"]: c for c in recent["configurations"]}
    selected = recent["selected"]
    lookup = {(c["id"], c["cost"]): c for c in recent["sensitivity"]}
    out = ['<h2 id="recent">Later-period retrospective scoreboard — NOT validation</h2>',
           '<div class="warning"><strong>This is an explicitly data-mined description, not an independent test.</strong> '
           'It was requested after the original locked choices failed the later period. All the same development configurations '
           'were then ranked on those later outcomes. The original failures above remain unchanged. '
           'A later-period winner has been selected on its evaluation data and is not a newly validated recommendation.</div>',
           f'<p class="receipt">Supplemental verification: <strong>{esc(status)}</strong> · {esc(text)}. '
           'Arithmetic verification does not remove retrospective selection bias.</p>',
           f'<p>{len(configs):,} previously enumerated configurations were replayed on the same '
           f'{len(expected_starts(plan["evaluation"], plan["horizon_days"]))} Monday starts in '
           f'{esc(" → ".join(plan["evaluation"]))} (end exclusive), with no added combinations, thresholds, risk levels or guards. '
           'The “primary” label below means the same ranking rule applied retrospectively—not the original locked primary choice. '
           'Fastest-observed means the quickest lucky path, not a typical completion time. All fractions remain dependent historical observations.</p>']
    rows = []
    for c in selected:
        for cost in ("recorded", "stress"):
            r = lookup[c["id"], cost]
            s = r["summary"]
            fast = s["fastest"]
            rows.append([esc(c["kind"] + " · " + c["role"]), label(c["keys"], labels),
                         "Base" if cost == "recorded" else "Same-period stress",
                         "≥50% base-scoreboard hits" if configs[c["id"]]["summary"]["hit_pct"] >= 50 else "NONE QUALIFIED — retrospective fallback",
                         *summary_cells(r), money(s["ending_cash_p10"]) + " / " + money(s["ending_cash_p90"]),
                         (number(fast["days"]) + " days<br>" + utc(fast["start"]) + " →<br>" + utc(fast["hit_epoch"])) if fast else "No hit"])
    out += [table(["Retrospective role", "EA configuration", "Costs", "Base-scoreboard qualification", *SUMMARY_HEADERS,
                   "Ending cash P10 / P90", "Fastest hit (retrospective)"], rows),
            '<h3>Top 10 retrospective single configurations</h3>',
            development_table(sorted((c for c in configs.values() if len(c["keys"]) == 1), key=ranking)[:10], labels),
            '<h3>Top 10 retrospective basket configurations</h3>',
            development_table(sorted((c for c in configs.values() if len(c["keys"]) > 1), key=ranking)[:10], labels),
            '<details><summary>All later-period retrospective configurations</summary>',
            development_table(configs.values(), labels), '</details>',
            '<details><summary>Every retrospective candidate attempt and illustrative path</summary>',
            '<p>Each unique selected configuration is listed once per cost regime. Stress uses the same period and selected rules; '
            'it is a sensitivity, not independent validation. Representative paths are chosen after their outcomes are known.</p>']
    for r in recent["sensitivity"]:
        roles = ", ".join(c["kind"] + " " + c["role"] for c in selected if c["id"] == r["id"])
        out += [f'<h3>{esc(roles)} · {label(r["keys"], labels)} · {pct(r["risk_pct"])} · {esc(r["cost"])}</h3>',
                attempts_table(r["attempts"])]
        out += [detail_html(r, detail, labels) for detail in r["details"]]
    out += ['</details><p><strong>No new forward evidence exists for a winner chosen from this scoreboard.</strong> '
            'Genuinely new observations and executable account testing would be needed before any reliability claim. '
            'No live deployment or new parameter selection is implied.</p>']
    if (root / "RISK-SENSITIVITY.json").exists():
        out.append(risk_html(root, plan, recent, read(root, "RISK-SENSITIVITY.json"), labels))
    return "\n".join(out)


def risk_html(root, plan, recent, risk, labels):
    validate_risk(root, plan, recent, risk)
    status, text = risk_receipt(root)
    out = ['<h3>Risk ladder for the two retrospectively selected families</h3>',
           '<p><strong>Same-period sensitivity — NOT new validation or an optimized live risk recommendation.</strong> '
           'All six originally declared risk levels are shown, so the fastest 20%/30% selections can be compared with lower-risk paths. '
           'EA families were selected using these same dates. Re-ranking this table would add another selection step; '
           'it would not establish a future success probability.</p>',
           f'<p class="receipt">Risk-ladder verification: <strong>{esc(status)}</strong> · {esc(text)}</p>']
    for family in (c for c in recent["selected"] if c["role"] == "primary"):
        out.append('<h4>' + esc(family["kind"]) + ' · ' + label(family["keys"], labels) + '</h4>')
        rr = [r for r in risk["results"] if r["kind"] == family["kind"]]
        out.append(table(["Costs", *SUMMARY_HEADERS, "Zero-trade starts", "Minimum-lot skips", "Margin skips"],
                         (["Base" if r["cost"] == "recorded" else "Stress", *summary_cells(r), pct(r["summary"]["no_trade_pct"]),
                           number(r["summary"]["total_counts"].get("minimum_lot", 0), 0),
                           number(r["summary"]["total_counts"].get("margin_proxy", 0), 0)]
                          for r in sorted(rr, key=lambda x: (x["risk_pct"], x["cost"])))))
    out.append('<p class="small">At very low requested risk, the broker minimum lot can prevent all entries. '
               'Zero closed DD in a zero-trade start is not evidence of a profitable low-risk strategy. '
               'All-start medians, closed-DD limitations and the $20 research floor retain the definitions above.</p>')
    return "\n".join(out)


def render(root=ROOT):
    plan, source, development, selection, results, audit, broker = [read(root, n) for n in (
        "PLAN.json", "INPUTS.json", "DEVELOPMENT.json", "SELECTION.json", "RESULTS.json", "SOURCE AUDIT.json", "BROKER.json")]
    validate(root, plan, source, development, selection, results)
    status, status_text = receipt(root)
    labels = source["metadata"]["labels"]
    labels = {**labels, "nasdaq-5m-candle-momentum": labels.get("nasdaq-5m-candle-momentum", "Nasdaq 5M") + " — current DI ON"}
    lookup = {(r["id"], r["cost"]): r for r in results["results"]}
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>$100 to $10,000 — historical challenge screen</title><style>',
        'body{margin:0;background:#071410;color:#dceee5;font:15px/1.6 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:32px 24px 80px}'
        'h1{font-size:clamp(28px,4vw,44px);line-height:1.15}h2{margin-top:42px;border-top:1px solid #29483b;padding-top:25px}h3{margin-top:28px}'
        'p{max-width:1100px}a{color:#7cefc8}.eyebrow{color:#80f7c6;text-transform:uppercase;letter-spacing:.15em;font-size:12px}'
        '.warning{border:1px solid #8d7330;background:#292510;padding:18px;border-radius:12px}.receipt{padding:10px 16px;border:1px solid #56866c;border-radius:8px}'
        '.scroll{overflow-x:auto;border:1px solid #29483b;border-radius:10px;margin:15px 0}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}'
        'th,td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #213b30}th{background:#10291f;font-size:12px;color:#a4c8b6;white-space:nowrap}'
        'td{font-size:13px}tr:last-child td{border-bottom:0}tbody tr:hover{background:#0d241a}.small,small{color:#a3bcaf;font-size:12px}'
        'details{border:1px solid #29483b;border-radius:10px;padding:14px 16px;margin:14px 0}summary{cursor:pointer;color:#83f1c5;font-weight:600}'
        'li{margin:7px 0}.pill{display:inline-block;border:1px solid #75804e;border-radius:30px;padding:3px 11px;color:#e7d794;font-size:12px}'
        'code{word-break:break-all;font-size:11px}nav{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}.path h4{margin-bottom:0}'
        '@media print{details{display:block}summary{display:block}.scroll{overflow:visible}body{background:white;color:black}th{color:black;background:#eee}}',
        '</style></head><body><main><p class="eyebrow">Calyx · research only · no live changes</p>',
        '<h1>Can one EA or a basket turn $100 into $10,000?</h1>',
        '<p>This finite historical screen searches existing stop-based EAs with real broker lot increments and conservative margin admission. '
        'It does not find a universally “best possible” strategy or establish a reliable way to multiply money 100×.</p>',
        '<div class="warning"><strong>High-risk research, not a live recommendation.</strong> '
        'Requested risk reaches 30% per trade. Real loss can exceed the simulated research floor or the original deposit. '
        'All hit fractions below are dependent historical starts—not future probabilities. Closed-cash replay does not measure floating drawdown or broker stopout.</div>',
        f'<p class="receipt">Verification: <strong>{esc(status)}</strong> · {esc(status_text)}</p>',
        '<nav><a href="#locked">Locked choices</a><a href="#evaluation">Evaluation</a><a href="#recent">Retrospective scoreboard</a><a href="#development">Development search</a>'
        '<a href="#attempts">Every evaluation start</a><a href="#paths">Detailed paths</a><a href="#method">Rules & limitations</a></nav>',
        table(["Development / selection", "Later evaluation", "Initial → target", "Attempt schedule", "Universe"], [[
            esc(" → ".join(plan["development"])) + " (end exclusive)",
            esc(" → ".join(plan["evaluation"])) + " (end exclusive)", "$100 → $10,000",
            f'Mondays · {plan["horizon_days"]} days each · {len(development["starts"])} development / {len(expected_starts(plan["evaluation"], plan["horizon_days"]))} evaluation starts',
            f'{audit["eligible_current_eas"]} current EAs + {audit["alternatives"]} DI-OFF alternative · {len(source["metadata"]["excluded"])} excluded']]),
        '<p class="small">Windows are UTC. Every start has a full follow-up within its partition. Starts overlap heavily; they are not independent trials. '
        'These dates and strategies were already researched before this screen: the later split is not genuinely untouched out-of-sample data.</p>',
        '<h2 id="locked">Locked development selections</h2>',
        '<p>Configurations and risk were selected using development only, then written to SELECTION.json before evaluation. '
        'Primary selects the fastest conditional median among configurations with at least 50% development hits. '
        'If none qualifies, the saved highest-hit fallback is explicitly marked. Highest-hit and fastest-observed roles are separate diagnostics; '
        'the fastest-observed “lottery” path is not the recommended configuration.</p>']
    locked_rows = []
    for c in selection["locked"]:
        locked_rows.append([esc(c["kind"]), esc(c["role"]), label(c["keys"], labels),
                            "≥50% development hits" if c["qualified"] else '<strong>NONE QUALIFIED — fallback</strong>', *summary_cells(dict(c, summary=c["development"]))])
    out.append(table(["Scope", "Locked role", "EA configuration", "Development qualification", *SUMMARY_HEADERS], locked_rows))
    out += ['<h2 id="evaluation">Later evaluation — no reselection</h2>',
            '<p>Base costs retain original observed fills, spread, entry/exit fees and swaps. Stress adds one available snapshot spread each side, '
            'doubles negative recorded swap and doubles margin admission estimates. It is a sensitivity, not measured future execution.</p>']
    primaries = [c for c in selection["locked"] if c["role"] == "primary"]
    if all(lookup[c["id"], "recorded"]["summary"]["hits"] == 0 for c in primaries):
        out.append('<div class="warning"><strong>Both locked primary choices had zero later-evaluation target hits.</strong> '
                   'A fast development result did not translate into a completed $100-to-$10,000 attempt for either primary choice. '
                   'Do not substitute the later best-looking diagnostic as a newly validated winner.</div>')
    eval_rows = []
    for c in selection["locked"]:
        for cost in ("recorded", "stress"):
            r = lookup[c["id"], cost]
            s = r["summary"]
            fast = s["fastest"]
            eval_rows.append([esc(c["kind"] + " · " + c["role"]), "Base" if cost == "recorded" else "Stress", label(r["keys"], labels),
                             *summary_cells(r), money(s["ending_cash_p10"]) + " / " + money(s["ending_cash_p90"]),
                             (number(fast["days"]) + " days<br>" + utc(fast["start"]) + " →<br>" + utc(fast["hit_epoch"])) if fast else "No hit"])
    out.append(table(["Locked role", "Costs", "EA configuration", *SUMMARY_HEADERS, "Ending cash P10 / P90", "Fastest evaluated hit (retrospective)"], eval_rows))
    out += ['<p class="small">¹ “Median days among hits” omits failures and timeouts and can look fast when almost every attempt fails. '
            'The all-start median is shown only when its central completion order position(s) hit within the horizon; '
            'otherwise it is unavailable within 365 days. For an even start count it averages both central completion times, '
            'not the fastest half or the mean of only winners. '
            'Floor means the $20 closed-cash latch (80% loss of the initial deposit), not reconstructed broker liquidation or proven maximum loss.</p>']
    if (root / "RECENT.json").exists():
        out.append(recent_html(root, plan, development, read(root, "RECENT.json"), labels))
    else:
        out.append('<h2 id="recent">Supplemental retrospective scoreboard</h2><p>No saved supplemental scoreboard is included in this report.</p>')
    out += ['<h2 id="development">Development search — selection evidence, not validation</h2>',
            f'<p>{development["configuration_count"]:,} configurations: {len(development["singles"]):,} single-EA / risk variants and '
            f'{len(development["combos"]):,} basket / risk variants. Requested risks: {esc(", ".join(str(x) + "%" for x in plan["risk_percentages"]))}. '
            'Trying many variants makes the best historical outcome look better by selection alone. No claim that the screen beats luck-adjusted search.</p>',
            '<h3>Top 10 single configurations</h3>', development_table(sorted(development["singles"], key=ranking)[:10], labels),
            '<h3>Top 10 basket configurations</h3>', development_table(sorted(development["combos"], key=ranking)[:10], labels),
            '<details><summary>Every tested single-EA / risk configuration</summary>', development_table(development["singles"], labels), '</details>',
            '<details><summary>Every tested basket / risk configuration</summary>', development_table(development["combos"], labels), '</details>',
            '<p class="small">Candidate/opened/skip totals count repeated opportunities across overlapping starts, not unique native trades. '
            'Each EA family contributes its best development variant to an eight-family shortlist; all pairs/triples and eligible named baskets are tested. '
            'Nasdaq DI ON and DI OFF cannot coexist in a basket. Basket names contribute eligible members only, not the original guard/risk scheme.</p>',
            '<h2 id="attempts">Every later-evaluation attempt — exact dates</h2>',
            '<p>Duplicate role configurations are listed once per cost regime. A target hit requires closed cash at or above $10,000 with no owned positions. '
            'While waiting flat, new entries pause; if cash drops below target before flat, admissions can resume. '
            'Timeout endpoints may still own positions and do not represent liquidated account value.</p>']
    for r in results["results"]:
        roles = ", ".join(c["kind"] + " " + c["role"] for c in selection["locked"] if c["id"] == r["id"])
        out += [f'<details><summary>{esc(roles)} · {esc(r["cost"])} · {pct(r["risk_pct"])} risk</summary>',
                '<p>' + label(r["keys"], labels) + '</p>', attempts_table(r["attempts"]), '</details>']
    out += ['<h2 id="paths">Saved illustrative paths — full position and cash breakdown</h2>']
    for r in results["results"]:
        out += [f'<h3>{label(r["keys"], labels)} · {pct(r["risk_pct"])} · {esc(r["cost"])}</h3>']
        out += [detail_html(r, d, labels) for d in r["details"]]
    out += ['<h2 id="method">Rules and broker geometry</h2>', '<ul>']
    for name in ("sizing", "cash", "success", "failure", "exposure", "daily_pause", "margin", "stress"):
        out.append('<li><strong>' + esc(name.replace('_', ' ').capitalize()) + ':</strong> ' + esc(plan[name]) + '</li>')
    out += ['</ul>', f'<p>Broker reference: {esc(broker["account"]["company"])} · {esc(broker["account"]["server"])} · '
            f'{esc(broker["account"]["currency"])} · snapshot leverage 1:{broker["account"]["leverage"]}. '
            'The leverage number is not applied uniformly across instruments; measured/cached contract margin proxies govern admission.</p>',
            table(["Symbol", "Contract size", "Minimum lots", "Lot step", "Maximum lots", "Stress spread cash / 1 lot / side", "Margin method", "Spread provenance"],
                  ([esc(key), number(v["trade_contract_size"], 0), number(v["volume_min"], 2), number(v["volume_step"], 2), number(v["volume_max"], 0),
                    money(v["spread_cash_per_lot"]), esc(v["margin_model"]), esc(v["spread_source"])] for key, v in sorted(source["symbols"].items()))),
            '<h3>Coverage, exclusions and native diagnostics</h3>',
            f'<p>{audit["counts"]["positions"]:,} source positions; {audit["counts"]["partial_positions"]:,} have genuine partial exits; '
            f'{audit["counts"]["end_censored_positions"]} source-end censored entries retained without artificial final-liquidation cash. '
            f'{audit["source_file_count"]:,} source files are recorded in preparation provenance.</p>',
            table(["Excluded EA", "Reason"], ([esc(k), esc(v)] for k, v in source["metadata"]["excluded"].items())),
            table(["Source EA", "Native diagnostic flags", "Treatment"],
                  ([esc(labels.get(w["key"], w["key"])), esc(json.dumps(w["native_flags"], sort_keys=True)), esc(w["note"])] for w in audit["source_warnings"])),
            '<p>Diagnostic counts are log flags/hits, not proven unique rejected orders. No rejected attempt is converted into a fill. '
            'The Nasdaq overnight source has no entries before June 2023; earlier zero rows mean shorter observed coverage, not a demonstrated absence of signals.</p>',
            '<details><summary>Every eligible EA — actual source-entry coverage</summary>',
            '<p>Counts below are unique source positions, not overlapping challenge appearances. First/last entries describe observed ledger coverage, '
            'not guaranteed availability of all earlier signals. Development skip counts above use only their own partition.</p>']
    grouped = {}
    for row in source.get("rows", []):
        grouped.setdefault(row["key"], []).append(row)
    out += [table(["EA", "Symbol", "Positions", "First observed entry UTC", "Last observed entry UTC", "With partial exits", "End-censored"],
                  ([esc(labels.get(k, k)), esc(", ".join(sorted({r["symbol"] for r in rr}))), str(len(rr)),
                    utc(min(r["op"] for r in rr)), utc(max(r["op"] for r in rr)),
                    str(sum(bool(r["partial"]) for r in rr)), str(sum(bool(r["end_censored"]) for r in rr))]
                   for k, rr in sorted(grouped.items()))), '</details>',
            '<h3>What this screen cannot establish</h3><ul>']
    for warning in dict.fromkeys(plan["limitations"] + audit["limitations"]):
        out.append('<li>' + esc(warning) + '</li>')
    out += ['</ul><h3>Saved evidence</h3><p>These files contain research evidence, not deployable presets.</p><ul>']
    for name in ("PLAN.json", "SOURCE AUDIT.json", "FROZEN.json", "SELECTION.json", "DEVELOPMENT.json", "RESULTS.json", "VERIFICATION.json",
                 "RECENT-PLAN.json", "RECENT-FROZEN.json", "RECENT.json", "RECENT-VERIFICATION.json"):
        if (root / name).exists():
            out.append(f'<li><a href="{esc(name.replace(" ", "%20"))}">{esc(name)}</a> · <code>{sha(root / name)}</code></li>')
    for name in ("RISK-SENSITIVITY-PLAN.json", "RISK-SENSITIVITY.json", "RISK-VERIFICATION.json"):
        if (root / name).exists():
            out.append(f'<li><a href="{esc(name)}">{esc(name)}</a> · <code>{sha(root / name)}</code></li>')
    out += ['</ul><p class="small">Static saved report. No server, tracking, external libraries, trade controls or client-side simulation. '
            'No production EA, preset, BAT, website or account changed.</p></main></body></html>']
    output = "\n".join(out)
    (root / "Results.html").write_text(output, encoding="utf-8")
    return output


if __name__ == "__main__":
    output = render()
    print(json.dumps({"report": str(ROOT / "Results.html"), "bytes": len(output.encode("utf-8")),
                      "verification": receipt(ROOT)[0],
                      "retrospective_verification": recent_receipt(ROOT)[0] if (ROOT / "RECENT.json").exists() else "NOT INCLUDED",
                      "risk_verification": risk_receipt(ROOT)[0] if (ROOT / "RISK-SENSITIVITY.json").exists() else "NOT INCLUDED"}))
