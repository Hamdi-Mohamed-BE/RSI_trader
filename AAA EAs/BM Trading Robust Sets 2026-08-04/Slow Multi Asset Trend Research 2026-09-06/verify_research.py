"""Fail-closed evidence verification for Step 3."""
from pathlib import Path
import hashlib,json
import pandas as pd

ROOT=Path(__file__).resolve().parent
SYMBOLS=('XAUUSD','XAGUSD','BTCUSD','ETHUSD','USTEC','US30','EURUSD','GBPJPY')

def check(condition,message,lines):
    if not condition:raise AssertionError(message)
    lines.append('PASS: '+message)

def main():
    lines=[]
    compile_log=(ROOT/'EA'/'compile.log').read_text()
    check('0 errors, 0 warnings' in compile_log,'EA compiles with zero errors and zero warnings',lines)
    check((ROOT/'EA'/'Calyx Slow Trend EA.ex5').exists(),'compiled EX5 is present',lines)
    source=(ROOT/'EA'/'Calyx Slow Trend EA.mq5').read_text()
    check('InpTesterOnly' in source and 'MQL_TESTER' in source,'EA has a tester-only live-chart guard',lines)
    check('MathAbs(InpRiskPercent-1.0)' in source,'EA hard-rejects risk values other than 1%',lines)
    screen=pd.read_csv(ROOT/'all-screen-results.csv')
    check(len(screen)==1696,'all 1,696 recorded screen evaluations are present',lines)
    check(set(screen.symbol)==set(SYMBOLS),'all eight requested assets are in the screen',lines)
    choices=json.loads((ROOT/'selection-lock.json').read_text())
    check(set(choices)==set(SYMBOLS),'one frozen configuration exists for every asset',lines)
    for symbol in SYMBOLS:
        for label,stage,model in [('baseline','test',0),('selected','test',0),('selected','full',1)]:
            folder=ROOT/'Native'/f'{symbol.lower()}-{label}-{stage}-model{model}';result=folder/'result.json';report=folder/f'{symbol.lower()}-{label}-{stage}-model{model}.htm'
            check(result.exists() and report.exists(),f'{symbol} {label} {stage} native result and report exist',lines)
            row=json.loads(result.read_text());check(row['history_quality_pct']>=98,f'{symbol} {label} {stage} history quality is at least 98%',lines)
            tradefile=folder/'trades.json';audit=json.loads(tradefile.read_text());check(len(audit)==row['trades'],f'{symbol} {label} {stage} trade ledger count reconciles',lines)
            check(abs(sum(t['net'] for t in audit)-row['net_profit'])<.06,f'{symbol} {label} {stage} trade P/L reconciles to MT5',lines)
    wf=json.loads((ROOT/'walk-forward.json').read_text());check(all(len(wf[s]['folds'])==4 for s in SYMBOLS),'32 rolling walk-forward folds are present',lines)
    summary=json.loads((ROOT/'summary.json').read_text());check(summary['risk_percent']==1.0,'primary evidence uses 1% risk',lines)
    portfolio=json.loads((ROOT/'portfolio-summary.json').read_text());check(portfolio['monte_carlo']['paths']==10000,'portfolio Monte Carlo contains 10,000 paths',lines)
    for name in ('native-locked-summary.png','native-locked-equity-curves.png','walk-forward-heatmap.png','candidate-portfolio.png','candidate-monte-carlo.png','all-configurations.png'):
        p=ROOT/'Charts'/name;check(p.exists() and p.stat().st_size>10000,f'chart {name} is rendered',lines)
    check((ROOT/'REPORT.md').exists() and (ROOT/'REPORT.md').stat().st_size>5000,'full Markdown report is present',lines)
    digest=hashlib.sha256((ROOT/'selection-lock.json').read_bytes()).hexdigest();lines.append('SELECTION SHA256: '+digest)
    lines.append('VERIFIED: Step 3 research evidence is internally complete. This does not make it predictive or authorize production deployment.')
    (ROOT/'VERIFICATION.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines))

if __name__=='__main__':main()
