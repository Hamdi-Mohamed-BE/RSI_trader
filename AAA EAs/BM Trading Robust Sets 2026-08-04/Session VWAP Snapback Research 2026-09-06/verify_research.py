"""Independent structural and evidence-integrity checks for Step 4."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parent
SYMBOLS=('XAUUSD','XAGUSD','USTEC','US30','GBPJPY')
errors=[];checks=[]

def check(condition,message):
    checks.append(message)
    if not condition:errors.append(message)

selection=json.loads((ROOT/'selection-lock.json').read_text(encoding='utf-8'))
final=json.loads((ROOT/'screen-final.json').read_text(encoding='utf-8'))
native=json.loads((ROOT/'native-results.json').read_text(encoding='utf-8'))
progress=json.loads((ROOT/'progress.json').read_text(encoding='utf-8'))
grid=pd.read_csv(ROOT/'all-screen-results.csv')
check(tuple(selection)==SYMBOLS,'All five assets are present in the frozen selection lock')
check(all(selection[s]['config']==final[s]['config'] for s in SYMBOLS),'Locked evaluation uses the exact frozen configuration')
check(len(grid)==8630,'All 8,630 pre-lock configuration rows are saved')
check(set(grid.phase)=={'signal','direction','frequency','stop','target','management','session-timeframe-recheck'},'All required optimization stages are present')
check(len(native)==10,'Five native locked and five native full runs are saved')
check(all(row['inputs']['InpRiskPercent']==1.0 for row in native),'Every native test hard-locks risk to 1%')
check(all(row['inputs']['InpTesterOnly'] is True for row in native),'Every saved native SET uses tester-only safety')
check(all(row['history_quality_pct']>=99 for row in native if row['stage']=='locked'),'Every native locked run has at least 99% history quality')
check(all(row['model']==0 for row in native if row['stage']=='locked'),'Locked runs use generated Every Tick model')
check(all(row['model']==1 for row in native if row['stage']=='full'),'Three-year context runs use 1-minute OHLC model')
for row in native:
    case=f"{row['symbol'].lower()}-frozen-{row['stage']}-model{row['model']}";trades=json.loads((ROOT/'Native'/case/'trades.json').read_text(encoding='utf-8'))
    check(len(trades)==row['trades'],f'{case} trade ledger count reconciles')
    check(abs(sum(x['net'] for x in trades)-row['net_profit'])<=0.06,f'{case} trade cash reconciles')
compile_text=(ROOT/'EA'/'compile.log').read_text(encoding='utf-8')
check('0 errors, 0 warnings' in compile_text,'EA compiles with 0 errors and 0 warnings')
for name in ('locked-summary.png','locked-equity-curves.png','configuration-screen.png','native-locked-summary.png','rolling-stability.png','monte-carlo.png','rr-sensitivity.png','session-timeframe-sensitivity.png'):
    path=ROOT/'Charts'/name;check(path.exists() and path.stat().st_size>10000,f'{name} exists and is non-empty')
check(progress['status']=='complete' and progress['production_changed'] is False,'Progress is complete and records no production deployment')
text=('PASS' if not errors else 'FAIL')+f' — {len(checks)-len(errors)}/{len(checks)} checks passed\n\n'+'\n'.join(('[OK] ' if item not in errors else '[FAIL] ')+item for item in checks)+'\n'
(ROOT/'VERIFICATION.txt').write_text(text,encoding='utf-8')
print(text)
if errors:raise SystemExit(1)
