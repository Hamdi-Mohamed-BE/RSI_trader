from pathlib import Path
import configparser,json,shutil,subprocess,time
import run_research as g
ROOT=g.ROOT;TESTER=g.TESTER;NAME='XAU Capped Recovery Diagnostics'
OPTIONS=[('capped-double',{'InpMultiplier':2}),('original-exit',{'InpOriginalExit':True}),('loss30',{'InpBasketLoss':30}),('daily30',{'InpDailyProfit':30}),('daily-none',{'InpDailyProfit':0})]

def main():
    selected=json.loads((ROOT/'selection.json').read_text())['selected']['parameters']
    assert selected==g.BASE,'Diagnostic wrapper currently encodes the selected baseline preset only'
    dest=TESTER/'MQL5'/'Experts'/g.EXPERT
    for name in (NAME+'.mq5','Optimization Core.mqh'):shutil.copy2(ROOT/'EA'/name,dest/name)
    expected=g.SOURCE.read_text().replace('input ','').replace('int OnInit()','int BaseInit()').strip()
    assert (ROOT/'EA'/'Optimization Core.mqh').read_text().strip()==expected
    log=ROOT/'diagnostics-compile.log'
    subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{dest/(NAME+".mq5")}" /log:"{log}"',cwd=TESTER,startupinfo=g.native.hidden(),timeout=120)
    content=log.read_text(encoding='utf-16',errors='replace');assert '0 errors, 0 warnings' in content,content
    shutil.copy2(dest/(NAME+'.ex5'),ROOT/'EA'/(NAME+'.ex5'))
    out=[]
    for index,period in enumerate(('dev','val')):
        magic=94000000+index*1000000;start_date,end_date=g.WINDOWS[period]
        settings=TESTER/'MQL5'/'Profiles'/'Tester'/f'capped-diag-{period}.set'
        settings.write_text(f'InpResearchCase=0||0||1||4||Y\nInpBatchMagic={magic}\n',encoding='utf-8')
        ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16');common=dict(ref['Common'])
        text='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())+'\n[Experts]\nAllowLiveTrading=0\nEnabled=0\nAllowDllImport=0\nAccount=1\nProfile=1\n\n[Charts]\nProfileLast=CappedResearchOnly\n\n[Tester]\n'
        text+=f'Expert={g.EXPERT}\\{NAME}\nExpertParameters={settings.name}\nSymbol=XAUUSD\nPeriod=M1\nLogin={common["login"]}\nDeposit=3000\nCurrency=USD\nLeverage=1:2000\nModel=4\nExecutionMode=1\nOptimization=1\nOptimizationCriterion=6\n'
        text+=f'FromDate={start_date}\nToDate={end_date}\nForwardMode=0\nReport=reports\\capped-grid\\diagnostics-{period}.xml\nReplaceReport=1\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n'
        cfg=TESTER/'backtest-configs'/'capped-grid'/f'diagnostics-{period}.ini';cfg.write_text(text,encoding='utf-16')
        started=time.time();sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')}
        print('START native five-case diagnostic batch '+period,flush=True)
        proc=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{cfg.relative_to(TESTER)}'],cwd=TESTER,startupinfo=g.native.hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:proc.wait(timeout=1800)
        except subprocess.TimeoutExpired:proc.kill();raise RuntimeError('Diagnostic batch timeout')
        report=TESTER/'reports'/'capped-grid'/f'diagnostics-{period}.xml'
        assert report.exists() and report.stat().st_mtime>started-2
        shutil.copy2(report,ROOT/'Backtest Reports'/report.name)
        logtext=''
        for p in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
            if p.stat().st_mtime<started-2:continue
            with p.open('rb') as f:f.seek(sizes.get(p,0));logtext+=f.read().decode('utf-16-le',errors='replace')
        for case,(name,changes) in enumerate(OPTIONS):
            tag=f'{name}-{period}-d1';pars={**selected,**changes}
            files=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/CappedGrid-{magic+case}-*.csv') if p.stat().st_mtime>started-2]
            assert len(files)==4,(period,case,'incomplete audit',len(files))
            for p in files:shutil.copy2(p,ROOT/'Audit'/(tag+p.name.split(str(magic+case),1)[1]))
            (ROOT/'Audit'/f'{tag}-journal.log').write_text(logtext,encoding='utf-8')
            out.append(g.analyze(tag,g.WINDOWS[period],pars,1,optimization=True))
    g.save(ROOT/'diagnostics.json',out)

if __name__=='__main__':main()
