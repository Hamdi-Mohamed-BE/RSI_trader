"""Finish generated report metadata and validate the complete research artifact."""
from pathlib import Path
from html.parser import HTMLParser
import json, runpy

R=Path(__file__).resolve().parent
m=runpy.run_path(str(R/'run.py'),run_name='rr05_report_helpers')
plan=m['read'](R/'PLAN.json');pairs=[]
for row in plan['setups']:
 file=R/'comparisons'/(row['slug']+'.json');pair=m['read'](file)
 for module in pair.get('module_breakdown',{}).values():
  for metrics in module.values():
   metrics['equity_dd_pct']=None;metrics['balance_dd_pct']=None
   metrics['account_drawdown_not_attributable_to_module']=True
 if pair.get('module_breakdown'):m['save'](file,pair)
 pairs.append(pair)
m['render'](plan,pairs)

class QA(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.targets=[];self.tables=0
 def handle_starttag(self,tag,attrs):
  values=dict(attrs)
  if 'id' in values:self.ids.append(values['id'])
  if tag=='a' and values.get('href','').startswith('#'):self.targets.append(values['href'][1:])
  if tag=='table':self.tables+=1

text=(R/'Results.html').read_text(encoding='utf-8');qa=QA();qa.feed(text)
assert len(pairs)==len(plan['setups'])==15
assert 'Pending' not in text and 'Completed 15 / 15' in text
assert len(qa.ids)==len(set(qa.ids))==15 and set(qa.targets)==set(qa.ids)
assert qa.tables==17
for pair in pairs:
 if pair.get('reused_verified_comparison'):
  prior=R.parent/'US100 H1 ORB RR05 Comparison 2026-10-08/Agent3010'
  assert m['read'](prior/'SUMMARY.json')['production_files_unchanged']
  assert m['read'](prior/'VERIFICATION.json')['no_optimization_or_deployment']
 else:assert pair['current']['no_live_changes'] and pair['half']['no_live_changes']
assert len(list((R/'native').glob('*/report.htm')))==28
assert m['read'](R/'INDEPENDENT_CHECK.json')['verified']==15
assert all(all(m['sha'](Path(p))==digest for p,digest in row['production_hashes'].items()) for row in plan['setups'])
audit=(R/'ReadOnlyAudit.mqh').read_text(encoding='utf-8')
assert 'OrderSend(' not in audit and 'OrderSendAsync(' not in audit and 'PositionClose(' not in audit
value=dict(completed=15,total=15,native_reports_new=28,native_reports_reused=2,
 all_production_hashes_unchanged=True,live_changes=False,report_anchor_and_table_checks=True,
 no_pending_results=True,module_account_metrics_not_misattributed=True,readonly_audit_has_no_order_operations=True)
m['save'](R/'FINAL_AUDIT.json',value)
print(json.dumps(value,indent=2))
for pair in pairs:
 a,b=pair['current']['metrics'],pair['half']['metrics']
 keys=['trades','win_rate','pf','return_pct','equity_dd_pct','sharpe_daily_equity','win_streak','loss_streak']
 print(pair['label'],json.dumps({k:[a[k],b[k]] for k in keys}))
