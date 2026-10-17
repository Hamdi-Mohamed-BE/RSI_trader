double C[][23]={
{15.0,32769.0,0.25,0.1,0.0,0.0,1.5,0.0,1.0,1.0,0.0,2.0,0.0,0.0,0.0,20.0,1.0,480.0,1.0,0.0,1.0,12.0,26.0}
};
input int InpCase=0;input int InpBot=6;input string InpTag="";input double InpRiskPct=1;
#define OnInit BaseInit
#define OnTick BaseTick
#define OnDeinit BaseDeinit
#include "Logic.mqh"
#undef OnInit
#undef OnTick
#undef OnDeinit
// Tester-only, read-only instrumentation. No order placement or modification.
string InpRR05AuditTag="";
int rr05_equity_file=INVALID_HANDLE;
datetime rr05_last_trace=0;
string RR05Path(const string suffix){return "CalyxGannPipeline20261009\\"+InpRR05AuditTag+"-"+suffix+".csv";}
bool RR05AuditInit()
{
 if(!MQLInfoInteger(MQL_TESTER) || InpRR05AuditTag=="")return false;
 FolderCreate("CalyxGannPipeline20261009",FILE_COMMON);
 rr05_equity_file=FileOpen(RR05Path("equity"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(rr05_equity_file==INVALID_HANDLE)return false;
 FileWrite(rr05_equity_file,"epoch","balance","equity");
 return true;
}
void RR05Observe()
{
 if(rr05_equity_file==INVALID_HANDLE)return;
 datetime now=TimeCurrent();
 if(rr05_last_trace>0 && now/(MQLInfoInteger(MQL_OPTIMIZATION)?86400:300)==rr05_last_trace/(MQLInfoInteger(MQL_OPTIMIZATION)?86400:300))return;
 rr05_last_trace=now;
 FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
}
void RR05Finish()
{
 if(rr05_equity_file==INVALID_HANDLE)return;
 FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
 FileClose(rr05_equity_file);rr05_equity_file=INVALID_HANDLE;
 int file=FileOpen(RR05Path("deals"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(file==INVALID_HANDLE || !HistorySelect(0,TimeCurrent())){Print("RR05_EXPORT_FAILED");return;}
 FileWrite(file,"deal","position_id","epoch","entry","type","volume","price","gross","commission","swap","fee","order","magic","sl","tp","reason","comment");
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong d=HistoryDealGetTicket(i);
  long kind=HistoryDealGetInteger(d,DEAL_TYPE);
  if(kind!=DEAL_TYPE_BUY && kind!=DEAL_TYPE_SELL)continue;
  ulong order=(ulong)HistoryDealGetInteger(d,DEAL_ORDER);
  FileWrite(file,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_ENTRY),kind,
    DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),
    DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),2),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),2),
    DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),2),DoubleToString(HistoryDealGetDouble(d,DEAL_FEE),2),
    order,HistoryDealGetInteger(d,DEAL_MAGIC),DoubleToString(HistoryOrderGetDouble(order,ORDER_SL),8),
    DoubleToString(HistoryOrderGetDouble(order,ORDER_TP),8),HistoryDealGetInteger(d,DEAL_REASON),HistoryDealGetString(d,DEAL_COMMENT));
 }
 FileClose(file);
 Print("RR05_EXPORT_COMPLETE");
}

int quotes_file=INVALID_HANDLE;
int OnInit(){if(!MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(C,0))return INIT_FAILED;LoadCase();int v=BaseInit();if(v!=INIT_SUCCEEDED)return v;InpRR05AuditTag=InpSignalAuditTag;if(!RR05AuditInit())return INIT_FAILED;
 quotes_file=FileOpen(RR05Path("quotes"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(quotes_file==INVALID_HANDLE)return INIT_FAILED;FileWrite(quotes_file,"deal","position_id","epoch","bid","ask","volume","price");RR05Observe();return INIT_SUCCEEDED;}
void OnTick(){RR05Observe();BaseTick();RR05Observe();}
void OnTradeTransaction(const MqlTradeTransaction &t,const MqlTradeRequest &request,const MqlTradeResult &result){if(t.type!=TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(t.deal))return;long type=HistoryDealGetInteger(t.deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)return;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;FileWrite(quotes_file,t.deal,HistoryDealGetInteger(t.deal,DEAL_POSITION_ID),HistoryDealGetInteger(t.deal,DEAL_TIME),DoubleToString(q.bid,8),DoubleToString(q.ask,8),DoubleToString(HistoryDealGetDouble(t.deal,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(t.deal,DEAL_PRICE),8));}
double OnTester(){int f=FileOpen(RR05Path("stats"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(f==INVALID_HANDLE)return -1e10;
 FileWrite(f,"net","balance","equity_dd_pct","balance_dd_pct","open_positions","rejected","invalid_geometry","undersize","placed");
 FileWrite(f,DoubleToString(TesterStatistics(STAT_PROFIT),2),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(TesterStatistics(STAT_EQUITY_DDREL_PERCENT),8),DoubleToString(TesterStatistics(STAT_BALANCE_DDREL_PERCENT),8),PositionsTotal(),rejected,invalid_geometry,undersize,placed);FileClose(f);return TesterStatistics(STAT_PROFIT);}
void OnDeinit(const int reason){RR05Observe();BaseDeinit(reason);RR05Finish();if(quotes_file!=INVALID_HANDLE)FileClose(quotes_file);}
