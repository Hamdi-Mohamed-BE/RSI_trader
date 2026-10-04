import argparse
import native
case=dict(opening_minutes=30,rr=1,entry_cutoff=840,direction=1,ema=0,adaptive_close=1)
p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');args=p.parse_args();rows=[]
if args.smoke:rows=native.batch('smoke',[case],'2026.09.01','2026.10.02',model=4)
else:
 for w,start in [('real-2026','2026.01.01'),('6m','2026.04.02'),('1y','2025.10.02'),('3y','2023.10.02'),('5y','2021.10.02')]:rows+=native.batch(w,[case],start,'2026.10.02',model=4)
native.save(native.ROOT/('SMOKE.json' if args.smoke else 'SUMMARY.json'),rows)
