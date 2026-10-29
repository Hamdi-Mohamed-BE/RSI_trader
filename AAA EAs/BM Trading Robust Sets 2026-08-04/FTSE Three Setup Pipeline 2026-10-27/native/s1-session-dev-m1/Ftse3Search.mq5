#property strict
#property version "1.00"
#property description "Research only (2026-10-27). FTSE 100 three-setup pipeline engine: compiled case table, InpCase selects one configuration."
#include <Trade/Trade.mqh>

input int    InpCase=0;
input string InpTag="ftse3";
input double InpRiskPct=0.75;
input int    InpServerUtcOffsetHours=0;
input int    InpMaximumDeviationPoints=1000;
input long   InpMagic=2710270;

#define NF 51
#define NP 17
#define I_on 0
#define I_tf 1
#define I_p1 2
#define I_p2 3
#define I_p3 4
#define I_p4 5
#define I_p5 6
#define I_stop 7
#define I_tp 8
#define I_hold 9
#define I_be 10
#define I_tratr 11
#define I_trstart 12
#define I_dir 13
#define I_sess 14
#define I_adx 15
#define I_trend 16
const int NC=9;
const double Cases[9][NF]={
{1.0,60.0,40.0,2.5,30.0,0.0,0.0,2.0,5.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,40.0,2.5,30.0,0.0,0.0,2.0,5.0,0.0,1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,40.0,2.5,30.0,0.0,0.0,2.0,5.0,0.0,1.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,20.0,2.5,30.0,0.0,0.0,2.0,6.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,20.0,2.5,30.0,0.0,0.0,2.0,6.0,0.0,1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,20.0,2.5,30.0,0.0,0.0,2.0,6.0,0.0,1.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,20.0,2.5,30.0,0.0,0.0,2.0,4.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,20.0,2.5,30.0,0.0,0.0,2.0,4.0,0.0,1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0},
{1.0,60.0,20.0,2.5,30.0,0.0,0.0,2.0,4.0,0.0,1.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0,60.0,20.0,40.0,0.0,0.0,0.0,2.5,2.0,24.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,60.0,100.0,5.0,40.0,1.5,40.0,2.0,2.0,24.0,0.0,0.0,0.0,2.0,0.0,0.0,0.0}
};

double P[4][NP];                                   // P[setup][field], setups 1..3
ENUM_TIMEFRAMES gTf[4];
CTrade trade;
int hRsi[4],hAtr[4],hA[4],hB[4],hAdx[4],hD1=INVALID_HANDLE;
datetime lastBar[4],lastS2Day=0,lastClose=0,lastManage[4];
double gDist[4];
long entries[4],marketClosed=0,skippedStops=0,skippedMargin=0,placeFails=0,closeFails=0,modifyFails=0,filtered=0;

void Apply(){
   for(int s=1;s<=3;s++)for(int i=0;i<NP;i++)P[s][i]=Cases[InpCase][(s-1)*NP+i];
}
ENUM_TIMEFRAMES Tf(int m){return m==30?PERIOD_M30:(m==240?PERIOD_H4:PERIOD_H1);}
int Bars_(double hours,int s){return (int)MathMax(2,MathRound(hours*60.0/P[s][I_tf]));}

datetime LastSunday(int year,int month){            // March and October both have 31 days
   MqlDateTime t={};t.year=year;t.mon=month;t.day=31;
   datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);
   return x-(datetime)(d.day_of_week*86400);
}
datetime London(datetime utc){
   MqlDateTime d;TimeToStruct(utc,d);
   datetime on=LastSunday(d.year,3)+3600,off=LastSunday(d.year,10)+3600;
   return utc+((utc>=on&&utc<off)?3600:0);
}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
double Buf(int h,int buffer,int shift){double v[];if(CopyBuffer(h,buffer,shift,1,v)!=1)return EMPTY_VALUE;return v[0];}

