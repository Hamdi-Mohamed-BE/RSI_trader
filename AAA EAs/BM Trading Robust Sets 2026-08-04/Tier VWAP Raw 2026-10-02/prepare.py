"""Mechanical reuse of archived native runner and position-net ledger, new namespaces."""
from pathlib import Path
p=Path(__file__).resolve().parent
old=p.parent/'US100 ORB Exploratory 2026-10-02'
tail=(old/'EA/Main.mqh').read_text().split('struct Item{',1)[1].split('void OnDeinit',1)[0]
tail='struct Item{'+tail.replace('"ORB"','"VWAP"')
(p/'EA/Main.mqh').write_text((p/'EA/Head.mqh').read_text()+tail+'void OnDeinit(const int why){if(audit!=INVALID_HANDLE)FileClose(audit);if(trace!=INVALID_HANDLE)FileClose(trace);if(barsFile!=INVALID_HANDLE)FileClose(barsFile);}\n')
s=(old/'native.py').read_text()
s=s.replace('US100ORBExplore20261002','TierVWAPRaw20261002').replace('us100-orb-explore-20261002','tier-vwap-raw-20261002').replace('ORBSearch','VWAPRaw')
s=s.replace("FIELDS=['opening_minutes','rr','entry_cutoff','direction','ema','adaptive_close']","FIELDS=['baseline']")
s=s.replace('warmup=90):','warmup=0,symbol="USTEC"):').replace('risk_percent=1,deposit=10000)','risk_percent=1,deposit=10000,symbol=symbol)')
s=s.replace("tag='orb-'","tag='vwap-'").replace('InpMagic=10020100','InpMagic=10020200').replace('Symbol=USTEC','Symbol={symbol}').replace("('USTEC',warm,end)","(symbol,warm,end)")
s=s.replace("('net.json','trades.csv','signals.csv','trace.csv')","('net.json','trades.csv','signals.csv','trace.csv','bars.csv')")
s=s.replace('Tester-only exploratory US100 ORB (generated frozen case table).','Tester-only raw VWAP baseline.').replace('Native optimisation over a frozen generated case table','Native raw VWAP tests over frozen parameters')
(p/'native.py').write_text(s)
