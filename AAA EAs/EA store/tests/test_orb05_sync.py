"""Owner-approved target and roster must agree everywhere, without live MT5 access."""
import json
from pathlib import Path
import pytest
from app.catalog import PACKAGE_ROOT,get_website_catalog
from app.portfolios import portfolio_catalog
from app.prop_sim.ledger import load_ea
from test_live_portfolio_launchers import powershell,import_helper,quote,SHARED

POLICY=json.loads((PACKAGE_ROOT/'_00 Live profiles/ORB05-policy.json').read_text())
ORBS=set(POLICY['slugs'])

def test_all_five_targets_and_memberships_in_every_current_profile():
    for p in portfolio_catalog()['portfolios']:
        members={m['slug']:m for m in p['members']}
        assert ORBS<=set(members)
        for slug in ORBS:
            assert members[slug]['target_rr']==.5
            assert float(members[slug]['inputs']['InpRewardRisk'])==.5
    reviewed=json.loads((PACKAGE_ROOT/'Reviewed EA Deployment 2026-10-06/selection.json').read_text())
    entries={e['slug']:e for e in reviewed['entries']}
    assert all(entries[s]['phase']=='live' and entries[s]['input_overrides']['InpRewardRisk']=='0.5' for s in ORBS)

def test_both_new_wrapped_packages_and_ftmo_guarded_package():
    for name in ['Current14 Plus ORB05 Portfolio 2026-10-08/Package.json','_00 Live profiles/Packages/FTMO/PACKAGE.json','_00 Live profiles/Packages/ORB-only/Package.json']:
        p=json.loads((PACKAGE_ROOT/name).read_text());key='slug' if 'FTMO/' in name else 'key'
        assert set(p['orb_keys'])==ORBS
        assert all(float(e['inputs']['InpRewardRisk'])==.5 for e in p['entries'] if e[key] in ORBS)
    ftmo=json.loads((PACKAGE_ROOT/'_00 Live profiles/Packages/FTMO/PACKAGE.json').read_text())
    assert len({e['inputs']['InpMagic'] for e in ftmo['entries']})==17

@pytest.mark.parametrize('slug',sorted(ORBS))
@pytest.mark.parametrize('period',['6m','1y','3y','5y'])
def test_simulator_target_ledger_is_not_old_cached_target(slug,period):
    p,trades=load_ea(slug,period)
    assert '0.5R' in p.risk_note
    from app.catalog import STORE_ROOT
    from datetime import datetime,timezone
    payload=json.loads((STORE_ROOT/'data/portfolio-risk-ledgers.json').read_text())['orbs-only']
    rows=payload[payload['window_sources'][period]]
    start=datetime.combine(p.start,datetime.min.time()).replace(tzinfo=timezone.utc).timestamp()
    end=datetime.combine(p.end,datetime.max.time()).replace(tzinfo=timezone.utc).timestamp()
    expected=[r for r in rows if r['key']==slug and start<=r['op']<=r['cl']<end]
    assert len(trades)==len(expected)
    assert sum(t.r*t.risk_cash for t in trades)==pytest.approx(sum(t['unit_gross']+t['unit_comm']+t['unit_swap'] for t in expected),abs=.001)
    assert load_ea(slug,period,'safe') is None

def test_normal_safe_dynamic_reviewed_shared_installer_forces05_only_on_these_labels():
    product={p.slug:p for p in get_website_catalog()}
    setup=json.loads((PACKAGE_ROOT/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json').read_text())['setups']
    entries=[e for e in setup if e['slug'] in ORBS]
    for e in entries:assert product[e['slug']].installer_label in POLICY['installer_labels']
    fixture=json.dumps([dict(label=e['label'],preset=e['preset']) for e in entries]).replace("'","''")
    script=import_helper(SHARED,['Read-SetInputs','Test-NewsAdaptiveExemption','Get-EffectiveInputs'])
    script+="""
 $UseAdaptiveProfile=$false;$IsAdaptiveAccount=$false;$IsSmallAccount=$false;$UsesDynamicRisk=$false;$IsFullSafe=$false
 $items=ConvertFrom-Json '"""+fixture+"""';$out=@()
 foreach($entry in $items){
  $item=[pscustomobject]@{Label=$entry.label;SetFullPath=$entry.preset;HistoricalLossSizing=$false;ForceEnable=$false;FixedPercentRisk=0;SupportsSafeFilter=$false;SafeByDesign=$false}
  $inputs=Get-EffectiveInputs $item;$out+=@{label=$entry.label;rr=$inputs['InpRewardRisk']}
 };$out|ConvertTo-Json -Compress
 """
    values=json.loads(powershell(script))
    assert len(values)==5 and all(float(v['rr'])==.5 for v in values)

def test_current_download_sets_are05_and_old_benchmarks_clearly_archived():
    products={p.slug:p for p in get_website_catalog()}
    for slug in ORBS:
        p=products[slug];source=Path(p.set_source)
        if not source.is_absolute():source=PACKAGE_ROOT/source
        assert 'InpRewardRisk=0.5' in source.read_text()
        assert 'archived targets' in p.one_year_note
