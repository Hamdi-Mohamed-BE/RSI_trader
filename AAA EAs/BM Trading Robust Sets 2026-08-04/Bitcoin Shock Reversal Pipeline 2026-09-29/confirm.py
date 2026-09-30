"""Native confirmation of unchanged Bitcoin raw rules; no live MT5 API."""
from pathlib import Path
import hashlib
import importlib.util
import json
import msvcrt
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'Market Style Bots Raw 2026-09-29'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    build=json.loads((SOURCE/'BUILD.json').read_text())
    for name in list(build)+['BUILD.json','compile.log']:
        dest=ROOT/name
        if not dest.exists():shutil.copy2(SOURCE/name,dest)
        assert sha(dest)==sha(SOURCE/name)
    assert all(sha(SOURCE/name)==expected for name,expected in build.items())
    spec=importlib.util.spec_from_file_location('frozen_native_runner',SOURCE/'run.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    runner.ROOT=ROOT
    assert '0 errors, 0 warnings' in runner.read(ROOT/'compile.log')
    native_popen=subprocess.Popen
    def hidden_popen(*args,**kwargs):
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        kwargs.setdefault('startupinfo',startup)
        return native_popen(*args,**kwargs)
    runner.subprocess.Popen=hidden_popen
    provenance=dict(source_root=str(SOURCE),source_runner_sha256=sha(SOURCE/'run.py'),
        protocol_sha256=sha(ROOT/'PROTOCOL.md'),wrapper_sha256=sha(Path(__file__)),original_build=build,
        mode='unchanged_raw_confirmation_only',gold_modified=False,nasdaq_modified=False)
    runner.save(ROOT/'PROVENANCE.json',provenance)
    bot=next(b for b in runner.CFG['bots'] if b['name']=='bitcoin-reversal')
    with (SOURCE/'tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        for window in ['3y','5y']:
            for control in [False,True]:runner.case(bot,window,4,control)
    runner.status('COMPLETE Bitcoin unchanged raw confirmation')

if __name__=='__main__':main()
