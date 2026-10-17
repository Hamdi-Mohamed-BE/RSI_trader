"""Seal approved inputs/code before outcomes; no simulation or performance selection."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 assert not (R/'OUTCOMES.json').exists()
 names=['PLAN.json','INPUTS.json','SOURCE-COVERAGE.json','prepare.py','freeze.py']
 names += [n for n in ('run.py','statistics.py') if (R/n).exists()]
 sources=json.loads((R/'SOURCE-COVERAGE.json').read_text())['source_hashes']
 assert all(sha(p)==v for p,v in sources.items())
 f=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),no_outcomes_computed=True,files={str(R/n):sha(R/n) for n in names},source_files=sources)
 (R/'FROZEN.json').write_text(json.dumps(f,indent=2)+'\n',encoding='utf-8')
 print(sha(R/'FROZEN.json'))
if __name__=='__main__':main()
