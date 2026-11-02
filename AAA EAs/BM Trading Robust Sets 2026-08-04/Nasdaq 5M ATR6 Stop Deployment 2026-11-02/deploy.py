"""Owner request 2026-11-02: use the Nasdaq 5M ATR(14)x6 initial stop (A6_M1_DION of `Nasdaq 5M Wide Stop Pipeline 2026-11-02`) everywhere.
Inputs only: InpStopMode 2 -> 0 (N5_STOP_ATR) and InpInitialStopATR -> 6.0. Same EX5 / wrappers, same DI choice, ATR6 trail from +1R,
no TP, no session close. Offline file work only: never opens MT5, never touches a running chart.

  python deploy.py prepare   back up every touched file to before/, write the new canonical SET, patch every live Nasdaq SET copy,
                             update package/portfolio manifests (file hashes, recorded inputs, SET name) and the canonical installer.
Then: `uv run python -m tools.build_live_profiles launchers` (EA store) regenerates the five generator-owned portfolio folders.
"""
import hashlib, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent; B = ROOT.parent; R = B / '_00 Live profiles'; STORE = B.parent / 'EA store'
OLD_NAME = '11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
NEW_NAME = '11 Nasdaq 5M - DI ATR6 STOP ATR6 TRAIL NO TP - 1PCT.set'
OLD_CANON = B / 'Selected Portfolio Settings 2026-09-01' / OLD_NAME; NEW_CANON = OLD_CANON.with_name(NEW_NAME)
# every live / packaged copy of the Nasdaq preset (research snapshots, native runs, superseded builds and client packages are not touched)
SET_DIRS = ['FTMO Thirteen EA Deployment 2026-09-27/package', 'Current14 Plus ORB05 Portfolio 2026-10-08/Sets',
            '_00 Live profiles/Packages/FTMO/package', '_00 Live profiles/Packages/FTMO-AnyBroker/package', '_00 Live profiles/Packages/PropReady/package',
            '_00 Live profiles/Packages/FundedV1/package', '_00 Live profiles/Packages/Turbo5/package',
            '_00 Live profiles/Best Prop Portfolio 2026-10-20/package', '_00 Live profiles/Best Prop Portfolio 2026-10-20/Sets',
            '_00 Live profiles/Best Prop 15 Portfolio 2026-10-29/package', '_00 Live profiles/Best Prop 15 Portfolio 2026-10-29/Sets',
            '_00 Live profiles/funded_v1/Sets', '_00 Live profiles/Turbo 50k - Custom 5 Guarded/Sets',
            '_00 Live profiles/Turbo 50k Funded Portfolio 2026-10-26/Sets']
MANIFESTS = ['FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json', 'Current14 Plus ORB05 Portfolio 2026-10-08/Package.json',
             *[f'_00 Live profiles/Packages/{p}/PACKAGE.json' for p in ('FTMO', 'FTMO-AnyBroker', 'PropReady', 'FundedV1', 'Turbo5')],
             '_00 Live profiles/Best Prop Portfolio 2026-10-20/PACKAGE.json', '_00 Live profiles/Best Prop Portfolio 2026-10-20/PORTFOLIO.json',
             '_00 Live profiles/Best Prop 15 Portfolio 2026-10-29/PACKAGE.json', '_00 Live profiles/Best Prop 15 Portfolio 2026-10-29/PORTFOLIO.json',
             '_00 Live profiles/funded_v1/PORTFOLIO.json', '_00 Live profiles/Turbo 50k - Custom 5 Guarded/PORTFOLIO.json',
             '_00 Live profiles/Turbo 50k Funded Portfolio 2026-10-26/PORTFOLIO.json']
TEXT = ['_Auto Deploy/Install-BMTradingPortfolio.ps1']          # SET name only


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def backup(p):
    dest = ROOT / 'before' / p.relative_to(B.parent)
    if p.exists() and not dest.exists(): dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)


