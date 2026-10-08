#ifndef CALYX_CURRENT14_ORB05_RISK_MQH
#define CALYX_CURRENT14_ORB05_RISK_MQH
// Allocation only. There is no FTMO phase, $50 cap or shared daily-loss governor.
input int InpPortfolioRiskMode=0; // 0=current equity percentage; 1=fixed USD
input double InpPortfolioPercent=0.5;
input double InpPortfolioFixedUSD=50.0;
input long InpPortfolioExpectedLogin=0;
input string InpPortfolioExpectedServer="";
input string InpPortfolioExpectedSymbol="";
input string InpPortfolioInstallNonce="";
datetime ur_last_heartbeat=0;
bool ur_binding_warning=false;

bool UR_BindingOK()
{
 bool ok=(InpPortfolioExpectedLogin==0||AccountInfoInteger(ACCOUNT_LOGIN)==InpPortfolioExpectedLogin)
  &&(InpPortfolioExpectedServer==""||AccountInfoString(ACCOUNT_SERVER)==InpPortfolioExpectedServer)
  &&(InpPortfolioExpectedSymbol==""||_Symbol==InpPortfolioExpectedSymbol)
  &&AccountInfoInteger(ACCOUNT_MARGIN_MODE)==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
 if(!ok&&!ur_binding_warning){Print("CURRENT14+ORB05: account/server/symbol binding changed or account is not hedging; trading stopped. Re-run setup for the new account.");ur_binding_warning=true;}
 return ok;
}

double UR_USDConversion()
{
 string currency=AccountInfoString(ACCOUNT_CURRENCY);
 if(currency=="USD")return 1.0;
 // Non-standard cent currencies require an explicit broker conversion, not a guessed factor.
 if(StringLen(currency)!=3||currency=="USC"||currency=="EUC"||currency=="GBC")return 0.0;
 for(int i=0;i<SymbolsTotal(false);i++)
 {
  string name=SymbolName(i,false);
  string base=SymbolInfoString(name,SYMBOL_CURRENCY_BASE);
  string profit=SymbolInfoString(name,SYMBOL_CURRENCY_PROFIT);
  if(!((base=="USD"&&profit==currency)||(base==currency&&profit=="USD")))continue;
  if(!SymbolSelect(name,true))continue;
  MqlTick tick={};
  if(!SymbolInfoTick(name,tick)||tick.bid<=0||tick.ask<=0||tick.ask<tick.bid)continue;
  // Never size a fresh trade using an old conversion quote.
  if(TimeCurrent()-tick.time>300)continue;
  return base=="USD"?tick.bid:1.0/tick.ask;
 }
 Print("CURRENT14+ORB05: no fresh direct USD/account-currency conversion; new entry skipped. Percentage mode is available.");
 return 0.0;
}

double UR_RiskBudget()
{
 if(!UR_BindingOK())return 0.0;
 double equity=AccountInfoDouble(ACCOUNT_EQUITY);
 double budget=InpPortfolioRiskMode==1?InpPortfolioFixedUSD*UR_USDConversion():equity*InpPortfolioPercent/100.0;
 if(!MathIsValidNumber(budget)||budget<=0||equity<=0)return 0.0;
 PrintFormat("UNIVERSAL_RISK mode=%d budget=%.8f equity=%.8f percent=%.8f currency=%s; broker minimum/rounding and costs can exceed target",InpPortfolioRiskMode,budget,equity,InpPortfolioPercent,AccountInfoString(ACCOUNT_CURRENCY));
 return budget;
}

double UR_RiskMultiplier()
{
 // All native strategy risk inputs are calibrated to 0.5% by the package.
 // This conversion makes every requested trade budget dynamic, including fixed USD.
 double equity=AccountInfoDouble(ACCOUNT_EQUITY);
 return equity>0?UR_RiskBudget()/(equity*0.005):0.0;
}

bool UR_InputsValid(const double calibration)
{
 return MathAbs(calibration-0.5)<1e-10&&InpPortfolioRiskMode>=0&&InpPortfolioRiskMode<=1
  &&MathIsValidNumber(InpPortfolioPercent)&&InpPortfolioPercent>0&&InpPortfolioPercent<=10
  &&MathIsValidNumber(InpPortfolioFixedUSD)&&InpPortfolioFixedUSD>0&&UR_BindingOK();
}

void UR_Heartbeat(const long magic,const bool force=false)
{
 if(MQLInfoInteger(MQL_TESTER)||InpPortfolioInstallNonce==""||!UR_BindingOK())return;
 datetime now=TimeGMT();if(!force&&now-ur_last_heartbeat<10)return;
 int f=FileOpen("CalyxCurrent14ORB05-"+IntegerToString(magic)+".tsv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
 if(f==INVALID_HANDLE){Print("CURRENT14+ORB05: unable to write initialization status.");return;}
 FileWriteString(f,IntegerToString((long)now)+"\t"+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"\t"+AccountInfoString(ACCOUNT_SERVER)+"\t"+_Symbol+"\t"+IntegerToString(magic)+"\t"+InpPortfolioInstallNonce+"\t"+IntegerToString(InpPortfolioRiskMode)+"\t"+DoubleToString(InpPortfolioFixedUSD,8)+"\n");
 FileClose(f);ur_last_heartbeat=now;
}
#endif
