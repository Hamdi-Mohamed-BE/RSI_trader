"""Independently reconcile native optimization receipts, then summarize research.
No production/deployment writes. Run after both research engines complete.
"""
from pathlib import Path
import gzip,json,math,xml.etree.ElementTree as ET

R=Path(__file__).resolve().parent
P=R.parent/'News XAU Exit Optimization 2026-10-03'
NS={'s':'urn:schemas-microsoft-com:office:spreadsheet'}

def audit(root):
 checked=[]
 for receipt in root.glob('native/*/report.xml.gz'):
  data=ET.fromstring(gzip.decompress(receipt.read_bytes()))
  rr=data.findall('.//s:Table/s:Row',NS)
  cols=[d.text for d in rr[0].findall('s:Cell/s:Data',NS)]
  native={}
  for row in rr[1:]:
   vals=[d.text for d in row.findall('s:Cell/s:Data',NS)]
   x=dict(zip(cols,vals));native[int(x['InpExitCase'])]=x
  parsed=json.loads((receipt.parent/'results.json').read_text())
  assert set(native)=={x['case'] for x in parsed}
  for x in parsed:
   n=native[x['case']]
   assert abs(float(n['Profit'])-x['net_profit'])<.061
   assert int(n['Trades'])==x['trades']
   assert abs(float(n['Equity DD %'])-x['equity_dd'])<.00011
   assert x['native']['open_positions']==x['native']['pending_orders']==0
   assert x['native']['boundary_violation']==0
   assert x['native']['attempted_events']==x['native']['complete_straddles']
  checked.append(str(receipt.relative_to(root)))
 return checked

def row(x):
 pf='undefined (no losses)' if x['net_pf'] is None else f"{x['net_pf']:.3f}"
 return (f"{x['label']}: return {x['return_pct']:+.2f}%; net PF {pf}; "
  f"win {x['win_rate']:.2f}%; trades {x['trades']}; native equity DD {x['equity_dd']:.3f}%; "
  f"winning/losing streak {x['win_streak']}/{x['loss_streak']}; "
  f"average win/loss ${x['average_win']:.2f}/${x['average_loss']:.2f}; "
  f"closed-weekday Sharpe {x['daily_closed_sharpe']:.2f}.")

def main():
 full=json.loads((R/'RESULTS.json').read_text());pilot=json.loads((P/'RESULTS.json').read_text())
 receipts={'expanded':audit(R),'pilot':audit(P)}
 selection=full['selection'];case=selection['case'];v=full['validation']
 base=next(x for x in v if x['case']==0);chosen=next(x for x in v if x['case']==case)
 val_ok=(case!=0 and chosen['return_pct']>base['return_pct'] and
  chosen['win_rate']>=base['win_rate']-1e-8 and
  chosen['equity_dd']<=max(1.5,base['equity_dd']*1.5))
 annual=full['annual'][0];current=full['baseline_year'];stress=full['stress'][0]
 cm=current['net_metrics'];nm=current['native']
 annual_ok=case!=0 and annual['return_pct']>cm['return_pct'] and annual['win_rate']>=cm['win_rate_pct']-1e-8
 wins=round(cm['win_rate_pct']*cm['trades']/100);n=cm['trades'];phat=wins/n;z=1.96
 den=1+z*z/n;center=(phat+z*z/(2*n))/den
 half=z*math.sqrt(phat*(1-phat)/n+z*z/(4*n*n))/den
 assessment=dict(selected_case=case,validation_pass=val_ok,annual_win_return_pass=annual_ok,
  recommend_promotion=val_ok and annual_ok,xml_receipts=receipts,
  baseline_win_rate_wilson_95_pct=[100*(center-half),100*(center+half)],
  caveats=['selection optimization, not untouched out of sample','75% full-year real ticks',
   'very small event sample','no news order-book fill realism','extended hold also extends opposite pending-order lifetime'])
 (R/'ASSESSMENT.json').write_text(json.dumps(assessment,indent=2),encoding='utf-8')
 text=['XAU NEWS PULSE EXIT / HOLD RESEARCH — 2026-10-03',
  'Year: 2025-10-03 inclusive to 2026-10-03 exclusive. $10,000 start, 0.75% equity risk per enabled side.',
  '$10 initial stop, $6 quote offset, both sides enabled; potential 1.5% nominal event exposure before costs/rounding/gaps.',
  'Targets $40/$60/$80 refer to XAU price movement, not account profit. Holds measured AFTER scheduled release.',
  'Longer holds also leave the opposite pending order eligible longer; trade counts can change.',
  'Production EA, BATs, public website cache and normal running MT5 were not changed.',
  '',f"CURRENT 30s: return {cm['return_pct']:+.2f}%; net PF {cm['pf']:.3f}; win {cm['win_rate_pct']:.2f}%; trades {cm['trades']}; native equity DD {nm['max_drawdown_pct']:.2f}%.",
  row(annual),row(stress),
  '',f"PRE-FROZEN DEVELOPMENT CHOICE: case {case}, {selection['label']}",
  'Development: 2025-10-03 to 2026-07-03 exclusive; selection required no drop in net win rate, PF >=1.2, higher return and DD <= max(1.5%, baseline DD *1.5).',
  '', 'CHRONOLOGICAL VALIDATION: 2026-07-03 to 2026-10-03 exclusive',row(base),row(chosen),
  f"Validation passed: {val_ok}. Whole-year win-rate / return improvement passed: {annual_ok}.",
  'Recommendation: '+('Keep this as a demo candidate; forward-test before promotion.' if val_ok and annual_ok else 'Keep current exits. No selected setting demonstrated the requested improvement across both periods.'),
  '', 'ALL 18 DEVELOPMENT CANDIDATES (not full-year rankings):']
 text.extend(row(x) for x in sorted(full['development'],key=lambda x:-x['return_pct']))
 text+=['','EARLIER 30s-ONLY STUDY','Development-selected 3R / no trail:',row(pilot['annual'][0])]
 text.extend(row(x) for x in pilot['validation'])
 text+=['','LIMITATIONS',
  f"Only {n} baseline trades; 95% Wilson win-rate interval is approximately {100*(center-half):.1f}%–{100*(center+half):.1f}% (not accounting for within-event dependence).",
  '75% full-year real ticks: pre-Jan-2026 gaps used generated ticks. Validation baseline was already inspected; not a pristine holdout.',
  'Native floating-equity drawdown is reported, not only closed balance. Sparse closed-weekday Sharpe is not intraday floating-equity Sharpe.',
  'Returns/PF include recorded commission, swap and fees. MT5 delay stress does not reproduce real news liquidity, queue priority or unfillable gaps.',
  'Selection is the best eligible setting in a finite menu, not a global optimum or a guarantee. No production deployment.',
  f"Independent XML-to-deal audit reconciled {sum(map(len,receipts.values()))} optimization receipts."]
 (R/'RESULTS.txt').write_text('\n'.join(text)+'\n',encoding='utf-8')
 print(json.dumps(assessment,indent=2))

if __name__=='__main__':main()
