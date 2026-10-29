"""9-EA build: put back the 8 EX5 binaries that were tested natively as v2 (MetaEditor builds are not byte-reproducible), after proving every
source file is byte-identical. Only Gold Overnight Value Area is a new compile. python restore_tested_ex5.py"""
import hashlib, json, shutil
from pathlib import Path

R = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
old = R / 'superseded/v2-8ea/package'; new = R.parent / '_00 Live profiles/Packages/FundedV1/package'
src_old = {p.name: sha(p) for p in old.iterdir() if p.suffix in ('.mq5', '.mqh')}
src_new = {p.name: sha(p) for p in new.iterdir() if p.suffix in ('.mq5', '.mqh')}
diff = [k for k in src_old if src_old[k] != src_new.get(k)]
print('source files differing:', diff); print('new source files:', sorted(set(src_new) - set(src_old)))
assert not diff, 'sources changed'
man_p = new.parent / 'PACKAGE.json'; man = json.loads(man_p.read_text(encoding='utf-8'))
for e in man['entries']:
    o = old / e['expert']
    if o.exists():
        shutil.copy2(o, new / e['expert']); e['expert_sha256'] = sha(new / e['expert'])
man['files'] = {str(p.relative_to(new)).replace('\\', '/'): sha(p) for p in new.rglob('*') if p.is_file() and p.suffix != '.log'}
man['ex5_note'] = ('The 8 original EX5 are the exact binaries tested natively as v2 (superseded/v2-8ea); only Gold Overnight Value Area was '
                   'compiled for the 9-EA build. All sources are byte-identical.')
man_p.write_text(json.dumps(man, indent=2) + '\n', encoding='utf-8')
oldm = {e['slug']: e['expert_sha256'] for e in json.loads((R / 'superseded/v2-8ea/PACKAGE.json').read_text(encoding='utf-8'))['entries']}
print('restored tested binaries:', all(e['expert_sha256'] == oldm[e['slug']] for e in man['entries'] if e['slug'] in oldm))
