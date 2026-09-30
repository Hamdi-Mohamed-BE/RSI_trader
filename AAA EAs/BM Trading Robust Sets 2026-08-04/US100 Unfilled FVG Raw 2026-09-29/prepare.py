"""Mechanical snapshot/assembly of known execution and reporting plumbing; no terminals."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
old=R.parent/'Market Style Bots Raw 2026-09-29'
src=(old/'MarketStyles.mq5').read_text()
prefix=src[:src.index('double Average(')].replace('MarketStyles','UnfilledFVG').replace('1.00','1.00').replace('input double InpRR=3.0','input double InpRR=1.0')
footer=src[src.index('struct Item {'):src.index('void OnDeinit(')]
footer=footer.replace('CalyxMarketStyles20260929','CalyxUnfilledFVG20260929')
(R/'UnfilledFVG.mq5').write_text(prefix+'\n#include "logic.mqh"\n'+footer)
run=(old/'run.py').read_text().replace('MarketStyles20260929','UnfilledFVG20260929').replace('MarketStyles','UnfilledFVG').replace('market-styles-20260929','unfilled-fvg-20260929')
run=run.replace("'RULES.md','run-config.json'","'RULES.md','run-config.json','logic.mqh','run.py','prepare.py'")
run=run.replace("['trades.csv','signals.csv','trace.csv']","['trades.csv','signals.csv','trace.csv','audit.csv']")
run=run.replace("with (ROOT/'tester.lock').open('a+b') as lease:","with (TESTER/'research-serial.lock').open('a+b') as lease:")
run=run.replace("proc=subprocess.Popen(","startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0\n proc=subprocess.Popen(")
run=run.replace('cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)','cwd=TESTER,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)')
# Confirm every raw version, not only screened winners; controls only on long windows.
run=run.replace("  elif mode=='confirm':\n   for g in gates():\n    if g['screen_pass']:\n     for w in ['3y','5y']:\n      for c in [False,True]:case(g['bot'],w,4,c)","  elif mode=='confirm':\n   for w in ['6m','1y','3y','5y']:\n    for b in CFG['bots']:\n     for c in ([False,True] if w in ['3y','5y'] else [False]):case(b,w,4,c)")
(R/'run.py').write_text(run)
(R/'PLUMBING.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [old/'MarketStyles.mq5',old/'run.py']},indent=2))
print('Research-only assembly ready; six fixed raw variants')
