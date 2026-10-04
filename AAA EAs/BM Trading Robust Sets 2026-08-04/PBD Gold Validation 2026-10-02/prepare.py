"""Copy frozen source and independent verifier; namespace runner outputs only."""
from pathlib import Path
import hashlib,shutil
p=Path(__file__).resolve().parent;old=p.parent/'PBD Profile Raw 2026-10-02'
assert hashlib.sha256((old/'EA/Main.mqh').read_bytes()).hexdigest()=='36fc9d9a910c8926c27531696037f14947dc52e7c95eda51e7513560b415f113'
(p/'EA').mkdir(exist_ok=True)
for f in ['Main.mqh','Head.mqh']:shutil.copy2(old/'EA'/f,p/'EA'/f)
for f in ['verify.py','rules.py','test_research.py']:shutil.copy2(old/f,p/f)
s=(old/'native.py').read_text()
s=s.replace('pbd-profile-raw-20261002','pbd-gold-validation-20261002')
s=s.replace("dest=TESTER/'MQL5/Experts/AAA Research/PBDProfileRaw20261002'","dest=TESTER/'MQL5/Experts/AAA Research/PBDGoldValidation20261002'")
s=s.replace('Expert=AAA Research\\\\PBDProfileRaw20261002\\\\PBDRaw','Expert=AAA Research\\\\PBDGoldValidation20261002\\\\PBDRaw')
s=s.replace("tag='pbd-'","tag='goldval-'")
# Export COMMON directory and embedded magic stay identical; unique tags prevent collisions.
(p/'native.py').write_text(s,encoding='utf-8')
