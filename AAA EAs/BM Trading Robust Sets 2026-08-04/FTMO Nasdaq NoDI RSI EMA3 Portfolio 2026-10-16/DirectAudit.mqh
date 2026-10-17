input string InpDirectTag="N5-direct-parity";
int directEquity=INVALID_HANDLE;datetime directLastMinute=0;
string DirectPath(const string suffix){return "FTMO3_20261016_"+InpDirectTag+"-"+suffix+".csv";}
bool DirectAuditInit()
{
 directEquity=FileOpen(DirectPath("equity"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(directEquity==INVALID_HANDLE)return false;FileWrite(directEquity,"epoch","balance","equity");return true;
}
void DirectObserve()
{
 if(TimeCurrent()/60==directLastMinute/60)return;directLastMinute=TimeCurrent();
 FileWrite(directEquity,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
}
void DirectFinish()
{
 FileWrite(directEquity,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileClose(directEquity);
 HistorySelect(0,TimeCurrent()+86400);int f=FileOpen(DirectPath("deals"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"deal","position_id","epoch","entry","type","volume","price","gross","commission","swap","fee","order","magic","sl","tp","reason","comment","order_price_open","order_type","time_msc","symbol");
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong d=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(d,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;ulong o=(ulong)HistoryDealGetInteger(d,DEAL_ORDER);
  FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_ENTRY),type,DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),2),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),2),DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),2),DoubleToString(HistoryDealGetDouble(d,DEAL_FEE),2),o,HistoryDealGetInteger(d,DEAL_MAGIC),DoubleToString(HistoryOrderGetDouble(o,ORDER_SL),8),DoubleToString(HistoryOrderGetDouble(o,ORDER_TP),8),HistoryDealGetInteger(d,DEAL_REASON),HistoryDealGetString(d,DEAL_COMMENT),DoubleToString(HistoryOrderGetDouble(o,ORDER_PRICE_OPEN),8),HistoryOrderGetInteger(o,ORDER_TYPE),HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetString(d,DEAL_SYMBOL));
 }
 FileClose(f);Print("FTMO3_DIRECT_COMPLETE last=",(long)TimeCurrent());
}
