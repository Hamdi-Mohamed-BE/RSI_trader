"""Generate a separate deployment build; never rewrite frozen research or install on MT5."""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
OLD = BASE / 'Indices Hourly EA Pipeline 2026-10-03'
CACHE = BASE.parent / 'EA store/data/evidence-cache/v1/products'
EA = ROOT / 'EA'
SETS = ROOT / 'Sets'

SIZING = r'''
double HistoricalSizedLots(const int side,const MqlTick &tick)
{
 if(InpSizingMode==0) return InpLots; // Exact frozen fixed-lot benchmark.
 double multiplier=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
 if(multiplier<=0) return 0;
 double budget=(InpSizingMode==2 ? InpFixedRiskMoney : AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0)*multiplier;
 double sample=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP));
 double tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double price=(side>0 ? tick.ask : tick.bid);
 if(!MathIsValidNumber(budget)||budget<=0||sample<=0||tickSize<=0) return 0;
 // The reference includes historical net costs expressed in index price units.
 // It is a synthetic adverse move for sizing, NOT a placed protective stop.
 double distance=MathCeil(InpHistoricalLossPoints/tickSize)*tickSize;
 double exitPrice=NormalizeDouble(price+(side>0 ? -distance : distance),_Digits);
 double projected=0;
 if(exitPrice<=0||!OrderCalcProfit(side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,_Symbol,sample,price,exitPrice,projected)||!MathIsValidNumber(projected)||projected>=0) return 0;
 double lossPerLot=-projected/sample;
 double requested=budget/lossPerLot;
 if(!MathIsValidNumber(requested)||requested<=0) return 0;
 PrintFormat("HOURLY_HISTORICAL_SIZE budget=%.2f historical_points=%.8f requested_lots=%.8f; NO SL, future loss can exceed reference",budget,InpHistoricalLossPoints,requested);
 return requested;
}
'''

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    EA.mkdir(parents=True, exist_ok=True)
    SETS.mkdir(parents=True, exist_ok=True)
    source = (OLD/'CalyxHourlyProfiles.mq5').read_text()
    assert sha(OLD/'CalyxHourlyProfiles.mq5') == '4ad21890864fcaea74d43738c8545f2d3543a6c660017556b9114988a9c1ea53'
    source = source.replace('#property version "1.00"', '#property version "1.11"')
    source = source.replace('Research/demo default; no SL/TP, fixed lots, not fixed account risk.', 'Historical-loss scenario sizing; no SL/TP, NOT a future loss cap.')
    source = source.replace('lots=",InpLots," NO SL/TP; fixed lots, not risk percent;', 'sizingMode=",InpSizingMode," historicalLossPoints=",InpHistoricalLossPoints," riskPercent=",InpRiskPercent," NO SL/TP; historical scenario, NOT a loss cap;')
    source = source.replace('#include <Trade/Trade.mqh>', '#include <Trade/Trade.mqh>\n#include "CalyxAdaptivePortfolio.mqh"')
    source = source.replace('input double InpLots=1.0;', '''input double InpLots=1.0;
input int InpSizingMode=1; // 0=frozen fixed lots, 1=balance percent, 2=fixed account cash
input double InpRiskPercent=0.5;
input double InpFixedRiskMoney=50.0;
input double InpHistoricalLossPoints=0;
input bool InpAdaptivePortfolioControls=false;''')
    source = source.replace('double lots=MathMax(lo,MathCeil((InpLots-1e-10)/step)*step);if(lots>hi){blocked++;running=false;return;}\n if(MathAbs(lots-InpLots)>1e-8)Print("HOURLY_VOLUME_ROUNDED requested=",InpLots," actual=",lots,"; no cash-risk guarantee");', '''double requested=HistoricalSizedLots(directions[ny.hour],tick);
 if(!MathIsValidNumber(requested)||requested<=0||step<=0||lo<=0||hi<lo){blocked++;running=false;return;}
 double lots=NormalizeDouble(lo+MathMax(0.0,MathFloor((requested-lo)/step+1e-10))*step,8);
 if(lots>hi){blocked++;running=false;return;}
 if(lots>requested+1e-8)Print("HOURLY_MINIMUM_OVERRIDE requested=",requested," actual=",lots,"; historical scenario budget exceeded; NO loss cap");
 else if(MathAbs(lots-requested)>1e-8)Print("HOURLY_VOLUME_ROUNDED_DOWN requested=",requested," actual=",lots,"; NO future loss cap");''')
    assert 'HistoricalSizedLots(directions[ny.hour],tick)' in source
    source = re.sub(r'\brunning\b', 'hourlyCycleBusy', source)
    source = source.replace('int OnInit(){', '''int OnInit(){
 if(InpSizingMode<0||InpSizingMode>2||!MathIsValidNumber(InpRiskPercent)||InpRiskPercent<=0||InpRiskPercent>10||!MathIsValidNumber(InpFixedRiskMoney)||InpFixedRiskMoney<=0)return INIT_PARAMETERS_INCORRECT;
 if(InpSizingMode!=0&&(!MathIsValidNumber(InpHistoricalLossPoints)||InpHistoricalLossPoints<=0))return INIT_PARAMETERS_INCORRECT;''')
    source = source.replace('void Cycle(){', SIZING+'\nvoid Cycle(){')
    target = EA/'CalyxHourlyProfiles History Sized.mq5'
    target.write_text(source, encoding='utf-8')
    shutil.copy2(BASE/'_Shared/CalyxAdaptivePortfolio.mqh', EA/'CalyxAdaptivePortfolio.mqh')
    rows = []
    for asset, slug, profile, magic in [('US30','us30-hourly-profiles',1,104103301),('US100','us100-hourly-profiles',2,104101001)]:
        ledgers = [CACHE/slug/'standard'/f'{p}.trades.json' for p in ('1y','6m')]
        trades = [t for path in ledgers for t in json.loads(path.read_text()) if t['net_profit']<0 and t['price_move']<0 and t['gross_profit']<0]
        def points(t):
            # Net loss / broker cash per index unit, including recorded costs.
            cash_per_unit = abs(t['gross_profit']/t['price_move'])
            return abs(t['net_profit'])/cash_per_unit
        worst = max(trades, key=points)
        reference = math.ceil(points(worst)*100000)/100000
        text = (OLD/f'{asset}.set').read_text().replace('InpAllowRealAccount=false', 'InpAllowRealAccount=true').replace('InpMagic=103310', f'InpMagic={magic}')
        text += f'InpSizingMode=1\nInpRiskPercent=0.5\nInpFixedRiskMoney=50.0\nInpHistoricalLossPoints={reference:.5f}\nInpAdaptivePortfolioControls=false\n'
        (SETS/f'{asset}.set').write_text(text, encoding='utf-8')
        rows.append(dict(asset=asset,slug=slug,profile=profile,magic=magic,historical_loss_points=reference,worst_trade=worst,ledger_sha256={p.name:sha(p) for p in ledgers},selected_windows=['2025-10-03 to 2026-10-03 exclusive','2026-04-03 to 2026-10-03 exclusive']))
    compiler = BASE/'_Backtests/MT5-DMC-20260811/metaeditor64.exe'
    log = ROOT/'compile.log'
    # MetaEditor uses nonzero exit codes even for clean compilation; inspect log.
    subprocess.run(f'"{compiler}" /portable /compile:"{target}" /log:"{log}"', timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    b = log.read_bytes()
    txt = b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
    assert '0 errors, 0 warnings' in txt, txt[-4000:]
    manifest = dict(version='HOURLY-HISTORY-20261004-v1.11',source_sha256=sha(target),expert_sha256=sha(target.with_suffix('.ex5')),shared_sha256=sha(EA/'CalyxAdaptivePortfolio.mqh'),original_source_sha256=sha(OLD/'CalyxHourlyProfiles.mq5'),default_percent=0.5,volume_policy='Round down to broker step; owner-authorized minimum-lot fallback may exceed scenario budget',compile_clean=True,entries=rows,not_installed_on_active_terminal=True,performance_revalidation_pending=True,notice='Closed-trade historical adverse move including recorded costs; not intratrade MAE or a guaranteed future-loss cap. No SL. Broker/currency costs and granularity can differ. Existing website figures remain original fixed-lot benchmarks, not results for this deployment build.')
    (ROOT/'RELEASE.json').write_text(json.dumps(manifest,indent=2), encoding='utf-8')
    print(json.dumps({'compile_clean':True,'references':[(r['asset'],r['historical_loss_points']) for r in rows],'active_MT5_changed':False}))

if __name__ == '__main__':
    main()
