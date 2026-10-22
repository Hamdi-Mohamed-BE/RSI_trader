"""MT5 drawdown parser audit (2026-10-22): "Maximal" vs "Relative" drawdown in every native report. Read-only.

MT5 prints two drawdown percentages:
- "Drawdown Maximal"  = "$amount (x%)": x% is the percentage AT the largest dollar drawdown.
- "Drawdown Relative" = "y% ($amount)": y% is the worst percentage drawdown.
On a run that compounded, x% < y%. The EA store parser (_native_metrics) stores x% as max_drawdown_pct.

Scans every *.htm / *.htm.gz under a native* folder of the portfolio package plus the EA store evidence caches,
lists runs where relative - maximal > 0.5 pp (equity or balance) and flags where they are cited:
study *.md files, CLAUDE.md, and the website (cached payloads the site serves, study folders the app reads).

Run from AAA EAs/EA store:  uv run python "../BM Trading Robust Sets 2026-08-04/_Ops Monitor/drawdown_audit.py"
Output: _Ops Monitor/output/drawdown-audit/ (scan.json.gz, flagged.json, tables.md)
"""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from common import AAA, HERE, PACKAGE, STORE

ROOT = AAA.parent
OUT = HERE / 'output' / 'drawdown-audit'
THRESH = 0.5
TAG = re.compile(r'<[^>]+>')
HEAD = 600_000  # bytes of the (decompressed) report holding the summary block


# ---------- report parsing ----------
def _bytes(p, limit=None):
    opener = gzip.open if p.name.lower().endswith('.gz') else open
    with opener(p, 'rb') as f:
        return f.read(limit) if limit else f.read()


