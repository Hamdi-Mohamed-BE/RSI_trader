"""Native MT5 full-search batch; per-case ledgers retained by local tester agents."""
from pathlib import Path
import configparser,hashlib,json,shutil,subprocess,time
import run_research as g

ROOT=g.ROOT;TESTER=g.TESTER;NAME='XAU Capped Recovery Batch'
def prepare():
    dest=TESTER/'MQL5'/'Experts'/g.EXPERT
    for name in ('Optimization Core.mqh',NAME+'.mq5'):shutil.copy2(ROOT/'EA'/name,dest/name)
    # Verify the batch core is a mechanical copy, not a different strategy.
    expected=g.SOURCE.read_text().replace('input ','').replace('int OnInit()','int BaseInit()').strip()
    assert (ROOT/'EA'/'Optimization Core.mqh').read_text().strip()==expected
    log=ROOT/'batch-compile.log'
    subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{dest/(NAME+".mq5")}" /log:"{log}"',cwd=TESTER,startupinfo=g.native.hidden(),timeout=120)
    content=log.read_text(encoding='utf-16',errors='replace');assert '0 errors, 0 warnings' in content,content
    shutil.copy2(dest/(NAME+'.ex5'),ROOT/'EA'/(NAME+'.ex5'))

def main():
    prepare();magic=92000000
    settings=TESTER/'MQL5'/'Profiles'/'Tester'/'capped-batch-dev.set'
    settings.write_text(f'InpResearchCase=0||0||1||11||Y\nInpBatchMagic={magic}\n',encoding='utf-8')
    ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16');common=dict(ref['Common'])
    text='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())+'\n[Experts]\nAllowLiveTrading=0\nEnabled=0\nAllowDllImport=0\nAccount=1\nProfile=1\n\n[Charts]\nProfileLast=CappedResearchOnly\n\n[Tester]\n'
    text+=f'Expert={g.EXPERT}\\{NAME}\nExpertParameters={settings.name}\nSymbol=XAUUSD\nPeriod=M1\nLogin={common["login"]}\nDeposit=3000\nCurrency=USD\nLeverage=1:2000\nModel=4\nExecutionMode=1\nOptimization=1\nOptimizationCriterion=6\n'
    text+='FromDate=2021.09.05\nToDate=2023.09.05\nForwardMode=0\nReport=reports\\capped-grid\\development-batch.xml\nReplaceReport=1\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n'
    cfg=TESTER/'backtest-configs'/'capped-grid'/'development-batch.ini';cfg.write_text(text,encoding='utf-16')
    start=time.time();sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')}
    print('START native 12-case development batch',flush=True)
    proc=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{cfg.relative_to(TESTER)}'],cwd=TESTER,startupinfo=g.native.hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:proc.wait(timeout=2400)
    except subprocess.TimeoutExpired:proc.kill();raise RuntimeError('Batch timeout')
    report=TESTER/'reports'/'capped-grid'/'development-batch.xml'
    assert report.exists() and report.stat().st_mtime>start-2,'No fresh native optimization report'
    shutil.copy2(report,ROOT/'Backtest Reports'/report.name)
    log=''
    for p in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if p.stat().st_mtime<start-2:continue
        with p.open('rb') as f:f.seek(sizes.get(p,0));log+=f.read().decode('utf-16-le',errors='replace')
    dev=[]
    for case in range(12):
        spacing=(10,20,30,'atr')[case//3];profit=(10,20,30)[case%3]
        label=f'g{spacing}-p{profit}';tag=label+'-dev-d1'
        pars={**g.BASE,'InpStep':10 if spacing=='atr' else spacing,'InpATRStep':spacing=='atr','InpBasketProfit':profit}
        files=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/CappedGrid-{magic+case}-*.csv') if p.stat().st_mtime>start-2]
        assert len(files)==4,(case,'incomplete optimization audit',len(files))
        for p in files:shutil.copy2(p,ROOT/'Audit'/(tag+p.name.split(str(magic+case),1)[1]))
        (ROOT/'Audit'/f'{tag}-journal.log').write_text(log,encoding='utf-8')
        dev.append(g.analyze(tag,g.WINDOWS['dev'],pars,1,optimization=True))
    g.save(ROOT/'development.json',dev)
    top=sorted(dev,key=lambda r:g.rank(r,30),reverse=True)[:3]
    val=[g.run(r['tag'].split('-dev-')[0],'val',r['parameters']) for r in top]
    chosen=max(val,key=lambda r:g.rank(r,20))
    g.save(ROOT/'selection.json',{'development':dev,'validation':val,'selected':chosen,'eligible_on_validation':g.rank(chosen,20)[0],
             'frozen_before_later_test':True,'ranking':'positive eligible first; net profit / (1 + equity DD dollars)',
             'batch_core_sha256':hashlib.sha256((ROOT/'EA'/'Optimization Core.mqh').read_bytes()).hexdigest()})

if __name__=='__main__':main()
