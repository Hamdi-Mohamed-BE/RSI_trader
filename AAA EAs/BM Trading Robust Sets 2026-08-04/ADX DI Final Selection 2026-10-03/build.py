"""User's final filter choices; reuse exact native-tested binaries, no live MT5."""
from pathlib import Path
import hashlib,json

R=Path(__file__).resolve().parent;B=R.parent
OLD=B/'ADX DI Deployment 2026-10-03'
STUDY=B/'ADX DI Five Bot Review 2026-10-03'
VERSION='ADXDI-FINAL-20261003'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')

def build():
    snapshot=R/'BEFORE.json'
    if not snapshot.exists():
        ftmo=B/'FTMO Thirteen EA Deployment 2026-09-27'
        store=B.parent/'EA store'
        rsi=bots_rsi=load(STUDY/'bots.json')['rsi']
        paths=[Path(rsi[k]) for k in ('original','source','setting')]
        paths+=list((store/'data/evidence-cache/v1/products/xau-rsi-vwap').rglob('*.json'))
        client=B.parents[1]/'clients/_owner/top5/manifest.json'
        if client.exists():paths.append(client)
        save(snapshot,dict(ftmo_manifest=load(ftmo/'PACKAGE.json'),guard_sha=sha(ftmo/'CalyxFTMOGuard.mqh'),unchanged_hashes={str(p):sha(p) for p in paths}))
    prior=load(OLD/'SELECTION.json');bots=load(STUDY/'bots.json');profiles={}
    for slug,old in prior['profiles'].items():
        b=bots[old['key']];p=dict(old)
        if old['key']=='london':
            assert sha(B/old['expert'])==old['expert_sha']
            inputs=dict(old['inputs']);status='kept';variant=old['variant']
        else:
            assert sha(Path(b['original']))==b['original_sha'] and sha(Path(b['source']))==b['source_sha']
            inputs=dict(b['inputs']);status='removed';variant='BASE'
            p.update(expert=str(Path(b['original']).relative_to(B)),expert_sha=b['original_sha'],source_sha=b['source_sha'])
            assert not any(k in inputs for k in ('InpUseADXFilter','InpRequireDIAgreement','InpStudyDI'))
        settings=R/'Sets'/(slug+'.set')
        settings.parent.mkdir(parents=True,exist_ok=True)
        settings.write_text(''.join(f'{k}={v}\n' for k,v in inputs.items()),encoding='utf-8')
        p.update(settings=str(settings.relative_to(B)),settings_sha=sha(settings),inputs=inputs,
                 variant=variant,research_case=old['key']+'-'+('ADX20_DI' if status=='kept' else 'ORIGINAL'),
                 filter_status=status,provisional=False)
        profiles[slug]=p
        print('SELECTED',slug,status,flush=True)
    selection=dict(version=VERSION,profiles=profiles,rsi_vwap='Unchanged, including binaries, inputs and evidence',
                   prior_release=str(OLD.relative_to(B)),live_terminal_changed=False,
                   promotion='Explicit user decision after frozen 1y/3y/5y comparisons; no new search or forecast')
    save(R/'SELECTION.json',selection)
    return selection

if __name__=='__main__':build()
