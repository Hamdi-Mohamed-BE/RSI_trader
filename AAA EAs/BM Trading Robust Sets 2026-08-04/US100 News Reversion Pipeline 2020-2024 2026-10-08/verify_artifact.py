"""Final independent checks of report, native hashes, source and export."""
from pathlib import Path
import hashlib,gzip,json,re
from bs4 import BeautifulSoup
import build_engine as b
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 s=json.loads((R/'SUMMARY.json').read_text());n=0
 def check(v,why):
  nonlocal n
  assert bool(v),why;n+=1
 for folder in (R/'native').iterdir():
  if not (folder/'results.json').exists():continue
  manifest=json.loads((folder/'manifest.json').read_text());rows=json.loads((folder/'results.json').read_text())
  expected=b.build(manifest['cases'])
  check(hashlib.sha256(expected.encode()).hexdigest()==manifest['engine_sha256'],'Generated source hash')
  check((folder/'OrbSearch.mq5').read_text()==expected,'Compiled source differs')
  report=folder/('report.xml.gz' if manifest['optimize'] else 'report.htm.gz')
  content=gzip.decompress(report.read_bytes())
  for row in rows:
   check(hashlib.sha256(content).hexdigest()==row['report_sha256'],'Native report hash')
   check(sha(folder/'OrbSearch.ex5')==row['binary_sha256'],'Native binary hash')
   p=[t['net_profit'] for t in row['trades']]
   check(abs(sum(p)-row['native']['net'])<.03,'Net reconciliation')
   check(row['native']['open_position']==0,'Open final position')
  compile_text=(folder/'compile.log').read_text(encoding='utf-16',errors='replace')
  check('0 errors, 0 warnings' in compile_text,'Compile diagnostics')
 frozen=json.loads((R/'FROZEN.json').read_text())
 selected=s['holdout-1']['parameters']
 from datetime import datetime
 started=json.loads((R/'native/holdout/owned-process.json').read_text())['started']
 check(datetime.fromisoformat(frozen['frozen_at_utc']).timestamp()<started,'Holdout ran before freeze')
 check(selected==frozen['locked']['parameters'],'Holdout different settings')
 check(all(v['parameters']==selected for k,v in s.items() if k.endswith('-1') or k.startswith(('delay-','in-sample-selected'))),'Frozen settings changed')
 check(not any(x['all_gates_pass'] for x in s.values()),'Execution-quality gate must remain failed')
 doc=(R/'Results.html').read_text(encoding='utf-8');soup=BeautifulSoup(doc,'html.parser')
 check(bool(soup.find('main')) and bool(soup.find('svg')),'Missing report/chart')
 check(not soup.find('script'),'Unexpected external/dynamic script')
 for link in soup.find_all('a',href=True):
  href=link['href']
  if not href.startswith(('http:','https:','#')):check((R/href).is_file(),'Missing report download '+href)
 for word in ['Research only','2020–2024','2025','Monte Carlo','Execution sensitivity','Raw gates','No live changes']:
  check(word in doc,'Missing disclosure '+word)
 check('nan%' not in doc.lower(),'Nonfinite displayed metric')
 export=R/'Frozen Research EA';e=json.loads((export/'manifest.json').read_text())
 for name,key in [('Research News Reversion.mq5','source_sha256'),('Research News Reversion.ex5','binary_sha256'),('Research News Reversion.set','set_sha256')]:
  check(sha(export/name)==e[key],'Export hash')
 check('!MQLInfoInteger(MQL_TESTER)' in (export/'Research News Reversion.mq5').read_text(),'EA not tester-only')
 (R/'ARTIFACT-VERIFICATION.json').write_text(json.dumps(dict(passed=True,checks=n,report_sha256=sha(R/'Results.html'),visual_browser_qa=False),indent=2))
 print(dict(passed=True,checks=n))

if __name__=='__main__':main()
