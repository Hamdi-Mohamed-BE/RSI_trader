"""Comment-only release audit/compiler. Does not install or restart a live terminal."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO = BASE.parents[1]
BEFORE = '53d4a171db59371248810cc3560a1dc185e6e1e4'
TESTER = BASE/'_Backtests/MT5-DMC-20260811'
SOURCES = [
    'ORB Volume Data EA/ORB Volume Data EA.mq5',
    'US100 Selective ORB Research 2026-08-21/EA/US100 Selective ORB Retest EA.mq5',
    'Ava Futures Portfolio Research 2026-09-09/EA/ORB Volume Data/ORB Volume Data EA.mq5',
    'Ava Futures Portfolio Research 2026-09-09/EA/Selective ORB/US100 Selective ORB Retest EA.mq5',
    'active EAs with code and saves and charts/02 ORB Volume Profile/Source Code/ORB Volume Data EA.mq5',
]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    raw=path.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n','\n')
def baseline(path):
    rel=path.relative_to(REPO).as_posix()
    return subprocess.check_output(['git','show',f'{BEFORE}:{rel}'],cwd=REPO)
def published(path):
    if path.parent.name=='Source Code': return path.parent.parent/'Compiled EA'/path.with_suffix('.ex5').name
    return path.with_suffix('.ex5')
def assert_comment_only(path):
    old=baseline(path).decode('utf-8-sig').replace('\r\n','\n')
    current=read(path)
    current,n=re.subn(r'^#include "[^"\n]*CalyxORBComments\.mqh"\n','',current,flags=re.M)
    assert n==1,path
    selective='Selective' in path.name
    previous=('   string note=StringFormat("US100 OR30 RV %.2f",g_opening_relative_volume);' if selective else
              '   string comment=StringFormat("ORB RV %.2f BV %.2f",g_opening_relative_volume,BarRelativeVolume(signal));')
    current,n=re.subn(r'^   string (?:note|comment)=CalyxORBTradeComment\([^;]+;',lambda _:previous,current,flags=re.M)
    assert n==1 and current==old, f'Non-comment source change: {path}'
    return hashlib.sha256(baseline(path)).hexdigest()
def compile_source(path, name):
    log=ROOT/(name+'.log'); began=time.time()
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{path}" /log:"{log}"',
                   creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
    summary=read(log)
    assert '0 errors, 0 warnings' in summary, '\n'.join(x for x in summary.splitlines() if 'error' in x or 'warning' in x)
    assert path.with_suffix('.ex5').stat().st_mtime>=began-2,'No fresh binary'
    return '0 errors, 0 warnings'
def main():
    records=[]
    for i,rel in enumerate(SOURCES):
        source=BASE/rel; target=published(source)
        old_source_sha=assert_comment_only(source)
        backup=ROOT/'before'/f'{i}.ex5'; backup.parent.mkdir(exist_ok=True)
        if not backup.exists():
            assert hashlib.sha256(baseline(target)).hexdigest()==sha(target),'Unexpected pre-release binary'
            shutil.copy2(target,backup)
        result=compile_source(source,f'compile-{i}')
        if target!=source.with_suffix('.ex5'): shutil.copy2(source.with_suffix('.ex5'),target)
        records.append(dict(source=rel,source_before_sha=old_source_sha,source_sha=sha(source),
                            expert=target.relative_to(BASE).as_posix(),expert_before_sha=sha(backup),
                            expert_sha=sha(target),compile=result,logic_unchanged=True))
        print('COMPILED '+rel,flush=True)
    helper=BASE/'_Shared/CalyxORBComments.mqh'
    release=dict(version='ORB-COMMENTS-20260928',baseline_commit=BEFORE,comment_only=True,
                 helper='_Shared/CalyxORBComments.mqh',helper_sha=sha(helper),builds=records)
    (ROOT/'RELEASE.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
    print('PASS: all five EA sources differ only in comment construction.',flush=True)
if __name__=='__main__':main()
