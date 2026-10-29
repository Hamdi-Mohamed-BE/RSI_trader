#property strict
#property version "1.00"
#property description "Research only (2026-10-26). Reel 'Trading with VWAP & EMA': enter when the close turns below (above) both the 09:30 NY"
#property description "session VWAP and EMA, exit when it closes beyond both the other way (reverse), flat 15:55 NY, 2 ATR emergency stop. Rules: RULES.md."
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;         // % of equity to the emergency stop; lots rounded UP to the step (minimum lot if needed)
input int    InpMode=0;                  // 0 = VWAP and EMA (main); 1 = VWAP only; 2 = EMA only
input int    InpEMAPeriod=20;
input double InpStopATR=2.0;
input int    InpATRPeriod=14;
input int    InpStartHourNY=9;
input int    InpStartMinuteNY=30;
input int    InpLastEntryHourNY=15;
input int    InpLastEntryMinuteNY=30;
input int    InpFlatHourNY=15;
input int    InpFlatMinuteNY=55;
input int    InpServerUtcOffsetHours=0;  // Exness server = UTC
input int    InpMaximumDeviationPoints=50;
input long   InpMagic=2610260;

CTrade trade;
int hEma=INVALID_HANDLE,hAtr=INVALID_HANDLE;
datetime lastBar=0,lastClose=0;
int prevState=0;                           // state of the previous closed bar within today's session (0 none / between)
int sessionKey=-1;
long entries=0,reversals=0,signalExits=0,flats=0,skippedStops=0,skippedMargin=0,placeFails=0,closeFails=0,days=0;

datetime NthSunday(int year,int month,int n){
   MqlDateTime t={};t.year=year;t.mon=month;t.day=1;
   datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);
   return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);
}
datetime NewYork(datetime utc){                      // DST from 2nd Sunday March 07:00 UTC to 1st Sunday November 06:00 UTC
   MqlDateTime d;TimeToStruct(utc,d);
   datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;
   return utc-5*3600+((utc>=on&&utc<off)?3600:0);
}
datetime NY(datetime server){return NewYork(server-(datetime)((long)InpServerUtcOffsetHours*3600));}
int Minutes(datetime ny){MqlDateTime d;TimeToStruct(ny,d);return d.hour*60+d.min;}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
double Buf(int h,int shift){double v[];if(CopyBuffer(h,0,shift,1,v)!=1)return EMPTY_VALUE;return v[0];}

// Session VWAP over closed bars of today's NY session up to bar 1 (typical price x tick volume).
double SessionVwap(){
   MqlRates r[];ArraySetAsSeries(r,true);
   int n=CopyRates(_Symbol,_Period,1,400,r);if(n<1)return 0;
   datetime ny1=NY(r[0].time);MqlDateTime d1;TimeToStruct(ny1,d1);
   int start=InpStartHourNY*60+InpStartMinuteNY;double pv=0,vol=0;
   for(int i=0;i<n;i++){
      datetime ny=NY(r[i].time);MqlDateTime d;TimeToStruct(ny,d);
      if(d.day_of_year!=d1.day_of_year||d.year!=d1.year||d.hour*60+d.min<start)break;
      double w=(double)r[i].tick_volume;if(w<=0)w=1;pv+=(r[i].high+r[i].low+r[i].close)/3.0*w;vol+=w;
   }
   return vol>0?pv/vol:0;
}

int PositionDir(ulong &ticket){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=t;return PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;}}
   ticket=0;return 0;
}

bool ClosePos(ulong ticket,string why){
   if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("VER_CLOSE_FAIL %s code=%u",why,trade.ResultRetcode());return false;}
   return true;
}

