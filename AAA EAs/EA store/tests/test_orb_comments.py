"""Comment-only regression and distribution checks; never access an MT5 account."""
import importlib.util
import json
import subprocess
import pytest
from app.catalog import PACKAGE_ROOT

RELEASE = PACKAGE_ROOT/'ORB Comment Labels 2026-09-28'
spec = importlib.util.spec_from_file_location('orb_comment_build', RELEASE/'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

@pytest.mark.parametrize('source', build.SOURCES)
def test_no_trade_logic_or_input_changes(source):
    build.assert_comment_only(PACKAGE_ROOT/source)

def test_compiled_distributions_match_release():
    data=json.loads((RELEASE/'RELEASE.json').read_text())
    assert len(data['builds'])==5 and data['comment_only']
    assert build.sha(PACKAGE_ROOT/data['helper'])==data['helper_sha']
    for item in data['builds']:
        assert build.sha(PACKAGE_ROOT/item['source'])==item['source_sha']
        assert build.sha(PACKAGE_ROOT/item['expert'])==item['expert_sha']
        assert item['compile']=='0 errors, 0 warnings'

def test_ftmo_only_orb_binaries_changed_and_guards_unchanged():
    folder=PACKAGE_ROOT/'FTMO Thirteen EA Deployment 2026-09-27'
    before=json.loads(build.baseline(folder/'PACKAGE.json'))
    after=json.loads((folder/'PACKAGE.json').read_text())
    assert after['news_enabled'] is False and after['risk_usd']==50
    assert after['guard_sha']==before['guard_sha']==build.sha(folder/'CalyxFTMOGuard.mqh')
    # 2026-09-30: 3 Way Gold appended as entry 14; the original 13 must stay unchanged.
    assert len(before['entries']) in (13,14) and len(after['entries'])==14 and after['entries'][13]['slug']=='3-way-gold'
    assert after['entries'][13]['inputs']['InpMarketEntries']=='true' and after['entries'][13]['inputs']['InpRiskPercent']=='0.5'
    admission=json.loads((PACKAGE_ROOT/'ADX DI Final Selection 2026-10-03/SELECTION.json').read_text())
    for old,new in zip(before['entries'],after['entries']):
        if new['slug'] in admission['profiles']:
            profile=admission['profiles'][new['slug']]
            gates={k:profile['inputs'][k] for k in ('InpUseADXFilter','InpADXMinimum','InpRequireDIAgreement','InpADXTimeframe')} if profile['filter_status']=='kept' else {}
            expected={**old['inputs'],**gates}
            if new['slug']=='xau-trend-progression':expected['InpRewardRisk']='0.6'
            assert after['admission_release']==admission['version'] and new['inputs']==expected
            assert new['inputs']==expected  # restored baseline need not differ from historical artifact
            continue
        if new['slug']=='xau-trend-progression':
            # Separate, explicitly selected target release; guard/other inputs unchanged.
            assert after['gold_target_release']=='GOLD-TARGETS-20261002'
            expected={**old['inputs'],'InpRewardRisk':'0.6'}
            assert new['inputs']==expected
            assert new['settings_sha']!=old['settings_sha'] and new['expert_sha']!=old['expert_sha']
            continue
        assert old['inputs']==new['inputs'] and old['settings_sha']==new['settings_sha']
        differences={key for key in old if old[key]!=new[key]}
        if new['slug'] in ('xau-orb-london-ny-overlap-m30','us100-h1-orb-13utc'):
            assert differences=={'expert_sha'}
        else:assert differences==set()
    for name,digest in after['files'].items():assert build.sha(folder/'package'/name)==digest

def read_set(path):
    return dict(line.split('=',1)[0:1]+[line.split('=',1)[1].split('||')[0]] for line in build.read(path).splitlines() if '=' in line and not line.startswith(';'))

@pytest.mark.parametrize('preset,minutes,tf,zone,hour,minute,confirmed', [
    ('Selected Portfolio Settings 2026-09-01/05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set',15,5,0,9,30,False),
    ('Selected Portfolio Settings 2026-09-01/05C ORB Volume Profile Volume Confirmed - DYNAMIC 50-20 - ALL DAY.set',15,5,0,9,30,True),
    ('Selected Portfolio Settings 2026-09-01/14 XAU ORB New York M30 - LOCKED STANDALONE.set',30,30,0,9,30,False),
    ('Selected Portfolio Settings 2026-09-01/15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set',5,30,1,13,0,False),
    ('Selected Portfolio Settings 2026-09-01/16 US100 ORB New York M30 - LOCKED STANDALONE.set',5,30,0,9,30,False),
    ('ORB H1 Range Research 2026-09-05/Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set',60,15,1,13,0,False),
])
def test_label_inputs_match_real_presets(preset,minutes,tf,zone,hour,minute,confirmed):
    path=PACKAGE_ROOT/preset
    # No SET change is needed: comments derive from the same actual inputs.
    original=build.baseline(path)
    encoding='utf-16' if original.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    assert original.decode(encoding).replace('\r\n','\n')==build.read(path)
    inputs=read_set(path)
    for key,value in dict(InpOpeningRangeMinutes=minutes,InpSignalTimeframe=tf,InpSessionZone=zone,InpSessionHour=hour,InpSessionMinute=minute).items():
        assert int(inputs[key])==value
    assert (float(inputs['InpMinOpeningRelativeVolume'])>1 or float(inputs['InpMinBreakoutRelativeVolume'])>1)==confirmed

def test_selective_v3_identity_matches_preset():
    inputs=read_set(PACKAGE_ROOT/'US100 Selective ORB Research 2026-08-21/Sets/BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set')
    assert inputs['InpOpeningRangeMinutes']=='30'
    assert inputs['InpSignalTimeframe']=='5'
    assert inputs['InpUseTimeDirectionFilter']=='true'

def test_native_formatter_checks_and_safe_harness():
    result=json.loads((RELEASE/'NATIVE-CHECK.json').read_text())
    assert result['passed'] and result['checks']==13 and result['orders_submitted']==0
    assert len(result['labels'])==13
    source=(RELEASE/'CommentProbe.mq5').read_text()
    assert 'MQLInfoInteger(MQL_TESTER)' in source
    assert 'OrderSend' not in source and 'trade.Buy' not in source and 'trade.Sell' not in source

def test_source_hashes_survive_windows_checkout():
    paths=[(PACKAGE_ROOT/p).relative_to(build.REPO).as_posix() for p in build.SOURCES+['_Shared/CalyxORBComments.mqh']]
    output=subprocess.check_output(['git','check-attr','text','--',*paths],cwd=build.REPO,text=True)
    assert len(output.splitlines())==6
    assert all(line.endswith(': text: unset') for line in output.splitlines())
