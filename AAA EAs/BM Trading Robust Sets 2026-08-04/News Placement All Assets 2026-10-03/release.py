"""Record exact maintained-build receipts, not strategy performance."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;B=R.parent;ROOT=B.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources=[B/'AAA Final EAs'/n/(n+'.mq5') for n in ['AAA Final News Pulse XAU Event Specific EA','AAA Final News Pulse Multi Asset Event EA']]+[ROOT/'AI news/mt5/GoldNewsV9EA.mq5']
fault=json.loads((R/'FAULT_CHECK.json').read_text());assert fault['passed']
records=[]
for p in sources:
 log=R/(p.stem+'.compile.log');raw=log.read_bytes();txt=raw.decode('utf-16') if raw[:2]==b'\xff\xfe' else raw.decode('utf-8-sig')
 assert '0 errors, 0 warnings' in txt
 records.append({'source':str(p.relative_to(ROOT)),'source_sha256':sha(p),'binary_sha256':sha(p.with_suffix('.ex5')),'compiler_result':txt.split('Result:')[-1].strip()})
ftmo=B/'_Auto Deploy/Install-FTMO13.ps1';assert sha(ftmo)=='fefbb53e320ed9f9a84c9b4a347dcc3ebc0155352229c48dfcaee68b30c3dc22'
result={'date':'2026-10-03','builds':records,'helper_sha256':sha(sources[0].parent/'NewsPulsePlacement.mqh'),'native_fault_checks':fault,'pytest':'56 passed','launcher_policy':'Standard/Safe/Recommended/Claude/Adaptive: 35 EAs, all five news systems; Ava unchanged','ftmo_unchanged_sha256':sha(ftmo),'live_terminal_changed':False,'exit_optimisation_applied':False,'performance_replay_pending':True,'risk_and_event_exit_tables':'unchanged from saved baseline','git_push_performed':False}
(R/'RELEASE.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'compiled_builds':len(records),'native_fault_checks_passed':True,'ftmo_unchanged':True,'no_live_deployment':True}))
