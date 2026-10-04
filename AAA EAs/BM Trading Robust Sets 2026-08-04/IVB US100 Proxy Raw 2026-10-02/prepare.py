"""Mechanical reuse of tester, clocks, ledger and sizing. New entry logic."""
from pathlib import Path
root=Path(__file__).resolve().parent
old=root.parent/'US100 ORB Exploratory 2026-10-02'
m=(old/'EA/Main.mqh').read_text();head=m.split('void OnTick(){',1)[0];tail='struct Item{'+m.split('struct Item{',1)[1]
head=head.replace('US100ORBExplore20261002','IVBUS100Proxy20261002').replace('InpMagic=10020100','InpMagic=10020250').replace('955','840').replace('if(P(5)<0.5)return false;','')
head=head.replace('emaHandle=INVALID_HANDLE;','emaHandle=INVALID_HANDLE,ticksFile=INVALID_HANDLE;\nint tickErrors=0;')
head=head.replace('if(P(4)>0){emaHandle=iMA(_Symbol,PERIOD_H1,(int)P(4),0,MODE_EMA,PRICE_CLOSE);if(emaHandle==INVALID_HANDLE)return INIT_FAILED;}','')
head=head.replace('"h1_close","ema"','"previous_bid_seed","up_ticks","down_ticks"')
head=head.replace('PrintFormat("ORBEX_SPEC', 'ticksFile=FileOpen(Dir+Tag()+"-ticks.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,\',\');if(ticksFile==INVALID_HANDLE)return INIT_FAILED;FileWrite(ticksFile,"signal_bar","time_msc","bid");\n PrintFormat("ORBEX_SPEC',1)
tail=tail.replace('"ORB"','"IVB_PROXY"').replace('if(emaHandle!=INVALID_HANDLE)IndicatorRelease(emaHandle);','if(emaHandle!=INVALID_HANDLE)IndicatorRelease(emaHandle);if(ticksFile!=INVALID_HANDLE)FileClose(ticksFile);PrintFormat("IVB_PROXY_TICK_ERRORS=%d",tickErrors);')
tail=tail.replace('\\"skips\\":%d}', '\\"skips\\":%d,\\"tick_errors\\":%d}').replace('ranges,signals,skips));','ranges,signals,skips,tickErrors));')
(root/'EA/Main.mqh').write_text(head+(root/'EA/Entry.mqh').read_text()+tail)
s=(old/'native.py').read_text().replace('US100ORBExplore20261002','IVBUS100Proxy20261002').replace('us100-orb-explore-20261002','ivb-us100-proxy-20261002').replace('ORBSearch','IVBProxy').replace('InpMagic=10020100','InpMagic=10020250').replace('warmup=90):','warmup=0):').replace("tag='orb-'","tag='ivb-'")
s=s.replace("('net.json','trades.csv','signals.csv','trace.csv')","('net.json','trades.csv','signals.csv','trace.csv','ticks.csv')").replace('Tester-only exploratory US100 ORB (generated frozen case table).','Tester-only Exness US100 IVB quote-delta proxy.')
(root/'native.py').write_text(s)
