"""The risk-only compatibility bridge must reject unverified evidence/builds."""
import hashlib
import json
import pytest
from app.news_runtime_compatibility import historical_news_source

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

@pytest.fixture
def bundle(tmp_path):
    source=tmp_path/'active.mq5'; source.write_text('new risk-input implementation')
    source.with_suffix('.ex5').write_bytes(b'compiled-new')
    audit=tmp_path/'News Standalone Risk 2026-09-28'
    baseline=audit/'baseline'/source.name
    baseline.parent.mkdir(parents=True)
    baseline.write_text('original 0.75 percent implementation')
    build={'baseline_source_sha256':digest(baseline),'source_sha256':digest(source),
           'binary_sha256':digest(source.with_suffix('.ex5'))}
    verification={'passed':True,'build':{'XAU':build},'checks':[{
        'asset':'XAU','default_risk_exact_trade_parity':True,'custom_risk_geometry_unchanged':True}]}
    manifest=audit/'NATIVE_VERIFICATION.json'
    manifest.write_text(json.dumps(verification))
    return tmp_path,source,baseline,manifest,verification

def test_original_matching_source_needs_no_compatibility_bridge(tmp_path):
    source=tmp_path/'source.mq5';source.write_text('original')
    assert historical_news_source(tmp_path,source,digest(source),'XAU')==source

def test_verified_risk_only_release_keeps_old_source(bundle):
    root,source,baseline,manifest,verification=bundle
    assert historical_news_source(root,source,digest(baseline),'XAU')==baseline

@pytest.mark.parametrize('change',['source','binary','baseline','missing_manifest','invalid_json',
                                  'failed','string_passed','no_parity','changed_geometry','wrong_asset',
                                  'unknown_build'])
def test_unknown_or_damaged_compatibility_is_rejected(bundle,change):
    root,source,baseline,manifest,verification=bundle
    expected=digest(baseline);asset='XAU'
    if change=='source':source.write_text('unreviewed change')
    elif change=='binary':source.with_suffix('.ex5').write_bytes(b'unreviewed binary')
    elif change=='baseline':baseline.write_text('substituted historical source')
    elif change=='missing_manifest':manifest.unlink()
    elif change=='invalid_json':manifest.write_text('{')
    elif change=='wrong_asset':asset='UNKNOWN'
    else:
        if change=='failed':verification['passed']=False
        elif change=='string_passed':verification['passed']='false'
        elif change=='no_parity':verification['checks'][0]['default_risk_exact_trade_parity']=False
        elif change=='changed_geometry':verification['checks'][0]['custom_risk_geometry_unchanged']=False
        elif change=='unknown_build':verification['build']['XAU']['source_sha256']='0'*64
        manifest.write_text(json.dumps(verification))
    with pytest.raises(RuntimeError,match='without a verified'):
        historical_news_source(root,source,expected,asset)
