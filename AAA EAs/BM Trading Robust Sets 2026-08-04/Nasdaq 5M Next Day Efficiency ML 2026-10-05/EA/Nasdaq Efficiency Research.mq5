#property strict
#include "Forecasts.mqh"
enum ER_MODE{ER_OFF=0,ER_ML=1,ER_LAGGED_CONTROL=2};
input ER_MODE InpERMode=ER_OFF;
input string InpERTag="research";
bool ERGate(const int key,const int direction);
#define OnInit N5BaseInit
#define OnDeinit N5BaseDeinit
#define OnTick N5BaseTick
#include "Core.mqh"
#undef OnInit
#undef OnDeinit
#undef OnTick
int er_file=INVALID_HANDLE,eq_file=INVALID_HANDLE;
datetime er_last_trace=0;
double er_peak=10000,er_dd=0;
int er_candidates=0,er_blocked=0,er_missing=0;
string ERPath(string suffix){return "CalyxNasdaqER20261005\\"+InpERTag+"-"+suffix+".csv";}
int ERFind(const int key)
{
 int lo=0,hi=ArraySize(ER_dates)-1;
 while(lo<=hi){int mid=(lo+hi)/2;if(ER_dates[mid]==key)return mid;if(ER_dates[mid]<key)lo=mid+1;else hi=mid-1;}
 return -1;
}
bool ERGate(const int key,const int direction)
{
 int i=ERFind(key);bool known=i>=0;
 bool timely=known && ER_available[i]<(long)TimeCurrent()-ServerUtcOffsetSeconds();
 bool pass=InpERMode==ER_OFF || (timely && (InpERMode==ER_ML ? ER_probability[i]>=0.50 : ER_lag_allow[i]==1));
 er_candidates++;if(!pass)er_blocked++;
 if(InpERMode!=ER_OFF && !timely){er_missing++;Print("ER_FORECAST_MISSING date=",key);}
 if(er_file!=INVALID_HANDLE)FileWrite(er_file,(long)TimeCurrent(),key,direction,known ? DoubleToString(ER_probability[i],12) : "-1",known ? ER_available[i] : 0,pass ? 1 : 0,(int)InpERMode);
 return pass;
}
void ERTrace(bool force=false)
{
 double e=AccountInfoDouble(ACCOUNT_EQUITY);er_peak=MathMax(er_peak,e);if(er_peak>0)er_dd=MathMax(er_dd,100*(er_peak-e)/er_peak);
 datetime now=TimeCurrent();
 if(eq_file!=INVALID_HANDLE && (force || now-er_last_trace>=300))
 {FileWrite(eq_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(e,2));er_last_trace=now;}
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 int result=N5BaseInit();if(result!=INIT_SUCCEEDED)return result;
 FolderCreate("CalyxNasdaqER20261005",FILE_COMMON);
 er_file=FileOpen(ERPath("gates"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 eq_file=FileOpen(ERPath("equity"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(er_file==INVALID_HANDLE || eq_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(er_file,"epoch","date_key","direction","probability","available","allow","mode");
 FileWrite(eq_file,"epoch","balance","equity");ERTrace(true);
 return INIT_SUCCEEDED;
}
void OnTick(){N5BaseTick();ERTrace();}
double OnTester()
{
 ERTrace(true);
 int f=FileOpen(ERPath("deals"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE){Print("ER_EXPORT_DEALS_FAILED");return 0;}
 FileWrite(f,"deal","position_id","epoch","entry","type","volume","price","gross","commission","swap","fee","comment");
 HistorySelect(0,TimeCurrent()+86400);
 for(int k=0;k<HistoryDealsTotal();k++){
  ulong d=HistoryDealGetTicket(k);
  if(HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol)continue;
  FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),2),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),2),DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),2),DoubleToString(HistoryDealGetDouble(d,DEAL_FEE),2),HistoryDealGetString(d,DEAL_COMMENT));
 }
 FileClose(f);
 PrintFormat("ER_SUMMARY candidates=%d blocked=%d missing=%d observed_dd=%.8f",er_candidates,er_blocked,er_missing,er_dd);
 return 0;
}
void OnDeinit(const int reason){if(er_file!=INVALID_HANDLE)FileClose(er_file);if(eq_file!=INVALID_HANDLE)FileClose(eq_file);N5BaseDeinit(reason);}

