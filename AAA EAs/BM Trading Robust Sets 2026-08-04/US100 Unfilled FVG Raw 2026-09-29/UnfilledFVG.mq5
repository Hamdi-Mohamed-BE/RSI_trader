#property strict
#property version "1.00"
#property description "Tester-only market-style hypotheses. Not a reproduction of the clip."
#include <Trade/Trade.mqh>
input int InpMode=0;
input bool InpControl=false;
input double InpRiskPercent=1.0;
input double InpRR=1.0;
input uint InpSeed=290929;
input datetime InpTradeFrom=D'2021.09.27';
input string InpTag="smoke";
input long InpMagic=9294400;
CTrade trade;
double tickSize=0,lotStep=0,minLot=0;
datetime lastBar=0,lastMinute=0,attemptDay=0,lastClose=0;
int trace=INVALID_HANDLE,signalFile=INVALID_HANDLE,entries=0,entryFails=0,closeFails=0,skips=0,stale=0;
struct Entry {ulong id;datetime time;int side;double risk,requestedRisk,sl,tp,volume,fill,atr;};
Entry initial[];
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
double Price(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,_Digits);}
bool Session(datetime now,int &remaining){
 MqlDateTime dt;TimeToStruct(now,dt);int s=(int)(now%86400);datetime a,b;remaining=0;
 for(uint i=0;i<20;i++){
  if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)dt.day_of_week,i,a,b))break;
  int lo=(int)((long)a%86400),hi=(int)((long)b%86400);if(hi==0)hi=86400;
  if(s>=lo && s<hi){remaining=hi-s;return true;}
 }
 return false;
}
void Close(){
 ulong ticket;if(!Own(ticket))return;datetime now=TimeCurrent();if(now-lastClose<60)return;lastClose=now;
 if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
  if(trade.ResultRetcode()==TRADE_RETCODE_POSITION_CLOSED && !Own(ticket)){Print("MS_CLOSE_RACE already closed");return;}
  closeFails++;PrintFormat("MS_CLOSE_FAIL code=%u",trade.ResultRetcode());
 }
}
uint Hash(uint x){x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return x;}

#include "logic.mqh"
struct Item {ulong id;datetime opened,closed;int side;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){
 HistorySelect(0,TimeCurrent());Item rows[];int n=0;
 for(int j=0;j<HistoryDealsTotal();j++){
  ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}
  if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);
 }
 int f=FileOpen("CalyxUnfilledFVG20260929\\"+InpTag+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit");
 for(int k=0;k<n;k++){
  int ix=-1;for(int z=0;z<ArraySize(initial);z++)if(initial[z].id==rows[k].id){ix=z;break;}
  double net=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;
  FileWrite(f,rows[k].id,(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,ix>=0?initial[ix].sl:0,ix>=0?initial[ix].tp:0,ix>=0?initial[ix].requestedRisk:0,ix>=0?initial[ix].risk:0,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,net);
 }
 FileClose(f);return TesterStatistics(STAT_PROFIT_FACTOR);
}
