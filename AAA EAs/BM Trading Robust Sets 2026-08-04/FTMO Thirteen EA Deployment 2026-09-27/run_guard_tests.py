"""Run MOCK-only MQL tests in the existing isolated tester, never the active terminal."""
from pathlib import Path
import gzip,json,re,shutil,subprocess,time
from build_package import ROOT,TESTER,read
def main():
    src=ROOT/"GuardTests.mq5";log=ROOT/"GuardTests.log"
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',
                   timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
    report=read(log)
    assert "0 errors, 0 warnings" in report,"\n".join(x for x in report.splitlines() if "error" in x or "warning" in x)
    # Refuse to share the research terminal with another job.
    snapshot=subprocess.check_output(["powershell.exe","-NoProfile","-Command",
        "Get-CimInstance Win32_Process | Where-Object Name -eq 'terminal64.exe' | Select-Object -ExpandProperty ExecutablePath"],
        text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert str(TESTER/"terminal64.exe").lower() not in snapshot.lower(),"Isolated tester busy"
    dest=TESTER/"MQL5/Experts/AAA Research/FTMO13-GuardTests.ex5"
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src.with_suffix(".ex5"),dest)
    settings=TESTER/"MQL5/Profiles/Tester/ftmo13-guardtests.set"
    settings.write_text("FTMOExpectedLogin=123456\nFTMOExpectedServer=FTMO.UnitTest\nFTMOExpectedSymbol=XAUUSD\nFTMOPhase=1\n",encoding="utf-8")
    ini=ROOT/"guardtests.ini"
    ini.write_text("""[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\FTMO13-GuardTests
ExpertParameters=ftmo13-guardtests.set
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:30
Model=1
Optimization=0
FromDate=2026.09.21
ToDate=2026.09.22
Report=reports\\ftmo13-guardtests.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
""",encoding="utf-8-sig")
    logs=lambda:list((TESTER/"Tester").glob("Agent-*/logs/*.log"))+list((TESTER/"logs").glob("*.log"))
    offsets={p:p.stat().st_size for p in logs()};began=time.time()
    proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',
                          cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
    # Caller polls this process; no live/normal terminal shutdown.
    try:proc.wait(timeout=180)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=20);raise
    journal=""
    for p in logs():
        if p.stat().st_mtime<began-2:continue
        with p.open("rb") as f:
            f.seek(offsets.get(p,0));journal+=f.read().decode("utf-16-le",errors="replace")+"\n"
    (ROOT/"GUARD_TEST_JOURNAL.txt.gz").write_bytes(gzip.compress(journal.encode(),mtime=0))
    matches=re.findall(r"FTMO13 GUARD TESTS: (\d+) checks, (\d+) failures",journal)
    assert matches, journal[-5000:]
    assert all(int(f)==0 for n,f in matches),"\n".join(x for x in journal.splitlines() if "GUARD FAIL" in x)
    result=dict(native_checks=int(matches[-1][0]),failures=0,mock_orders_only=True,active_account_untouched=True)
    (ROOT/"GUARD_TESTS.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))
if __name__=="__main__":main()