bool HasPosition(long magic){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==magic)return true;}
   return false;
}
bool AnyPosition(){for(int s=1;s<=3;s++)if(HasPosition(InpMagic+s))return true;return false;}

bool Open(int s,bool buy,double atr){
   long magic=InpMagic+s;double stopAtr=P[s][I_stop],rr=P[s][I_tp];
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double dist=stopAtr*atr,entry=buy?q.ask:q.bid;
   double sl=Price(buy?entry-dist:entry+dist),tp=rr>0?Price(buy?entry+rr*dist:entry-rr*dist):0;
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   double ref=buy?q.bid:q.ask;
   if(MathAbs(ref-sl)<=gap||(tp>0&&MathAbs(tp-ref)<=gap)){skippedStops++;return false;}
   double unit=0,margin=0;ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPct/100.0;
   double volume=NormalizeDouble(MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step),8);
   if(volume>mx||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   trade.SetExpertMagicNumber(magic);
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,tp,"FTSE3P S"+(string)s):trade.Sell(volume,_Symbol,0,sl,tp,"FTSE3P S"+(string)s);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
      if(trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED)marketClosed++;else placeFails++;
      return false;
   }
   gDist[s]=MathAbs(entry-sl);entries[s]++;
   return true;
}

bool InTradeSession(){                               // broker trade-session table; quotes can arrive while trading is closed
   datetime now=TimeCurrent(),from=0,to=0;MqlDateTime d;TimeToStruct(now,d);long sec=(long)(now%86400);
   for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,from,to);i++)
      if(sec>=(long)from&&sec<(long)to)return true;
   return false;
}

void TimeExits(){
   datetime now=TimeCurrent();if(now-lastClose<30||!InTradeSession())return;
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;
      long m=PositionGetInteger(POSITION_MAGIC);if(m<InpMagic+1||m>InpMagic+3)continue;
      int ss=(int)(m-InpMagic);double hold=P[ss][I_hold];if(hold<=0)continue;
      if(now-(datetime)PositionGetInteger(POSITION_TIME)<(long)(hold*3600))continue;
      lastClose=now;
      if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
         if(trade.ResultRetcode()!=TRADE_RETCODE_POSITION_CLOSED&&trade.ResultRetcode()!=TRADE_RETCODE_MARKET_CLOSED)closeFails++;}
   }
}

void ManageStops(){
   datetime now=TimeCurrent();
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;
      long m=PositionGetInteger(POSITION_MAGIC);if(m<InpMagic+1||m>InpMagic+3)continue;
      int s=(int)(m-InpMagic);double be=P[s][I_be],tr=P[s][I_tratr];
      if((be<=0&&tr<=0)||gDist[s]<=0||now==lastManage[s])continue;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
      double price=buy?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double gain=buy?price-open:open-price,want=sl;
      if(be>0&&gain>=be*gDist[s])want=buy?MathMax(want,open):(want<=0?open:MathMin(want,open));
      if(tr>0&&gain>=P[s][I_trstart]*gDist[s]){
         double atr=Buf(hAtr[s],0,1);
         if(atr!=EMPTY_VALUE&&atr>0){double x=buy?price-tr*atr:price+tr*atr;want=buy?MathMax(want,x):MathMin(want,x);}
      }
      want=Price(want);
      double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
      bool better=buy?want>sl+_Point:want<sl-_Point;
      bool legal=buy?price-want>gap:want-price>gap;
      if(!better||!legal)continue;
      lastManage[s]=now;
      if(!trade.PositionModify(t,want,tp))modifyFails++;
   }
}

