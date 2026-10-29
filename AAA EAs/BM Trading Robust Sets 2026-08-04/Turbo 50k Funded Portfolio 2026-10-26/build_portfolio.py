"""Save the selected Turbo 50k portfolio as files in _00 Live profiles (no installer, nothing installed).
Each member = the exact EX5 + preset + input overrides used by the tested ledger (Portfolio Long History All ORB05 2026-10-14 PLAN.json),
with InpRiskPercent set to the recommended risk and the adaptive governor off (the simulation used fixed risk per trade).
python build_portfolio.py
"""
import hashlib, json, shutil
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
OUT = B / '_00 Live profiles' / 'Turbo 50k Funded Portfolio 2026-10-26'
PLAN = json.loads((B / 'Portfolio Long History All ORB05 2026-10-14/PLAN.json').read_text(encoding='utf-8'))
imp = json.loads((R / 'IMPROVE.json').read_text(encoding='utf-8')); sel = dict(members=imp['basket'])   # v2: improved 20-EA basket
PROFILE_RISK = '0.75'; G = imp['risks'][PROFILE_RISK]['guard']
rec = 0.3   # SET risk = $150 = the improved guard's maximum trade at full $3,000 room (5% taper)
cases = {c['case_id']: c for c in PLAN['cases']}; mapping = PLAN['mappings']['full-eas']
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731


def set_lines(preset, overrides, risk):
    lines = Path(preset).read_text(encoding='utf-8-sig').splitlines(); seen = set(); out = []
    ov = dict(overrides) if isinstance(overrides, list) else dict(overrides or {})
    for line in lines:
        if '=' in line and not line.startswith(';'):
            k = line.split('=', 1)[0]
            if k in ov: line = f'{k}={ov[k]}'; seen.add(k)
            if k in ('InpRiskPercent', 'InpMomentumRiskPercent', 'InpContrarianRiskPercent', 'InpAbsoluteRiskCapPercent'): line = f'{k}={risk:g}'; seen.add(k)
            if k == 'InpAdaptivePortfolioControls': line = 'InpAdaptivePortfolioControls=false'; seen.add(k)
        out.append(line)
    out += [f'{k}={v}' for k, v in ov.items() if k not in seen]
    return out


if OUT.exists(): raise SystemExit(f'{OUT} already exists; not overwriting')
(OUT / 'EAs').mkdir(parents=True); (OUT / 'Sets').mkdir()
members = []
for i, key in enumerate(sel['members'], 1):
    c = cases[mapping[key]]; ex = Path(c['expert']); pre = Path(c['preset'])
    exd = OUT / 'EAs' / ex.name
    if not exd.exists(): shutil.copy2(ex, exd)
    lines = set_lines(pre, c.get('input_settings') or {}, rec)
    has_risk = any(l.startswith(('InpRiskPercent=', 'InpMomentumRiskPercent=')) for l in lines)
    sname = f'{i:02d} {c["label"]}.set'; (OUT / 'Sets' / sname).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    members.append(dict(n=i, key=key, label=c['label'], symbol=c['symbol'], timeframe=c['period'], expert=f'EAs/{ex.name}', expert_sha256=sha(ex),
                        source_expert=str(ex.relative_to(B)), tested_preset=str(pre.relative_to(B)), tested_preset_sha256=sha(pre),
                        overrides_applied=c.get('input_settings') or {}, settings=f'Sets/{sname}', settings_sha256=sha(OUT / 'Sets' / sname),
                        risk_input_present=has_risk))
g = G
profile = dict(firm='Turbo programme (owner screenshot 2026-10-26)', account=50000, set_risk_percent=rec, profile_label_risk_percent=float(PROFILE_RISK),
               firm_rules=dict(daily_loss='3% of day-start balance (assumed basis)', max_loss='6% trailing below highest closed balance (assumed; re-based after rewards)',
                               rewards='every 14 days (5-day option), 3 profitable days >= 0.5%, consistency 20%, share 80% (95% upgrade)'),
               guard_for_recommended=dict(per_trade_usd=f"min(${float(PROFILE_RISK) * 500:,.0f}, {100 * g['taper']:.0f}% of room) -> at most $150", max_open_risk_usd=g['maxopen'] / 100 * 50000, max_per_symbol_usd=g['persym'] * float(PROFILE_RISK) / 100 * 50000,
                                          daily_profit_cap_usd=g['dcap'] / 100 * 50000,
                                          daily_soft_stop_usd=g['dstop'] / 100 * 50000, trailing_buffer_usd=g['buffer'] / 100 * 50000,
                                          room_taper=f"risk <= {100 * g['taper']:.0f}% of (balance - open stops - trailing floor)" if g['taper'] else 'off',
                                          fit='cut each trade to fit every limit; skip under $25 risk'),
               guards_by_risk={r: imp['risks'][r]['guard'] for r in imp['risks']}, removed_as_drags=imp['drags'], evidence='AAA EAs/BM Trading Robust Sets 2026-08-04/Turbo 50k Funded Portfolio 2026-10-26/')
(OUT / 'RISK_PROFILE.json').write_text(json.dumps(profile, indent=1), encoding='utf-8')
(OUT / 'PORTFOLIO.json').write_text(json.dumps(dict(name='Turbo 50k Funded Portfolio 2026-10-26', status='RESEARCH FILES ONLY - no installer, no guard EA built',
                                                    members=members), indent=1), encoding='utf-8')
print(OUT, len(members), 'members;', len(list((OUT / 'EAs').iterdir())), 'EX5 files')
