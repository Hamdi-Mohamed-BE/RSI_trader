"""Check generated evidence against native deal ledgers and NY entry times."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib,json
import run_research as research

root=Path(__file__).resolve().parent
checked=0
for path in sorted((root/'Reports').glob('*/*.json')):
    if path.name.endswith('-trades.json'): continue
    row=json.loads(path.read_text())
    start,end,model=research.WINDOWS[row['stage']]
    fingerprint=hashlib.sha256((research.SOURCE.read_text()+json.dumps(row['config'],sort_keys=True)+start+end+str(model)+row['symbol']).encode()).hexdigest()
    assert row['fingerprint']==fingerprint, f'Stale evidence: {path.name}'
    trades=research.trade_audit(Path(row['report']))
    assert len(trades)==row['trades'],path.name
    assert abs(sum(t['net'] for t in trades)-row['net_profit'])<0.05,path.name
    dates=set()
    c=row['config']
    assert c['InpRiskPercent']==1.0,path.name
    assert row['history_quality_pct']>=90,path.name
    if row['stage']!='development': assert row['execution_mode']==-1,path.name
    for t in trades:
        ny=datetime.fromisoformat(t['entry_time']).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/New_York'))
        assert ny.date() not in dates, f'Multiple entries per day: {path.name}'
        dates.add(ny.date())
        minute=ny.hour*60+ny.minute
        wanted=c['InpEntryHourNY']*60+c['InpEntryMinuteNY']
        assert 0<=minute-wanted<=1, f'Entry window / DST mismatch: {path.name} {ny}'
        assert 0<=t['holding_minutes']<=180, f'Unexpected holding period: {path.name}'
    checked+=1
print(f'PASS: {checked} native reports; net P/L reconciled; no duplicate daily entries; NY/DST entry times verified; 1% risk; no overnight holdings; validation uses random delay.')
(root/'VERIFICATION.txt').write_text(f'PASS: {checked} native reports checked.\nTrade count and net profit reconciled to MT5.\nSource fingerprints match.\nOne trade per NY date; expected NY/DST entry times.\n1% risk inputs. No holding above 180 minutes.\nHeld-out/full runs use random execution delay.\n',encoding='utf-8')
