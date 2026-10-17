"""Freeze current three-source native shared account; no production writes or live API."""
from pathlib import Path
from datetime import datetime, timezone
import copy, hashlib, importlib.util, json, re, shutil
R=Path(__file__).resolve().parent; B=R.parent
PRIOR=B/'Top10 EA Two Month Backtest 2026-10-16'
spec=importlib.util.spec_from_file_location('frozen_shared_namespacing',B/'Five EA Shared Portfolio 2026-10-07/build.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
SLUGS=[('N5','nasdaq-5m-candle-momentum',5),('RV','xau-rsi-vwap',16385),('E3','ema3',16388)]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def freeze_inputs(source,values):
    declared={}
    def convert(m):
        typ,name,default=m.groups();value=values.get(name,default.strip());declared[name]=value
        if typ=='string' and not value.startswith('"'):value=json.dumps(value)
        elif typ.startswith('ENUM_'):value='('+typ+')'+value
        return ('bool ' if name=='InpRequireDIAgreement' else 'const '+typ+' ')+name+'='+value+';'
    out=re.sub(r'\binput\s+(\w+)\s+(\w+)\s*=\s*([^;]+);',convert,source)
    assert set(values)<=set(declared),set(values)-set(declared)
    return out,declared
def main():
    assert not (R/'RUN_STATUS.json').exists(),'Do not prepare after outcomes begin'
    prior=json.loads((PRIOR/'PLAN.json').read_text(encoding='utf-8-sig'))
    rows=[];chunks=['#property strict\n#property version "1.00"\n#include <Trade/Trade.mqh>\n#include "../_Shared/CalyxAdaptivePortfolio.mqh"\n#include "PortfolioHarness.mqh"\n']
    for index,(key,slug,tf) in enumerate(SLUGS,1):
        row=copy.deepcopy(next(x for x in prior['cases'] if x['slug']==slug))
        assert all(sha(path)==digest for path,digest in row['production_hashes'].items())
        values=row['input_settings'];values.setdefault('InpAdaptivePortfolioControls','false')
        assert float(values['InpRiskPercent'])==1 and values['InpAdaptivePortfolioControls']=='false'
        row['prior_current_inputs']=copy.deepcopy(values)
        if key=='N5':values['InpRequireDIAgreement']='false'
        files={};source=old.expand(Path(row['source']),files);source,declared=freeze_inputs(source,values)
        names=old.own_names(source)|set(declared)
        source=old.rename(source,names,key,row['symbol'],tf)
        # Trade core unchanged; override only virtual order admission for account policy/margin receipt.
        source=re.sub(r'\bCTrade\b','CPortfolioTrade',source)
        assert 'EventSetTimer' not in old.mask(source) and 'OnTimer(' not in old.mask(source)
        chunks.append(source)
        row.update(index=index,key=key,timeframe=tf,inputs=declared,dependencies=files,namespaced_identifiers=sorted(names))
        snap=R/'snapshots'/slug;snap.mkdir(parents=True,exist_ok=True)
        shutil.copy2(row['expert'],snap/'production.ex5');shutil.copy2(row['preset'],snap/'production.set')
        save(snap/'inputs.json',values);rows.append(row)
    chunks.append('''
void Pump()
{
 if(insidePump)return;insidePump=true;Observe();LiquidateFailure();
 if(InpTradingFromEpoch>0 && TimeCurrent()<InpTradingFromEpoch){insidePump=false;return;}
 if(InpChallenge && officialStatus!=0){insidePump=false;return;}
 bool nq=Fresh("USTEC",seenUSTEC),gold=Fresh("XAUUSD",seenGold);
 if(nq && Active(1)){N5_OnTick();Observe();RefreshLedger();Observe();LiquidateFailure();}
 if(!(InpChallenge && officialStatus!=0) && gold && Active(2)){RV_OnTick();Observe();RefreshLedger();Observe();LiquidateFailure();}
 if(!(InpChallenge && officialStatus!=0) && gold && Active(3)){E3_OnTick();Observe();RefreshLedger();Observe();LiquidateFailure();}
 Observe();LiquidateFailure();insidePump=false;
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("TESTER ONLY: live initialization refused");return INIT_FAILED;}
 if(InpCase<0 || InpCase>3 || InpPhase<1 || InpPhase>2 || InpTag=="" || AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING || AccountInfoString(ACCOUNT_CURRENCY)!="USD")return INIT_PARAMETERS_INCORRECT;
 if(!SymbolSelect("USTEC",true) || !SymbolSelect("XAUUSD",true) || !OpenAudit())return INIT_FAILED;
 N5_InpRequireDIAgreement=InpNasdaqDI;
 if(Active(1) && N5_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(2) && RV_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(3) && E3_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 EventSetTimer(1);Print("FTMO3_INIT tag=",InpTag," case=",InpCase," DI=",InpNasdaqDI," challenge=",InpChallenge," phase=",InpPhase," risk=1% shared account; conservative gross notional/15 margin");return INIT_SUCCEEDED;
}
void OnTick(){Pump();}
void OnTimer(){Pump();}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
 if(trans.type==TRADE_TRANSACTION_DEAL_ADD)
 {
  if(trans.deal>0 && HistoryDealSelect(trans.deal) && StringFind(HistoryDealGetString(trans.deal,DEAL_COMMENT),"end of test")>=0){forcedFinalization=true;return;}
  Observe();RefreshLedger(true);Observe();
 }
}
void OnDeinit(const int reason)
{
 EventKillTimer();if(Active(1))N5_OnDeinit(reason);if(Active(2))RV_OnDeinit(reason);
 if(auditFile!=INVALID_HANDLE)FileClose(auditFile);if(eventFile!=INVALID_HANDLE)FileClose(eventFile);if(admitFile!=INVALID_HANDLE)FileClose(admitFile);if(dayFile!=INVALID_HANDLE)FileClose(dayFile);if(contractFile!=INVALID_HANDLE)FileClose(contractFile);
}
double OnTester(){FinishAudit();return 0;}
''')
    (R/'SharedPortfolio.mq5').write_text('\n'.join(chunks),encoding='utf-8')
    direct_files={};direct=old.expand(Path(rows[0]['source']),direct_files)
    direct,declared=freeze_inputs(direct,rows[0]['input_settings'])
    direct=old.rename(direct,{'OnInit','OnTick','OnDeinit'},'Direct','USTEC',5)
    (R/'NasdaqDirect.mq5').write_text('#property strict\n#include <Trade/Trade.mqh>\n#include "../_Shared/CalyxAdaptivePortfolio.mqh"\n#include "DirectAudit.mqh"\n'+direct+'''
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;if(!DirectAuditInit())return INIT_FAILED;return Direct_OnInit();}
void OnTick(){Direct_OnTick();DirectObserve();}
void OnDeinit(const int reason){Direct_OnDeinit(reason);}
double OnTester(){DirectFinish();return 0;}
''',encoding='utf-8')
    config=dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(),start='2026-08-16',end_exclusive='2026-10-16',deposit=10000,risk_percent=1,model=4,delay_ms=150,native_leverage=15,entries=rows,primary_symbol='USTEC',dispatch='Primary USTEC ticks + 1-second timer; latest new secondary quote; deterministic N5 then RV then E3. Not every secondary historical tick.',account_policy=dict(daily_loss=500,static_floor=9000,challenge_target=11000,verification_target=10500,minimum_prague_entry_days=4,reset_timezone='Europe/Prague',breach='equity strictly below floor; permanent failure; challenge liquidation after observed breach; no reset',target='naturally flat only before OnTester; no target liquidation',phase2='Fresh $10k from next Prague calendar day, model handover assumption, only if Phase1 passed',margin='No resize; reject new entry when gross open + pending + proposed USD notional / 15 exceeds current equity. No additional percent buffer.'),production_changed=False,optimization=False,live_changes=False)
    save(R/'CONFIG.json',config)
    cases=[dict(tag='noDI-shared-diagnostic',index=0,di=False,challenge=False,phase=1),dict(tag='DIon-shared-control',index=0,di=True,challenge=False,phase=1),dict(tag='noDI-challenge',index=0,di=False,challenge=True,phase=1)]
    cases += [dict(tag=key+'-alone',index=i,di=False,challenge=False,phase=1) for i,(key,slug,tf) in enumerate(SLUGS,1)]
    cases += [dict(tag='N5-direct-parity',index=1,di=False,challenge=False,phase=1,direct=True)]
    plan=dict(config=config,cases=cases,conditional_case='If Challenge passes naturally, run fresh Phase2 from next Prague day with same rules through fixed Oct16 boundary.',no_selection=True,whole_position_accounting=True,forced_boundary_closures_separate=True,official_sources=['https://ftmo.com/en/trading-objectives/','https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/','https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/'],limitations=['Exness historical quotes/fees and broker contract model, not actual FTMO execution.','Native source-compiled namespaced adapter, not proof of byte-identical production EX5.','Secondary symbol latest-quote dispatch and FTMO equity observer are sampled at primary ticks plus one-second timer.','61-day retrospective path cannot estimate funded pass probability or future median pass days.','Existing module broker lot rounding is retained; nominal1% is not a maximum realized loss.'])
    save(R/'PLAN.json',plan)
    files=[R/x for x in ('build.py','run.py','PortfolioHarness.mqh','DirectAudit.mqh','SharedPortfolio.mq5','NasdaqDirect.mq5','CONFIG.json','PLAN.json')]
    files += [B/'Five EA Shared Portfolio 2026-10-07/build.py',B/'FTMO Exit Management Research 2026-09-27/run.py',PRIOR/'PLAN.json']
    save(R/'FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),files={str(p):sha(p) for p in files},production_hashes={p:h for row in rows for p,h in row['production_hashes'].items()},no_results_seen=True))
    print(json.dumps(dict(entries=[r['slug'] for r in rows],cases=cases,freeze=sha(R/'FROZEN.json')),indent=2))
if __name__=='__main__':main()
