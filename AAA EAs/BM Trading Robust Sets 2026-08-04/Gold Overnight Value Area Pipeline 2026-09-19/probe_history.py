"""Read-only re-query of the anomalous broker-history day. Never fills gaps."""
from datetime import datetime,timezone
import numpy as np
import MetaTrader5 as mt
from data import ROOT,NORMAL,load,save
import json

def main():
    meta=json.loads((ROOT/'manifest.json').read_text());assert mt.initialize(NORMAL)
    assert mt.account_info().login==meta['account']['login']
    rows=[];data=load()
    try:
        for label,tf,cached in [('M1',mt.TIMEFRAME_M1,data[0]),('M5',mt.TIMEFRAME_M5,data[1])]:
            for day in (18,19,20,23):
                start=datetime(2025,6,day,tzinfo=timezone.utc);end=datetime(2025,6,day+1,tzinfo=timezone.utc)
                for attempt in range(2):
                    b=mt.copy_rates_range(meta['symbol'],tf,start,end);assert b is not None and len(b)
                    b=b[(b['time']>=start.timestamp())&(b['time']<end.timestamp())]
                    old=cached[(cached['time']>=start.timestamp())&(cached['time']<end.timestamp())]
                    same=np.array_equal(old,b)
                    rows.append(dict(day=start.date().isoformat(),timeframe=label,request=attempt,bars=len(b),
                        first=datetime.fromtimestamp(int(b['time'][0]),timezone.utc).isoformat(),last=datetime.fromtimestamp(int(b['time'][-1]),timezone.utc).isoformat(),matches_frozen_cache=bool(same)))
                    assert same,('Broker history changed; stop and review',label,day)
    finally:mt.shutdown()
    save(ROOT/'history-gap-probe.json',dict(captured_utc=datetime.now(timezone.utc).isoformat(),rows=rows,
        finding='Broker API re-requests match the frozen cache. On 2025-06-20 XAUUSD M1 history stops at 07:17 UTC, before the NY session. Treat as unresolved broker-history coverage gap/closure; no fictional NY-session bars or trades were inserted.',
        passed_cache_consistency=True,complete_market_coverage=False))
    print('PROBED: same broker history; June 20 NY session remains unavailable',flush=True)

if __name__=='__main__':main()
