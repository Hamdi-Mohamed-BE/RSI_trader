// Tester-only, read-only instrumentation. No order placement or modification.
input string InpRR05AuditTag="";
int rr05_equity_file=INVALID_HANDLE;
datetime rr05_last_trace=0;
string RR05Path(const string suffix){return "CalyxRR05All20261008\\"+InpRR05AuditTag+"-"+suffix+".csv";}
bool RR05AuditInit()
{
 if(!MQLInfoInteger(MQL_TESTER) || InpRR05AuditTag=="")return false;
 FolderCreate("CalyxRR05All20261008",FILE_COMMON);
 rr05_equity_file=FileOpen(RR05Path("equity"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(rr05_equity_file==INVALID_HANDLE)return false;
 FileWrite(rr05_equity_file,"epoch","balance","equity");
 return true;
}
void RR05Observe()
{
 if(rr05_equity_file==INVALID_HANDLE)return;
 datetime now=TimeCurrent();
 if(rr05_last_trace>0 && now/300==rr05_last_trace/300)return;
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
