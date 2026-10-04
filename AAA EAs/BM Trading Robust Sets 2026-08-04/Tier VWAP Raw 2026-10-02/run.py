import argparse
import native
parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
rows=[]
if args.smoke:
 rows=native.batch('smoke',[dict(baseline=1)],'2026.09.01','2026.10.02',model=4)
else:
 for symbol in ['USTEC','US500']:
  for window,start in [('1y','2025.10.02'),('3y','2023.10.02'),('5y','2021.10.02'),('6m','2026.04.02')]:
   rows+=native.batch(symbol+'-'+window,[dict(baseline=1)],start,'2026.10.02',model=4,symbol=symbol)
native.save(native.ROOT/('SMOKE.json' if args.smoke else 'SUMMARY.json'),rows)
