"""Mechanically reuse audited isolated runner / position ledger; never touch live terminal."""
from pathlib import Path
R=Path(__file__).resolve().parent
old=R.parent/'Tier VWAP Raw 2026-10-02'
tail='struct Item{'+(old/'EA/Main.mqh').read_text().split('struct Item{',1)[1].split('void OnDeinit',1)[0]
tail=tail.replace('"VWAP"','"EMA_AVWAP"')
tail=tail.replace('double OnTester(){HistorySelect','double OnTester(){ExportInputs();HistorySelect')
(R/'EA/Main.mqh').write_text((R/'EA/Head.mqh').read_text()+tail+'void OnDeinit(const int why){if(audit!=INVALID_HANDLE)FileClose(audit);if(trace!=INVALID_HANDLE)FileClose(trace);if(barsFile!=INVALID_HANDLE)FileClose(barsFile);IndicatorRelease(e9);IndicatorRelease(e21);IndicatorRelease(e50);IndicatorRelease(atrh);}\n')
s=(old/'native.py').read_text().replace('TierVWAPRaw20261002','__RESEARCH_NAMESPACE__').replace('tier-vwap-raw-20261002','ema-avwap-raw-20261004').replace('VWAPRaw','EMAAVWAPRaw').replace('__RESEARCH_NAMESPACE__','EMAAVWAPRaw20261004')
s=s.replace("tag='vwap-'","tag='avwap-'").replace('InpMagic=10020200','InpMagic=10040401').replace('warmup=0,symbol','warmup=400,symbol')
s=s.replace('risk_percent=1,deposit','risk_percent=0.5,deposit').replace('InpRiskPercent=1.0','InpRiskPercent=0.5')
s=s.replace("'trace.csv','bars.csv')","'trace.csv','bars.csv','d1.csv','h1.csv')")
(R/'native.py').write_text(s)
print('Prepared tester-only source and isolated runner')