bool Open(bool buy,double atr,string cm){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double entry=buy?q.ask:q.bid,dist=InpStopATR*atr,sl=Price(buy?entry-dist:entry+dist);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   if((buy&&q.bid-sl<=gap)||(!buy&&sl-q.ask<=gap)){skippedStops++;return false;}
   ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;double unit=0,margin=0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeDouble(MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step),8);
   if(volume>mx||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   trade.SetExpertMagicNumber(InpMagic);
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,0,cm):trade.Sell(volume,_Symbol,0,sl,0,cm);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){placeFails++;PrintFormat("VER_PLACE_FAIL %s code=%u",cm,trade.ResultRetcode());return false;}
   PrintFormat("VER_ENTRY %s entry=%.2f sl=%.2f atr=%.2f lots=%.2f risk=%.2f",cm,entry,sl,atr,volume,goal);
   return true;
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpMode<0||InpMode>2||InpEMAPeriod<2||InpStopATR<=0)return INIT_PARAMETERS_INCORRECT;
   hEma=iMA(_Symbol,_Period,InpEMAPeriod,0,MODE_EMA,PRICE_CLOSE);hAtr=iATR(_Symbol,_Period,InpATRPeriod);
   if(hEma==INVALID_HANDLE||hAtr==INVALID_HANDLE)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   PrintFormat("VER_SPEC symbol=%s tf=%s digits=%d vol_min=%.2f step=%.2f mode=%d ema=%d stop_atr=%.2f",
               _Symbol,EnumToString(_Period),_Digits,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),InpMode,InpEMAPeriod,InpStopATR);
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime now=TimeCurrent();int nm=Minutes(NY(now));ulong ticket=0;int dir=PositionDir(ticket);
   // session close: flatten (retry every 30 s if the market rejects)
   if(dir!=0&&nm>=InpFlatHourNY*60+InpFlatMinuteNY&&now-lastClose>=30){lastClose=now;if(ClosePos(ticket,"FLAT"))flats++;return;}
   datetime bar=iTime(_Symbol,_Period,0);
   if(bar==0||bar==lastBar)return;
   lastBar=bar;
   datetime closedOpen=iTime(_Symbol,_Period,1);datetime ny1=NY(closedOpen);MqlDateTime d1;TimeToStruct(ny1,d1);
   int key=d1.year*1000+d1.day_of_year;
   if(key!=sessionKey){sessionKey=key;prevState=0;}
   int start=InpStartHourNY*60+InpStartMinuteNY,barMin=d1.hour*60+d1.min;
   if(d1.day_of_week<1||d1.day_of_week>5||barMin<start)return;
   int closeMin=barMin+PeriodSeconds(_Period)/60;
   if(closeMin>InpFlatHourNY*60+InpFlatMinuteNY)return;
   if(barMin==start)days++;
   double c1=iClose(_Symbol,_Period,1),e1=Buf(hEma,1),v1=SessionVwap(),atr=Buf(hAtr,1);
   if(e1==EMPTY_VALUE||atr==EMPTY_VALUE||atr<=0||v1<=0)return;
   double hi=InpMode==1?v1:InpMode==2?e1:MathMax(v1,e1),lo=InpMode==1?v1:InpMode==2?e1:MathMin(v1,e1);
   int state=c1>hi?1:c1<lo?-1:0;
   int was=prevState;prevState=state;
   dir=PositionDir(ticket);
   if(dir!=0&&state==-dir){if(ClosePos(ticket,"SIGNAL")){signalExits++;dir=0;}}
   bool canEnter=closeMin<=InpLastEntryHourNY*60+InpLastEntryMinuteNY;
   if(dir==0&&canEnter&&state!=0&&was!=state){
      bool rev=(signalExits>0&&was==-state);
      if(Open(state>0,atr,state>0?"VER LONG":"VER SHORT")){entries++;if(rev)reversals++;}
   }
}

void OnDeinit(const int reason){
   PrintFormat("VER_SUMMARY days=%I64d entries=%I64d reversals=%I64d signal_exits=%I64d flats=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d close_fails=%I64d",
               days,entries,reversals,signalExits,flats,skippedStops,skippedMargin,placeFails,closeFails);
}
