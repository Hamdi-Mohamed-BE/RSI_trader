"""Four frozen raw rules, not a parameter optimisation. Local tester only."""
import argparse
import native
p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--asset',choices=['USTEC','XAUUSD','BTCUSD']);args=p.parse_args()
symbols=[args.asset] if args.asset else ['USTEC','XAUUSD','BTCUSD']
rows=[]
for symbol in symbols:
 if args.smoke:
  rows+=native.batch(symbol+'-smoke',[dict(module=4)],'2026.09.01','2026.10.02',model=4,symbol=symbol)
 else:
  for label,start in [('1y','2025.10.02'),('6m','2026.04.02')]:
   for module in [1,2,3,4]:
    rows+=native.batch(symbol+'-'+str(module)+'-'+label,[dict(module=module)],start,'2026.10.02',model=4,symbol=symbol)
native.save(native.ROOT/(('SMOKE' if args.smoke else 'SUMMARY')+('-'+args.asset if args.asset else '')+'.json'),rows)