bool SessionOk(int s){
   int mode=(int)P[s][I_sess];if(mode==0)return true;
   MqlDateTime n;TimeToStruct(London(Utc(TimeCurrent())),n);int mins=n.hour*60+n.min;
   if(mode==1)return mins>=8*60&&mins<16*60+30;
   return mins>=7*60&&mins<21*60;
}
bool FilterOk(int s,bool buy){
   double a=P[s][I_adx];
   if(a!=0){double x=Buf(hAdx[s],0,1);if(x==EMPTY_VALUE)return false;if(a>0&&x<a)return false;if(a<0&&x>-a)return false;}
   int tr=(int)P[s][I_trend];
   if(tr!=0){double e=Buf(hD1,0,1),c=iClose(_Symbol,PERIOD_D1,1);if(e==EMPTY_VALUE||c<=0)return false;bool up=c>e;
      if(tr==1&&up!=buy)return false;if(tr==2&&up==buy)return false;}
   return true;
}
bool DirOk(int s,bool buy){int d=(int)P[s][I_dir];return d==2||(d==0&&buy)||(d==1&&!buy);}
bool Try(int s,bool buy,double atr){
   if(!DirOk(s,buy))return false;
   if(!SessionOk(s)||!FilterOk(s,buy)){filtered++;return false;}
   return Open(s,buy,atr);
}

void Evaluate(int s){
   if(P[s][I_on]<0.5)return;
   datetime bar=iTime(_Symbol,gTf[s],0);
   if(bar==0||bar==lastBar[s])return;
   lastBar[s]=bar;
   datetime prev=iTime(_Symbol,gTf[s],1);
   double rsi=Buf(hRsi[s],0,1),atr=Buf(hAtr[s],0,1),close=iClose(_Symbol,gTf[s],1);
   if(prev==0||rsi==EMPTY_VALUE||atr==EMPTY_VALUE||atr<=0||close<=0)return;
   if(s==1){
      if(HasPosition(InpMagic+1))return;
      double lower=Buf(hA[1],2,1),upper=Buf(hA[1],1,1),r=P[1][I_p3];if(lower==EMPTY_VALUE||upper==EMPTY_VALUE)return;
      if(close<lower&&rsi<r){Try(1,true,atr);return;}
      if(close>upper&&rsi>100-r)Try(1,false,atr);
   }
   if(s==2){
      double ma=Buf(hA[2],0,1),r=P[2][I_p2];if(ma==EMPTY_VALUE)return;
      datetime lon=London(Utc(prev));MqlDateTime d;TimeToStruct(lon,d);datetime day=lon-lon%86400;
      bool dayOk=P[2][I_p3]<0.5?d.day_of_week==1:(d.day_of_week==1||d.day_of_week==2);
      if(!dayOk||day==lastS2Day||HasPosition(InpMagic+2))return;
      bool ok=false;
      if(close<ma&&rsi<r)ok=Try(2,true,atr);
      else if(close>ma&&rsi>100-r)ok=Try(2,false,atr);
      if(ok)lastS2Day=day;
   }
   if(s==3){
      if(HasPosition(InpMagic+3))return;
      double t0=Buf(hA[3],0,1),tN=Buf(hA[3],0,1+(int)P[3][I_p2]),ma=Buf(hB[3],0,1),dist=P[3][I_p4],r=P[3][I_p5];
      if(t0==EMPTY_VALUE||tN==EMPTY_VALUE||ma==EMPTY_VALUE)return;
      if(t0>tN&&close<=ma-dist*atr&&rsi<r)Try(3,true,atr);
      else if(t0<tN&&close>=ma+dist*atr&&rsi>100-r)Try(3,false,atr);
   }
}

