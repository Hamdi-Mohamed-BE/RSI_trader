// Private tester-only exit experiment. Never included in production.
input int InpExitCase=0;
input long InpResearchRun=0;

string NR_Stamp(datetime t){return TimeToString(t,TIME_DATE|TIME_SECONDS);}
void NR_Value(int f,string key,double value){FileWrite(f,key,DoubleToString(value,8));}

double NR_WriteAudit()
{
   string prefix="NP-EXIT-"+IntegerToString(InpResearchRun)+"-"+IntegerToString(InpExitCase);
   int f=FileOpen(prefix+"-summary.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
   if(f==INVALID_HANDLE)return -DBL_MAX;
   FileWrite(f,"key","value");
   NR_Value(f,"case",InpExitCase);NR_Value(f,"profit",TesterStatistics(STAT_PROFIT));
   NR_Value(f,"trades",TesterStatistics(STAT_TRADES));NR_Value(f,"native_pf",TesterStatistics(STAT_PROFIT_FACTOR));
   NR_Value(f,"equity_dd_pct",TesterStatistics(STAT_EQUITY_DDREL_PERCENT));
   NR_Value(f,"final_balance",AccountInfoDouble(ACCOUNT_BALANCE));
   NR_Value(f,"expected_events",g_tester_expected_event_count);
   NR_Value(f,"attempted_events",g_tester_attempted_event_count);
   NR_Value(f,"complete_straddles",g_tester_successful_event_count);
   NR_Value(f,"boundary_violation",g_tester_calendar_boundary_violation ? 1 : 0);
   NR_Value(f,"open_positions",PositionsTotal());NR_Value(f,"pending_orders",OrdersTotal());
   FileClose(f);
   f=FileOpen(prefix+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
   if(f==INVALID_HANDLE)return -DBL_MAX;
   FileWrite(f,"deal","time","symbol","position_id","magic","type","entry","volume","price","profit","commission","swap","fee","comment");
   HistorySelect(0,TimeCurrent());
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong d=HistoryDealGetTicket(i);
      FileWrite(f,d,NR_Stamp((datetime)HistoryDealGetInteger(d,DEAL_TIME)),
         HistoryDealGetString(d,DEAL_SYMBOL),HistoryDealGetInteger(d,DEAL_POSITION_ID),
         HistoryDealGetInteger(d,DEAL_MAGIC),HistoryDealGetInteger(d,DEAL_TYPE),HistoryDealGetInteger(d,DEAL_ENTRY),
         HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),
         HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),
         HistoryDealGetString(d,DEAL_COMMENT));
   }
   FileClose(f);
   return g_tester_calendar_boundary_violation ? -DBL_MAX : TesterStatistics(STAT_PROFIT);
}
