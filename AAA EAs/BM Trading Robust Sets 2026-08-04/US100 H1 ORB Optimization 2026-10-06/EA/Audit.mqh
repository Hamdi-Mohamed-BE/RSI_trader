input string InpAuditTag="";
int oa_events=INVALID_HANDLE,oa_equity=INVALID_HANDLE;
datetime oa_last=0;
string OAPath(const string kind) { return "CalyxORBOptimize20261006\\"+InpAuditTag+"-"+kind+".csv"; }
void ORBAuditInit()
{
   if(!(bool)MQLInfoInteger(MQL_TESTER) || InpAuditTag=="") return;
   FolderCreate("CalyxORBOptimize20261006",FILE_COMMON);
   oa_events=FileOpen(OAPath("events"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   oa_equity=FileOpen(OAPath("equity"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(oa_events==INVALID_HANDLE || oa_equity==INVALID_HANDLE) Print("ORB_AUDIT_OPEN_FAILED");
   FileWrite(oa_events,"position_id","epoch","signal_epoch","side","volume","entry","sl","tp","requested_risk","actual_risk","cash_per_point_lot","request_spread","request_price","range_width","atr","open_relvol");
   FileWrite(oa_equity,"epoch","balance","equity");
   ORBAuditTrace();
}
void ORBAuditTrace()
{
   if(oa_equity==INVALID_HANDLE) return;
   datetime now=TimeCurrent();
   if(oa_last>0 && now/300==oa_last/300) return;
   oa_last=now;
   FileWrite(oa_equity,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
}
void ORBAuditEntry(const int side,const MqlRates &signal,const MqlTick &quote,const double sl,const double tp)
{
   if(oa_events==INVALID_HANDLE) return;
   ulong ticket=0;
   if(!SelectOurPosition(ticket) || !PositionSelectByTicket(ticket)) { Print("ORB_AUDIT_POSITION_MISSING");return; }
   double entry=PositionGetDouble(POSITION_PRICE_OPEN),volume=PositionGetDouble(POSITION_VOLUME),risk=0,unit=0;
   ENUM_ORDER_TYPE type=(side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,volume,entry,sl,risk) || !OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1.0,entry,entry+1.0,unit)) Print("ORB_AUDIT_PROFIT_FAILED");
   FileWrite(oa_events,PositionGetInteger(POSITION_IDENTIFIER),(long)TimeCurrent(),(long)signal.time,side,DoubleToString(volume,8),DoubleToString(entry,8),DoubleToString(sl,8),DoubleToString(tp,8),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0,2),DoubleToString(MathAbs(risk),2),DoubleToString(unit,8),DoubleToString(quote.ask-quote.bid,8),DoubleToString(side>0 ? quote.ask : quote.bid,8),DoubleToString(g_range_high-g_range_low,8),DoubleToString(g_atr,8),DoubleToString(g_opening_relative_volume,8));
}
void ORBAuditDone()
{
   if(oa_events==INVALID_HANDLE) return;
   int f=FileOpen(OAPath("deals"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(f==INVALID_HANDLE) { Print("ORB_AUDIT_DEALS_FAILED");return; }
   FileWrite(f,"deal","position_id","epoch","entry","type","volume","price","gross","commission","swap","fee","comment");
   if(!HistorySelect(0,TimeCurrent())) Print("ORB_AUDIT_HISTORY_FAILED");
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong d=HistoryDealGetTicket(i);
      if(d==0 || HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic) continue;
      long type=HistoryDealGetInteger(d,DEAL_TYPE);
      if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL) continue;
      FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_ENTRY),type,DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),2),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),2),DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),2),DoubleToString(HistoryDealGetDouble(d,DEAL_FEE),2),HistoryDealGetString(d,DEAL_COMMENT));
   }
   FileWrite(oa_equity,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));
   FileClose(f);FileClose(oa_events);FileClose(oa_equity);
   Print("ORB_SUMMARY audit_complete");
}