int OnInit(){
   if(!MQLInfoInteger(MQL_TESTER)||InpCase<0||InpCase>=NC||InpRiskPct<=0||InpRiskPct>5)return INIT_PARAMETERS_INCORRECT;
   Apply();
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   hD1=iMA(_Symbol,PERIOD_D1,50,0,MODE_EMA,PRICE_CLOSE);if(hD1==INVALID_HANDLE)return INIT_FAILED;
   for(int s=1;s<=3;s++){
      hRsi[s]=hAtr[s]=hA[s]=hB[s]=hAdx[s]=INVALID_HANDLE;lastBar[s]=0;lastManage[s]=0;gDist[s]=0;entries[s]=0;
      if(P[s][I_on]<0.5)continue;
      if(P[s][I_tp]<=0&&P[s][I_hold]<=0&&P[s][I_tratr]<=0)return INIT_PARAMETERS_INCORRECT;
      gTf[s]=Tf((int)P[s][I_tf]);
      hRsi[s]=iRSI(_Symbol,gTf[s],14,PRICE_CLOSE);hAtr[s]=iATR(_Symbol,gTf[s],14);hAdx[s]=iADX(_Symbol,gTf[s],14);
      if(s==1)hA[1]=iBands(_Symbol,gTf[1],Bars_(P[1][I_p1],1),0,P[1][I_p2],PRICE_CLOSE);
      if(s==2)hA[2]=iMA(_Symbol,gTf[2],Bars_(P[2][I_p1],2),0,MODE_SMA,PRICE_CLOSE);
      if(s==3){hA[3]=iMA(_Symbol,gTf[3],Bars_(P[3][I_p1],3),0,MODE_SMA,PRICE_CLOSE);hB[3]=iMA(_Symbol,gTf[3],Bars_(P[3][I_p3],3),0,MODE_SMA,PRICE_CLOSE);if(hB[3]==INVALID_HANDLE)return INIT_FAILED;}
      if(hRsi[s]==INVALID_HANDLE||hAtr[s]==INVALID_HANDLE||hA[s]==INVALID_HANDLE||hAdx[s]==INVALID_HANDLE)return INIT_FAILED;
   }
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   return INIT_SUCCEEDED;
}

void OnTick(){
   TimeExits();ManageStops();
   for(int s=1;s<=3;s++)Evaluate(s);
}

string Tag(){return InpTag+"-"+(string)InpCase;}
double OnTester(){
   HistorySelect(0,TimeCurrent());
   int out=FileOpen(Tag()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
   if(out==INVALID_HANDLE)return -1e99;
   FileWrite(out,"ticket","position_id","epoch","entry","type","volume","price","profit","commission","swap","fee","reason","initial_sl","initial_tp","magic");
   for(int i=0;i<HistoryDealsTotal();i++){
      ulong deal=HistoryDealGetTicket(i);if(deal==0)continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);if(entry!=DEAL_ENTRY_IN&&entry!=DEAL_ENTRY_OUT)continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol)continue;
      ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
      FileWrite(out,deal,HistoryDealGetInteger(deal,DEAL_POSITION_ID),(long)HistoryDealGetInteger(deal,DEAL_TIME),entry,HistoryDealGetInteger(deal,DEAL_TYPE),
         HistoryDealGetDouble(deal,DEAL_VOLUME),HistoryDealGetDouble(deal,DEAL_PRICE),HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_COMMISSION),
         HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_FEE),HistoryDealGetInteger(deal,DEAL_REASON),HistoryOrderGetDouble(order,ORDER_SL),HistoryOrderGetDouble(order,ORDER_TP),
         HistoryDealGetInteger(deal,DEAL_MAGIC));
   }
   FileClose(out);
   out=FileOpen(Tag()+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(out==INVALID_HANDLE)return -1e99;
   FileWrite(out,"net","equity_dd","balance_dd","failed_entries","balance","open_position","trades","mt5_sharpe","s1_entries","s2_entries","s3_entries","market_closed","filtered","skipped_stops","skipped_margin","close_fails","modify_fails");
   FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_BALANCE_DDREL_PERCENT),placeFails,AccountInfoDouble(ACCOUNT_BALANCE),
      (int)AnyPosition(),TesterStatistics(STAT_TRADES),TesterStatistics(STAT_SHARPE_RATIO),entries[1],entries[2],entries[3],marketClosed,filtered,skippedStops,skippedMargin,closeFails,modifyFails);
   FileClose(out);
   return TesterStatistics(STAT_PROFIT);
}
