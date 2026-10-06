import argparse
import native
p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');a=p.parse_args()
rows=[]
if a.smoke:
 rows=native.batch('smoke-v2',[dict(baseline=1)],'2026.09.01','2026.10.04',model=4)
else:
 for symbol in ['USTEC','US30','UK100','XAUUSD','BTCUSD']:
  for window,start in [('1y','2025.10.04'),('3m','2026.07.04')]:
   rows+=native.batch(symbol+'-'+window,[dict(baseline=1)],start,'2026.10.04',model=4,symbol=symbol)
   native.save(native.ROOT/'SUMMARY.json',rows)
native.save(native.ROOT/('SMOKE.json' if a.smoke else 'SUMMARY.json'),rows)
