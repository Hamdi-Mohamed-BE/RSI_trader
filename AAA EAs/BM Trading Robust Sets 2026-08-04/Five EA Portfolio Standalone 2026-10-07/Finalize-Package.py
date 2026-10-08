"""Refresh distribution checksums and create a relocatable ZIP, excluding local/private test files."""
from pathlib import Path
import hashlib,json,zipfile
R=Path(__file__).resolve().parent
NAMES={'five_eas_portfolio.bat','Install-FivePortfolio.ps1','Installer-Helpers.ps1','Probe-MT5.py','README.txt','Package.json','BUILD.json','TESTS.json','VALIDATION.json','TRANSACTION-TESTS.json'}
def main():
 files=[p for p in R.rglob('*') if p.is_file() and ((len(p.relative_to(R).parts)==1 and p.name in NAMES) or (p.relative_to(R).parts[0] in {'Experts','Sets'}) or (p.relative_to(R).parts[0]=='Sources' and p.suffix in {'.mq5','.mqh'}))]
 checks={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
 (R/'Checksums.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
 dest=R.parent/'Five EA Portfolio Standalone 2026-10-07.zip'
 with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files+[R/'Checksums.json']:z.write(p,R.name+'/'+p.relative_to(R).as_posix())
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None
  assert len([n for n in z.namelist() if '/Experts/' in n and n.endswith('.ex5')])==5
  assert len([n for n in z.namelist() if '/Sets/' in n and n.endswith('.set')])==5
  assert not any(x in n for n in z.namelist() for x in ('NativeTests','tester.ini','Receipt.json','__pycache__'))
 print('Created standalone ZIP:',dest,'files:',len(files)+1,'bytes:',dest.stat().st_size)
if __name__=='__main__':main()