def _decode(b):
    if b[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return b[:len(b) - len(b) % 2].decode('utf-16', 'ignore')
    if len(b) > 4 and b[1:2] == b'\x00' and b[3:4] == b'\x00':
        return b[:len(b) - len(b) % 2].decode('utf-16-le', 'ignore')
    return b.decode('utf-8', 'ignore')


def _metric(t, label):
    m = re.search(rf'>\s*{re.escape(label)}:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>', t, flags=re.I | re.S)
    return html.unescape(TAG.sub('', m.group(1))).replace('\xa0', ' ').strip() if m else ''


def _num(v):
    m = re.search(r'[-+]?\d[\d ]*(?:\.\d+)?', v.replace('%', ''))
    return float(m.group(0).replace(' ', '')) if m else None


def _maximal(v):  # "93 099.19 (35.08%)"
    m = re.match(r'\s*([-+]?\d[\d ]*(?:\.\d+)?)\s*\(([-+]?\d+(?:\.\d+)?)%\)', v)
    return (float(m.group(1).replace(' ', '')), float(m.group(2))) if m else (None, None)


def _relative(v):  # "46.90% (48 776.45)"
    m = re.match(r'\s*([-+]?\d+(?:\.\d+)?)%\s*\(([-+]?\d[\d ]*(?:\.\d+)?)\)', v)
    return (float(m.group(1)), float(m.group(2).replace(' ', ''))) if m else (None, None)


def _weekdays(a, b):
    return sum((a + timedelta(days=i)).weekday() < 5 for i in range((b - a).days))


def parse(p):
    t = _decode(_bytes(p, HEAD))
    if 'Equity Drawdown Relative' not in t:
        t = _decode(_bytes(p))
        if 'Equity Drawdown Relative' not in t:
            return None
    r = {'expert': _metric(t, 'Expert'), 'symbol': _metric(t, 'Symbol')}
    m = re.match(r'(\w+)\s*\((\d{4})\.(\d{2})\.(\d{2})\s*-\s*(\d{4})\.(\d{2})\.(\d{2})\)', _metric(t, 'Period'))
    if m:
        a, b = date(int(m[2]), int(m[3]), int(m[4])), date(int(m[5]), int(m[6]), int(m[7]))
        r.update(tf=m[1], **{'from': a.isoformat()}, to=b.isoformat(), days=(b - a).days, weekdays=_weekdays(a, b))
    else:
        r.update(tf=None, **{'from': None}, to=None, days=None, weekdays=None)
    r.update(initial=_num(_metric(t, 'Initial Deposit')), net=_num(_metric(t, 'Total Net Profit')),
             pf=_num(_metric(t, 'Profit Factor')), trades=int(_num(_metric(t, 'Total Trades')) or 0),
             history_quality=_metric(t, 'History Quality'))
    r['eq_max_cash'], r['eq_max_pct'] = _maximal(_metric(t, 'Equity Drawdown Maximal'))
    r['eq_rel_pct'], r['eq_rel_cash'] = _relative(_metric(t, 'Equity Drawdown Relative'))
    r['bal_max_cash'], r['bal_max_pct'] = _maximal(_metric(t, 'Balance Drawdown Maximal'))
    r['bal_rel_pct'], r['bal_rel_cash'] = _relative(_metric(t, 'Balance Drawdown Relative'))
    r['return_pct'] = round(r['net'] / r['initial'] * 100, 2) if r['initial'] and r['net'] is not None else None
    r['trades_per_month'] = round(r['trades'] / (r['days'] / 30.4375), 2) if r['days'] else None
    r['trades_per_weekday'] = round(r['trades'] / r['weekdays'], 3) if r['weekdays'] else None
    for a, b, k in (('eq_rel_pct', 'eq_max_pct', 'eq_gap'), ('bal_rel_pct', 'bal_max_pct', 'bal_gap')):
        r[k] = round(r[a] - r[b], 2) if r[a] is not None and r[b] is not None else None
    return r


def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _harness(p):
    """max_drawdown_pct a study harness stored next to the report (run.json 'metrics'), if any."""
    for cand in (p.parent / 'run.json', p.with_name(p.name.split('.htm')[0] + '.json')):
        if cand.is_file():
            try:
                mt = json.loads(cand.read_text(encoding='utf-8')).get('metrics')
            except (ValueError, AttributeError):
                continue
            if isinstance(mt, dict):
                return {k: mt[k] for k in ('max_drawdown_pct', 'balance_dd_pct', 'equity_dd_rel_pct', 'balance_dd_rel_pct') if k in mt}
    return None


def reports():
    for p in sorted(PACKAGE.rglob('*')):
        n = p.name.lower()
        if p.is_file() and (n.endswith('.htm') or n.endswith('.htm.gz')) and \
                any(x.lower().startswith('native') for x in p.relative_to(PACKAGE).parts[:-1]):
            yield 'study', p
    for sub in ('evidence-cache', 'evidence-jobs'):
        for p in sorted((STORE / 'data' / sub).rglob('*')):
            n = p.name.lower()
            if p.is_file() and (n.endswith('.htm') or n.endswith('.htm.gz')):
                yield 'store-' + sub, p


def scan():
    rows, skipped = [], []
    for kind, p in reports():
        r = parse(p)
        if r is None:
            skipped.append(str(p.relative_to(ROOT)).replace('\\', '/'))
            continue
        r.update(kind=kind, path=str(p.relative_to(ROOT)).replace('\\', '/'), sha256=_sha(p))
        if kind == 'study':
            parts = p.relative_to(PACKAGE).parts
            r.update(study=parts[0], run='/'.join(parts[1:]), harness=_harness(p))
        else:
            parts = p.relative_to(STORE / 'data').parts
            r.update(study='/'.join(parts[:2]), run='/'.join(parts[2:]), harness=None)
        rows.append(r)
    return rows, skipped


# ---------- citations ----------
def _num_re(v, dp):
    s = f'{abs(v):.{dp}f}'.replace('.', r'\.')
    return re.compile(rf'(?<![\d.]){s}(?!\d)' + ('%' if dp == 1 else ''))


def _corroborators(r):
    out = []
    if r['trades'] >= 10:
        t = r['trades']
        out.append(re.compile(rf'(?<![\d.,$-]){t}(?![\d.%])|(?<![\d.$-]){t:,}(?![\d.%])'))
    if r['return_pct'] is not None and abs(r['return_pct']) >= 1:
        out += [_num_re(r['return_pct'], 2), _num_re(r['return_pct'], 1)]
    if r['pf']:
        out.append(re.compile(rf'PF\s*{r["pf"]:.2f}'.replace('.', r'\.', 1)))
    return out


def _search(lines, r, key, window):
    """Lines quoting r[key] (2 dp, or 1 dp with %); 'strong' when trades, return or PF of the same run sit within `window` lines."""
    pats, cor, hits = [_num_re(r[key], 2), _num_re(r[key], 1)], _corroborators(r), []
    for i, line in enumerate(lines):
        if any(p.search(line) for p in pats):
            ctx = ' '.join(lines[max(0, i - window): i + window + 1])
            hits.append({'line': i + 1, 'strong': any(c.search(ctx) for c in cor), 'text': line.strip()[:220]})
    return hits


METRICS = (('eq_max_pct', 'equity maximal', 'eq_gap'), ('eq_rel_pct', 'equity relative', 'eq_gap'),
           ('bal_max_pct', 'balance maximal', 'bal_gap'), ('bal_rel_pct', 'balance relative', 'bal_gap'))


def _study_docs(study, cache={}):  # noqa: B006 - per-run memo
    if study not in cache:
        base, docs = PACKAGE / study, {}
        for p in base.rglob('*.md') if base.is_dir() else ():
            if not any(x.lower().startswith('native') for x in p.relative_to(base).parts[:-1]):
                docs[str(p.relative_to(PACKAGE)).replace('\\', '/')] = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        cache[study] = docs
    return cache[study]


def _payload(r):
    """The cached payload the website serves for an EA store report, and which drawdown it shows."""
    parts = r['run'].split('/')
    if r['kind'] == 'store-evidence-cache' and parts[0] == 'source-runs' and len(parts) == 4:
        p = STORE / 'data' / 'evidence-cache' / 'v1' / 'products' / parts[1] / parts[2] / f"{parts[3].split('.')[0]}.json"
    elif r['kind'] == 'store-evidence-jobs':
        p = STORE / 'data' / 'evidence-jobs' / r['study'].split('/')[1] / 'latest.json'
    else:
        return None
    rel = str(p.relative_to(ROOT)).replace('\\', '/')
    if not p.is_file():
        return {'payload': rel, 'missing': True}
    s = json.loads(p.read_text(encoding='utf-8')).get('stats') or {}
    shown = s.get('max_drawdown_pct')
    basis = None if shown is None else 'equity maximal' if abs(shown - r['eq_max_pct']) < 0.011 and abs(shown - r['eq_rel_pct']) >= 0.011 \
        else 'equity relative' if abs(shown - r['eq_rel_pct']) < 0.011 else 'other (not this report; payload built elsewhere)'
    return {'payload': rel, 'shown_max_drawdown_pct': shown, 'basis': basis, 'payload_trades': s.get('trades')}


def cite(rows):
    flagged = [r for r in rows if (r['eq_gap'] or 0) > THRESH or (r['bal_gap'] or 0) > THRESH]
    claude = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8', errors='ignore').splitlines()
    app_text = '\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in (STORE / 'app').rglob('*.py'))
    app_studies = {r['study'] for r in rows if r['kind'] == 'study' and r['study'] in app_text}
    store_by_sha = defaultdict(list)
    for r in rows:
        if r['kind'].startswith('store'):
            store_by_sha[r['sha256']].append(r['path'])
    try:  # which cached mode the site shows by default (needs the EA store app)
        from app.catalog import get_product, get_sellable_catalog
        from app.main import _recommended_mode
        sellable = {p.slug for p in get_sellable_catalog()}
    except Exception:  # noqa: BLE001 - audit still useful without the app
        get_product = _recommended_mode = None; sellable = set()
    for r in flagged:
        c = {'docs': [], 'claude_md': [], 'website': []}
        live = [(k, label) for k, label, gap in METRICS if (r[gap] or 0) > THRESH]
        if r['kind'] == 'study':
            for name, lines in _study_docs(r['study']).items():
                for k, label in live:
                    c['docs'] += [{'file': name, 'metric': label, **h} for h in _search(lines, r, k, 0)]
            if r['study'] in app_studies:
                c['website'].append({'source': 'study folder read by EA store app code'})
            c['website'] += [{'source': 'identical report in EA store cache', 'store_path': sp} for sp in store_by_sha.get(r['sha256'], [])]
        else:
            pp = _payload(r)
            if pp:
                if get_product and r['kind'] == 'store-evidence-cache':
                    slug, mode = r['run'].split('/')[1:3]; product = get_product(slug)
                    rec = _recommended_mode(product) if product else None
                    pp.update(recommended_mode=rec, displayed_mode=rec == mode, sellable=slug in sellable)
                c['website'].append({'source': 'EA store cached payload', **pp})
        for k, label in live:
            c['claude_md'] += [{'metric': label, **h} for h in _search(claude, r, k, 1) if h['strong']]
        r['cites'] = c
        r['invalid_run'] = any(x in r['path'].upper() for x in ('INVALID', 'FAILED', 'INFRASTRUCTURE', 'SMOKE'))
    return flagged, sorted(app_studies)


# ---------- tables ----------
def _f(v, dp=2, sign=False):
    return '—' if v is None else f'{v:+.{dp}f}' if sign else f'{v:.{dp}f}'


def _run_label(r):
    return r['run'].replace('native/', '', 1).replace('|', '/')


def tables(flagged):
    head = ('| Study | Run | Symbol TF | Window | Trades | Trades/mo | Trades/weekday | Return % | PF | Eq DD max % | Eq DD rel % | Eq gap pp '
            '| Bal DD max % | Bal DD rel % | Bal gap pp | Harness stored | Cited |\n|' + '---|' * 17)
    out = [head]
    for r in sorted(flagged, key=lambda r: (r['study'], -(max(r['eq_gap'] or 0, r['bal_gap'] or 0)))):
        h = r['harness'] or {}
        hs = '—' if 'max_drawdown_pct' not in h else 'maximal' if abs(h['max_drawdown_pct'] - r['eq_max_pct']) < 0.011 and r['eq_gap'] > 0.01 \
            else 'relative' if abs(h['max_drawdown_pct'] - r['eq_rel_pct']) < 0.011 else 'other'
        c = r['cites']; flags = []
        if any(x['strong'] and 'maximal' in x['metric'] for x in c['docs']): flags.append('doc:max')
        if any(x['strong'] and 'relative' in x['metric'] for x in c['docs']): flags.append('doc:rel')
        if c['claude_md']: flags.append('CLAUDE.md')
        if c['website']: flags.append('web')
        if r['invalid_run']: flags.append('invalid-run')
        out.append(f"| {r['study']} | {_run_label(r)} | {r['symbol']} {r['tf']} | {r['from']} → {r['to']} | {r['trades']} | {_f(r['trades_per_month'])} "
                   f"| {_f(r['trades_per_weekday'], 3)} | {_f(r['return_pct'], 2, True)} | {_f(r['pf'])} | {_f(r['eq_max_pct'])} | {_f(r['eq_rel_pct'])} "
                   f"| {_f(r['eq_gap'])} | {_f(r['bal_max_pct'])} | {_f(r['bal_rel_pct'])} | {_f(r['bal_gap'])} | {hs} | {', '.join(flags) or '—'} |")
    return '\n'.join(out) + '\n'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, skipped = scan()
    flagged, app_studies = cite(rows)
    meta = {'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'threshold_pp': THRESH,
            'reports_parsed': len(rows), 'unique_reports': len({r['sha256'] for r in rows}), 'skipped_no_drawdown_block': skipped,
            'flagged_rows': len(flagged), 'flagged_unique_reports': len({r['sha256'] for r in flagged}),
            'flagged_equity': sum((r['eq_gap'] or 0) > THRESH for r in flagged), 'flagged_balance': sum((r['bal_gap'] or 0) > THRESH for r in flagged),
            'app_studies': app_studies}
    (OUT / 'scan.json.gz').write_bytes(gzip.compress(json.dumps(rows).encode('utf-8')))
    (OUT / 'flagged.json').write_text(json.dumps({**meta, 'flagged': flagged}, indent=1), encoding='utf-8')
    (OUT / 'tables.md').write_text(tables(flagged), encoding='utf-8')
    print(json.dumps({k: v for k, v in meta.items() if k not in ('skipped_no_drawdown_block', 'app_studies')}))


if __name__ == '__main__':
    main()