def decode(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')): return raw.decode('utf-16'), 'utf-16'
    return raw.decode('utf-8-sig'), ('utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8')


def is_nasdaq(v):
    g = lambda k: str(v.get(k, '')).strip()  # noqa: E731
    return (g('InpSignalHourNY') == '9' and g('InpSignalMinuteNY') == '30' and g('InpEMAPeriod') == '12' and g('InpStopMode') == '2'
            and g('InpInitialStopPercent') == '0.60' and g('InpUseATRTrailing') == 'true' and g('InpTrailingATR') == '6.0'
            and g('InpTrailStartR') == '1.0' and g('InpUseFixedTarget') == 'false' and g('InpCloseAtSessionEnd') == 'false')


def patch_set_text(text):
    v = dict(l.split('=', 1) for l in text.splitlines() if '=' in l)
    if not is_nasdaq(v): return None
    out, n1 = re.subn(r'(?m)^InpStopMode=2(\r?)$', r'InpStopMode=0\1', text)
    out, n2 = re.subn(r'(?m)^InpInitialStopATR=[0-9.]+(\r?)$', r'InpInitialStopATR=6.0\1', out)
    assert n1 == 1 and n2 == 1, (n1, n2)
    return out


def prepare():
    hashes, log = {}, []
    # 1. canonical SET = old canonical with exactly the two stop lines changed (byte-identical to the SET the website runs tested)
    backup(OLD_CANON); new = patch_set_text(OLD_CANON.read_bytes().decode('utf-8')); assert new
    NEW_CANON.write_bytes(new.encode('utf-8')); hashes[sha(OLD_CANON)] = sha(NEW_CANON)
    log.append(dict(file=str(NEW_CANON.relative_to(B)), from_file=OLD_NAME, old_sha=sha(OLD_CANON), new_sha=sha(NEW_CANON)))
    # 2. every live copy
    for d in SET_DIRS:
        for p in sorted((B / d).glob('*.set')):
            orig = ROOT / 'before' / p.relative_to(B.parent); src = orig if orig.exists() else p      # re-runnable: originals live in before/
            raw = src.read_bytes(); text, enc = decode(raw); out = patch_set_text(text)
            if out is None: continue
            backup(p); old = sha(src); p.write_bytes(out.encode(enc)); hashes.setdefault(old, sha(p)); assert hashes[old] == sha(p)
            log.append(dict(file=str(p.relative_to(B)), old_sha=old, new_sha=sha(p)))
    # 3. manifests: hashes of changed files, recorded Nasdaq inputs, canonical SET name (structured; exact JSON round-trip asserted first)
    for m in MANIFESTS:
        p = B / m
        if not p.exists(): log.append(dict(manifest=m, missing=True)); continue
        text = p.read_text(encoding='utf-8'); data = json.loads(text)
        fmt = next(dict(indent=i, ensure_ascii=a) for i in (2, 1) for a in (False, True) if json.dumps(data, indent=i, ensure_ascii=a) == text.rstrip('\n'))
        count = [0]

        def walk(x):
            if isinstance(x, dict):
                if is_nasdaq(x): x['InpStopMode'] = '0'; x['InpInitialStopATR'] = '6.0'; count[0] += 1
                return {k: walk(v) for k, v in x.items()}
            if isinstance(x, list): return [walk(v) for v in x]
            if isinstance(x, str):
                if x in hashes: count[0] += 1; return hashes[x]
                if OLD_NAME in x: count[0] += 1; return x.replace(OLD_NAME, NEW_NAME)
            return x
        new = walk(data)
        if count[0]:
            backup(p); p.write_text(json.dumps(new, **fmt) + ('\n' if text.endswith('\n') else ''), encoding='utf-8')
        log.append(dict(manifest=m, changes=count[0]))
    for t in TEXT:
        p = B / t; raw = p.read_bytes(); text, enc = decode(raw); n = text.count(OLD_NAME); assert n, t
        backup(p); p.write_bytes(text.replace(OLD_NAME, NEW_NAME).encode(enc)); log.append(dict(text=t, replacements=n))
    (ROOT / 'PREPARE.json').write_text(json.dumps(dict(hash_map=hashes, changes=log), indent=1), encoding='utf-8')
    for x in log: print(x)


def pins():
    """Second pass: files that pin the hash of a manifest changed above (Current14 provenance record, a website test, Checksums.json)."""
    changed = {}
    for b in (ROOT / 'before').rglob('*'):
        cur = B.parent / b.relative_to(ROOT / 'before')
        if b.is_file() and cur.exists() and sha(b) != sha(cur): changed[sha(b)] = sha(cur)
    for rel in ('Current14 Plus ORB05 Portfolio 2026-10-08/Package.json', '../EA store/tests/test_prop_ready_broker_neutral.py'):
        p = (B / rel).resolve(); text = p.read_text(encoding='utf-8'); new = text
        for o, n in changed.items(): new = new.replace(o, n)
        if new != text: backup(p); p.write_text(new, encoding='utf-8'); print('pinned', rel)
    c = B / 'Current14 Plus ORB05 Portfolio 2026-10-08/Checksums.json'; text = c.read_text(encoding='utf-8-sig'); data = json.loads(text)
    fmt = next(dict(indent=i, ensure_ascii=a) for i in (2, 1, 4) for a in (False, True) if json.dumps(data, indent=i, ensure_ascii=a) == text.rstrip('\n'))
    for k in data:
        actual = sha(c.parent / k)
        if actual.lower() != data[k].lower():
            assert any(data[k].lower() == o for o in changed) or data[k].lower() in changed.values(), k     # only files this deployment changed
            data[k] = actual.upper() if data[k].isupper() else actual; print('checksum', k)
    backup(c); c.write_text(json.dumps(data, **fmt) + ('\n' if text.endswith('\n') else ''), encoding='utf-8')


def publish():
    """Website product caches (dynamic = the selected Nasdaq mode) from the four native Model 4 runs of the deployed preset.
    Run from EA store with EA_STORE_DISABLE_MT5=1: uv run python "<this>/deploy.py" publish"""
    import gzip, os
    from datetime import date
    assert os.getenv('EA_STORE_DISABLE_MT5') == '1'
    sys.path[:0] = [str(STORE), str(STORE / 'tools')]
    import precompute_evidence_cache as P
    from app.mt5_evidence_jobs import _report_inputs, _same_setting
    product = next(p for p in P.get_sellable_catalog() if p.slug == 'nasdaq-5m-candle-momentum')
    assert Path(product.dynamic_set_source).name == NEW_NAME, product.dynamic_set_source
    ex5 = B / product.dynamic_expert_source; assert sha(ex5).startswith('fe9f391db5af')
    canon = dict(l.split('=', 1) for l in NEW_CANON.read_text().splitlines() if '=' in l)
    native = B / 'Nasdaq 5M Wide Stop Pipeline 2026-11-02' / 'native'; end = date(2026, 11, 1); checks = []
    for period, months in P.PERIOD_MONTHS.items():
        start = P.subtract_months(end, months); folder = native / f'nw-USTEC-DEPLOY-{period}'
        meta = json.loads((folder / 'run.json').read_text())
        raw = gzip.decompress(next(folder.glob('*.htm.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == meta['report_sha256'] and meta['ok']
        assert meta['start'] == start.strftime('%Y.%m.%d') and meta['end_exclusive'] == end.strftime('%Y.%m.%d'), (period, meta['start'])
        tested = dict(l.split('=', 1) for l in next(folder.glob('*.set')).read_text().splitlines() if '=' in l)
        assert tested == canon, period                                       # tested SET = deployed canonical SET, input for input
        report, metadata = P.source_paths(product, 'dynamic', period); report.parent.mkdir(parents=True, exist_ok=True)
        backup(report); backup(metadata); report.write_bytes(raw)
        actual = _report_inputs(report)
        assert all(k in actual and _same_setting(v, actual[k]) for k, v in canon.items() if k in actual) and len(set(canon) & set(actual)) >= 0.8 * len(canon)
        fingerprint = P.source_fingerprint(product, 'dynamic', start, end)
        fingerprint.update(source_report_sha256=meta['report_sha256'], original_expert_name=meta['expert'],
                           binary_identity='Exact copy of the deployed EX5 (fe9f391db5af), study Nasdaq 5M Wide Stop Pipeline 2026-11-02')
        P.write_json(metadata, fingerprint)
        payload, trades = P.product_payload(product, 'dynamic', period, start, end, report)
        assert payload['stats']['trades'] == len(trades) == meta['metrics']['trades']
        assert abs(payload['stats']['net_profit'] - meta['metrics']['net_profit']) < 0.011
        payload['notice'] = ('Owner-selected 2026-11-02: DI14 + EMA12 entry, ATR(14) x 6 initial stop, no TP, ATR6 trail from +1R, overnight/weekend '
                             'holding. Native Model 4, 150 ms delay, recorded commission/swap. Real ticks begin January 2026; earlier ticks are '
                             'generated. Chosen after a 124-version search over 2019-2026 that viewed these years: retrospective, not a clean holdout.')
        payload['source_fingerprint'] = fingerprint
        for p in (P.product_cache_path(product.slug, 'dynamic', period), P.product_trades_path(product.slug, 'dynamic', period)): backup(p)
        P.write_json(P.product_cache_path(product.slug, 'dynamic', period), payload)
        P.write_json(P.product_trades_path(product.slug, 'dynamic', period), trades)
        checks.append(dict(period=period, stats=payload['stats'], report_sha256=meta['report_sha256']))
        print('PUBLISHED', period, len(trades), payload['stats']['return_pct'], flush=True)
    (ROOT / 'WEBSITE_PUBLICATION.json').write_text(json.dumps(dict(checked=checks, live_deployment_verified=False), indent=2), encoding='utf-8')


if __name__ == '__main__':
    {'prepare': prepare, 'pins': pins, 'publish': publish}[sys.argv[1]]()
