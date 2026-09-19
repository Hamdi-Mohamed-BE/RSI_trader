import shutil
from pathlib import Path
from run_native import ROOT,TESTER
archive=ROOT/'first-pass';archive.mkdir(exist_ok=True)
for name in ['quotes.csv','quote-arrays.npz','selected.json','search-results.npz','screening-comparison.json','search-space.json']:
 p=ROOT/name
 if p.exists():
  assert not (archive/name).exists()
  p.rename(archive/name)
files=list((TESTER/'Tester').glob('Agent-*/MQL5/Files/news-clean-quotes-20260919.csv'))
assert len(files)==1
shutil.copy2(files[0],ROOT/'quotes.csv')
print('Archived first pass; installed quote-only export')
