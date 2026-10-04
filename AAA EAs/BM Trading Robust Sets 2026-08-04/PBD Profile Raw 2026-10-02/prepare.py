"""Mechanical reuse of safe isolated native runner and net-position ledger."""
from pathlib import Path
p=Path(__file__).resolve().parent
old=p.parent/'Tier VWAP Raw 2026-10-02'
tail=(old/'EA/Main.mqh').read_text().split('struct Item{',1)[1].split('void OnDeinit',1)[0]
tail='struct Item{'+tail.replace('rows[k].id,"VWAP",','rows[k].id,ix>=0?initial[ix].module:"UNKNOWN",')
(p/'EA/Main.mqh').write_text((p/'EA/Head.mqh').read_text()+tail+'\nvoid OnDeinit(const int why){if(audit!=INVALID_HANDLE)FileClose(audit);if(trace!=INVALID_HANDLE)FileClose(trace);if(barsFile!=INVALID_HANDLE)FileClose(barsFile);if(profileFile!=INVALID_HANDLE)FileClose(profileFile);if(inputFile!=INVALID_HANDLE)FileClose(inputFile);}\n')
s=(old/'native.py').read_text().replace('TierVWAPRaw20261002','PBDProfileRaw20261002').replace('tier-vwap-raw-20261002','pbd-profile-raw-20261002').replace('VWAPRaw','PBDRaw')
s=s.replace("FIELDS=['baseline']","FIELDS=['module']").replace("tag='vwap-'","tag='pbd-'").replace('InpMagic=10020200','InpMagic=10020300')
s=s.replace("('net.json','trades.csv','signals.csv','trace.csv','bars.csv')","('net.json','trades.csv','signals.csv','trace.csv','bars.csv','profiles.csv','profile-inputs.csv')")
s=s.replace('raw VWAP','raw PBD proxy').replace('VWAP baseline','PBD proxy')
s=s.replace("if gl else (99.0 if gp > 0 else None)","if gl else (99.0 if gp > 0 else None)")
(p/'native.py').write_text(s)
