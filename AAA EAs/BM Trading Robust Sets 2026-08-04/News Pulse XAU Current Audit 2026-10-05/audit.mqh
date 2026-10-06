input string InpAuditTag="smoke";
int nr_intents=INVALID_HANDLE,nr_equity=INVALID_HANDLE;
datetime nr_last_trace=0;
string NR_Prefix(){return "CalyxNewsAudit20261005/"+InpAuditTag;}
bool NR_Init()
{
   if(!MQLInfoInteger(MQL_TESTER) || InpAdaptivePortfolioControls)return false;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return false;
   nr_intents=FileOpen(NR_Prefix()+"-intents.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',',CP_UTF8);
   nr_equity=FileOpen(NR_Prefix()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',',CP_UTF8);
   if(nr_intents<0 || nr_equity<0)return false;
   FileWrite(nr_intents,"epoch","comment","dir","entry","sl","tp","volume","budget","bid","ask","retcode","market");
   FileWrite(nr_equity,"epoch","balance","equity");
   return true;
}
void NR_Intent(const string comment,const bool buy,const double entry,const double sl,const double tp,const double lots,const double pct,const double bid,const double ask,const uint rc,const bool market)
{
   FileWrite(nr_intents,TimeCurrent(),comment,buy?1:-1,entry,sl,tp,lots,
      AccountInfoDouble(ACCOUNT_EQUITY)*pct/100.0,bid,ask,rc,market?1:0);
}
void NR_Trace(const bool force=false)
{
   if(nr_equity<0)return;
   datetime now=TimeCurrent();
   if(!force && now-nr_last_trace<(g_active_event_time>0?1:300))return;
   nr_last_trace=now;
   FileWrite(nr_equity,now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
}
void NR_Close(){if(nr_intents>=0)FileClose(nr_intents);if(nr_equity>=0)FileClose(nr_equity);}
void NR_Export()
{
   NR_Trace(true);FileFlush(nr_intents);FileFlush(nr_equity);
   int f=FileOpen(NR_Prefix()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',',CP_UTF8);
   if(f<0){Print("NR_AUDIT_FAILED deals");return;}
   FileWrite(f,"deal","epoch","position_id","entry","type","reason","volume","price","gross","commission","swap","fee","comment");
   HistorySelect(0,D'2099.01.01');
   ulong owned[];
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong d=HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(d,DEAL_TYPE)>1 || HistoryDealGetInteger(d,DEAL_ENTRY)!=DEAL_ENTRY_IN || HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic)continue;
      int n=ArraySize(owned);ArrayResize(owned,n+1);owned[n]=(ulong)HistoryDealGetInteger(d,DEAL_POSITION_ID);
   }
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong d=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(d,DEAL_TYPE);if(type>1)continue;
      bool ours=false;for(int j=0;j<ArraySize(owned);j++)if(owned[j]==(ulong)HistoryDealGetInteger(d,DEAL_POSITION_ID)){ours=true;break;}
      if(!ours)continue;
      FileWrite(f,d,HistoryDealGetInteger(d,DEAL_TIME),HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_ENTRY),type,
         HistoryDealGetInteger(d,DEAL_REASON),HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),
         HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT));
   }
   FileClose(f);
   PrintFormat("NR_EXPOSURE pending=%d positions=%d",OrdersTotal(),PositionsTotal());
}
