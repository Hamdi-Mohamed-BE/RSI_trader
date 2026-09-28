"""Execute the no-order formatter harness in the isolated tester only."""
from build import ROOT, BASE, TESTER, compile_source
import gzip, json, re, shutil, subprocess, time

def main():
    probe=subprocess.run(['powershell','-NoProfile','-Command',
        'Get-CimInstance Win32_Process -Filter "Name=\'terminal64.exe\'" | Select-Object -ExpandProperty ExecutablePath'],
        capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert probe.returncode==0 and str(TESTER).lower() not in probe.stdout.lower(),'Isolated terminal occupied'
    net=subprocess.check_output(['netstat','-ano','-p','TCP'],text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert not any(':3000 ' in line and 'LISTENING' in line for line in net.splitlines()),'Tester port occupied'
    compile_source(ROOT/'CommentProbe.mq5','probe-compile')
    dest=TESTER/'MQL5/Experts/AAA Research/ORB Comments 20260928';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'CommentProbe.ex5',dest/'CommentProbe.ex5')
    out=ROOT/'native';out.mkdir(exist_ok=True)
    # Retain the existing private isolated-research connection; never print it.
    header=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
    ini=out/'probe.ini'
    ini.write_text(header+'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ORB Comments 20260928\\CommentProbe
Symbol=USTEC
Period=M15
Deposit=10000
Currency=USD
Leverage=1:100
Model=4
ExecutionMode=150
Optimization=0
FromDate=2026.09.21
ToDate=2026.09.22
Report=reports\\orb-comments-20260928\\probe.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    (TESTER/'reports/orb-comments-20260928').mkdir(parents=True,exist_ok=True)
    def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
    offsets={p:p.stat().st_size for p in logs()};started=time.time()
    proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
    try: proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=30);raise
    journal=''
    for p in logs():
        if p.stat().st_mtime<started-2:continue
        with p.open('rb') as handle:
            handle.seek(offsets.get(p,0));journal+='\n'+handle.read().decode('utf-16-le',errors='replace')
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert 'ORB_LABEL_TESTS_PASS=13' in journal and 'ORB_LABEL_FAIL' not in journal,'Native comment test failed'
    assert not re.search('initialization failed|critical error|access violation',journal,re.I)
    rows=sorted(set(re.findall(r'ORB_LABEL_OK[^\r\n]+',journal)))
    assert len(rows)==13,rows
    result=dict(passed=True,checks=13,orders_submitted=0,scope='isolated native MT5 formatter harness',labels=rows)
    (ROOT/'NATIVE-CHECK.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
