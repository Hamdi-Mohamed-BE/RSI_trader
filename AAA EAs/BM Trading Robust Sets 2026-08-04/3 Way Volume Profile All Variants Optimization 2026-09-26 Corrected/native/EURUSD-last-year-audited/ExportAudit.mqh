// Optional native optimization audit. Trading code is unchanged.
// This file is included only in audited validation/comparison builds.
double OnTester()
{
   double objective=OriginalOnTester();
   ulong ids[]; double pnl[]; datetime opened[],closed[];
   HistorySelect(0,TimeCurrent());
   for(int j=0;j<HistoryDealsTotal();j++)
   {
      ulong t=HistoryDealGetTicket(j),id=(ulong)HistoryDealGetInteger(t,DEAL_POSITION_ID);
      if(id==0 || HistoryDealGetString(t,DEAL_SYMBOL)!=_Symbol) continue;
      int k=-1; for(int z=0;z<ArraySize(ids);z++) if(ids[z]==id) { k=z; break; }
      if(k<0) { k=ArraySize(ids); ArrayResize(ids,k+1); ArrayResize(pnl,k+1); ArrayResize(opened,k+1); ArrayResize(closed,k+1); ids[k]=id; pnl[k]=0; opened[k]=0; closed[k]=0; }
      pnl[k]+=HistoryDealGetDouble(t,DEAL_PROFIT)+HistoryDealGetDouble(t,DEAL_SWAP)+HistoryDealGetDouble(t,DEAL_COMMISSION)+HistoryDealGetDouble(t,DEAL_FEE);
      datetime stamp=(datetime)HistoryDealGetInteger(t,DEAL_TIME);
      if(HistoryDealGetInteger(t,DEAL_ENTRY)==DEAL_ENTRY_IN && opened[k]==0) opened[k]=stamp;
      if(HistoryDealGetInteger(t,DEAL_ENTRY)==DEAL_ENTRY_OUT) closed[k]=stamp;
   }
   string path="CalyxResearch3WVPAll20260926\\"+AuditTag+"-"+IntegerToString(InpCase)+".csv";
   int file=FileOpen(path,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'|',CP_UTF8);
   if(file==INVALID_HANDLE) return -999999;
   int count=0,wins=0; double gain=0,loss=0;
   for(int k=0;k<ArraySize(ids);k++)
   {
      if(closed[k]==0) continue;
      count++; if(pnl[k]>0) { wins++; gain+=pnl[k]; } else loss-=pnl[k];
      FileWrite(file,"P",ids[k],(long)opened[k],(long)closed[k],DoubleToString(pnl[k],2));
   }
   double pf=loss>0 ? gain/loss : gain>0 ? 100 : 0;
   FileWrite(file,"S",count,wins,DoubleToString(pf,10),DoubleToString(gain-loss,2),
      DoubleToString(TesterStatistics(STAT_EQUITY_DDREL_PERCENT),10),
      DoubleToString(TesterStatistics(STAT_BALANCE_DDREL_PERCENT),10));
   FileClose(file);
   return objective;
}
