#ifndef CALYX_FIVE_RISK_SUPPORT_MQH
#define CALYX_FIVE_RISK_SUPPORT_MQH
// Allocation-only extension. Signal, stops, targets and broker volume policy are unchanged.
input int    InpPortfolioRiskMode=0; // 0=current equity percentage, 1=fixed USD target
input double InpPortfolioFixedUSD=50.0;
input long   InpPortfolioExpectedLogin=0; // 0=unbound research/default; installer binds the active account
input string InpPortfolioExpectedServer="";
input string InpPortfolioExpectedSymbol="";
input string InpPortfolioInstallNonce="";
datetime fp_last_heartbeat=0;
bool fp_binding_warning=false;
bool FP_BindingOK()
{
 bool ok=(InpPortfolioExpectedLogin==0||AccountInfoInteger(ACCOUNT_LOGIN)==InpPortfolioExpectedLogin)
   &&(InpPortfolioExpectedServer==""||AccountInfoString(ACCOUNT_SERVER)==InpPortfolioExpectedServer)
   &&(InpPortfolioExpectedSymbol==""||_Symbol==InpPortfolioExpectedSymbol)
   &&(InpPortfolioRiskMode!=1||AccountInfoString(ACCOUNT_CURRENCY)=="USD");
 if(!ok&&!fp_binding_warning){Print("FIVE PORTFOLIO: account/server/symbol/currency binding mismatch; EA will not trade this account.");fp_binding_warning=true;}
 return ok;
}
bool FP_InputsValid(const double percent)
{
 return InpPortfolioRiskMode>=0&&InpPortfolioRiskMode<=1&&MathIsValidNumber(InpPortfolioFixedUSD)
  &&InpPortfolioFixedUSD>0&&MathIsValidNumber(percent)&&percent>0&&percent<=10
  &&AccountInfoInteger(ACCOUNT_MARGIN_MODE)==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING&&FP_BindingOK();
}
double FP_RiskBudget(const double percent,const double multiplier=1.0)
{
 if(!FP_BindingOK()||multiplier<=0)return 0;
 double equity=AccountInfoDouble(ACCOUNT_EQUITY);
 double budget=(InpPortfolioRiskMode==1?InpPortfolioFixedUSD:equity*percent/100.0)*multiplier;
 if(!MathIsValidNumber(budget)||budget<=0)return 0;
 PrintFormat("FIVE_RISK mode=%d target=%.8f equity=%.8f percent=%.8f; broker rounding/minimum and gaps can exceed target",InpPortfolioRiskMode,budget,equity,percent);
 return budget;
}
void FP_Heartbeat(const long magic,const bool force=false)
{
 if(MQLInfoInteger(MQL_TESTER)||InpPortfolioInstallNonce==""||!FP_BindingOK())return;
 datetime now=TimeGMT();if(!force&&now-fp_last_heartbeat<10)return;
 int f=FileOpen("CalyxFivePortfolio-"+IntegerToString(magic)+".tsv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
 if(f==INVALID_HANDLE){Print("FIVE PORTFOLIO: unable to write initialization status.");return;}
 FileWriteString(f,IntegerToString((long)now)+"\t"+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"\t"+AccountInfoString(ACCOUNT_SERVER)+"\t"+_Symbol+"\t"+IntegerToString(magic)+"\t"+InpPortfolioInstallNonce+"\t"+IntegerToString(InpPortfolioRiskMode)+"\t"+DoubleToString(InpPortfolioFixedUSD,8)+"\n");
 FileClose(f);fp_last_heartbeat=now;
}
#endif
