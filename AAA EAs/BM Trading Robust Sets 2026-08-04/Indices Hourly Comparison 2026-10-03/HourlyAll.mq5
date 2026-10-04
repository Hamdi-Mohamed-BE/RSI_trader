#property strict
#include <Trade/Trade.mqh>
input bool InpOvernight=false;
input string InpTag="indices-hourly";
input double InpLots=1.0;
CTrade tr;
long base=103000;
int lastday[48];datetime deadline[48],lastclose[48];
double realised[48],peak[48],maxdd[48];
int errors=0;
int Sunday(int y,int m,int nth){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=1;TimeToStruct(StructToTime(x),x);return 1+(7-x.day_of_week)%7+7*(nth-1);}
datetime NY(datetime utc){MqlDateTime x;TimeToStruct(utc,x);int y=x.year;MqlDateTime a,b;ZeroMemory(a);ZeroMemory(b);a.year=y;a.mon=3;a.day=Sunday(y,3,2);a.hour=7;b.year=y;b.mon=11;b.day=Sunday(y,11,1);b.hour=6;return utc-((utc>=StructToTime(a)&&utc<StructToTime(b))?4:5)*3600;}
void Mark(){
 double eq[48];for(int i=0;i<48;i++)eq[i]=10000+realised[i];
 for(int j=PositionsTotal()-1;j>=0;j--){ulong t=PositionGetTicket(j);if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;long magic=PositionGetInteger(POSITION_MAGIC);int slot=(int)(magic-base);if(slot>=0&&slot<48)eq[slot]+=PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP);}
 for(int i=0;i<48;i++){peak[i]=MathMax(peak[i],eq[i]);if(peak[i]>0)maxdd[i]=MathMax(maxdd[i],100*(peak[i]-eq[i])/peak[i]);}
}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;ArrayInitialize(lastday,0);ArrayInitialize(deadline,0);ArrayInitialize(lastclose,0);ArrayInitialize(realised,0.);ArrayInitialize(peak,10000.);ArrayInitialize(maxdd,0.);tr.SetTypeFillingBySymbol(_Symbol);tr.SetDeviationInPoints(30);return INIT_SUCCEEDED;}
void OnTradeTransaction(const MqlTradeTransaction &t,const MqlTradeRequest &r,const MqlTradeResult &s){
 if(t.type!=TRADE_TRANSACTION_DEAL_ADD||!HistoryDealSelect(t.deal))return;
 int slot=(int)(HistoryDealGetInteger(t.deal,DEAL_MAGIC)-base);
 if(slot>=0&&slot<48)realised[slot]+=HistoryDealGetDouble(t.deal,DEAL_PROFIT)+HistoryDealGetDouble(t.deal,DEAL_COMMISSION)+HistoryDealGetDouble(t.deal,DEAL_SWAP)+HistoryDealGetDouble(t.deal,DEAL_FEE);
}
void OnTick(){
 datetime now=TimeCurrent();MqlDateTime ny;TimeToStruct(NY(now),ny);int day=ny.year*10000+ny.mon*100+ny.day;
 Mark();
 for(int j=PositionsTotal()-1;j>=0;j--){ulong ticket=PositionGetTicket(j);if(!ticket||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;int slot=(int)(PositionGetInteger(POSITION_MAGIC)-base);if(slot<0||slot>=48)continue;if(deadline[slot]>0&&now>=deadline[slot]&&now>lastclose[slot]){lastclose[slot]=now;tr.SetExpertMagicNumber(base+slot);if(!tr.PositionClose(ticket))errors++;}}
 if(ny.day_of_week==0||ny.day_of_week==6||ny.min!=0)return;
 if(InpOvernight&&ny.hour!=19)return;
 if(!InpOvernight&&(ny.hour==16||ny.hour==17))return;
 int first=InpOvernight?38:ny.hour*2,last=InpOvernight?38:first+1;
 for(int slot=first;slot<=last;slot++){
  if(lastday[slot]==day)continue;lastday[slot]=day;
  // No entry-side foresight: completeness is a post-execution sample audit.
  int sec=ny.sec;deadline[slot]=now-sec+(InpOvernight?660:60)*60;
  tr.SetExpertMagicNumber(base+slot);string tag=InpTag+"|"+IntegerToString(slot);
  bool ok=(slot%2==0)?tr.Buy(InpLots,_Symbol,0,0,0,tag):tr.Sell(InpLots,_Symbol,0,0,0,tag);
  uint code=tr.ResultRetcode();if(!ok||(code!=TRADE_RETCODE_DONE&&code!=TRADE_RETCODE_DONE_PARTIAL)){errors++;Print("HOUR_ORDER_ERROR ",slot," ",code);}
 }
}
double OnTester(){
 HistorySelect(0,TimeCurrent());
 int f=FileOpen(InpTag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"ticket","position_id","time_msc","magic","entry","type","volume","price","profit","commission","swap","fee","comment");
 for(int j=0;j<HistoryDealsTotal();j++){ulong d=HistoryDealGetTicket(j);int slot=(int)(HistoryDealGetInteger(d,DEAL_MAGIC)-base);if(slot<0||slot>=48)continue;FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetInteger(d,DEAL_MAGIC),HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT));}FileClose(f);
 Mark();int e=FileOpen(InpTag+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');FileWrite(e,"slot","realised","max_equity_dd_pct");for(int i=0;i<48;i++)FileWrite(e,i,realised[i],maxdd[i]);FileClose(e);
 Print("HOUR_NATIVE_COMPLETE errors=",errors," deals=",HistoryDealsTotal());return 0;
}
