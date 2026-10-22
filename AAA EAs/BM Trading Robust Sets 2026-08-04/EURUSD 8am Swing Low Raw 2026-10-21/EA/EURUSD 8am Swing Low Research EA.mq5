#property strict
#property version "1.00"
#property description "Research only (2026-10-21). EURUSD H1: at 08:00 London or New York, buy after a fresh fractal swing low"
#property description "(pivot confirmed by the 08:00 close), stop below the pivot, time exit. Mirror/every-day/random controls and a logger. Rules: RULES.md."
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;         // % of equity per trade; lots rounded UP to the step (minimum lot if needed)
input int    InpClock=0;                 // 0 = 08:00 London (UK DST); 1 = 08:00 New York (US DST)
input int    InpEntryHour=8;
input int    InpMode=0;                  // 0 fresh swing low long; 1 fresh swing high short; 2 every day long; 3 random days long
input int    InpFractal=2;               // bars on each side of the pivot
input int    InpFreshWindow=1;           // pivot positions accepted (1 = confirmed exactly by the 08:00 close)
input bool   InpRequireLowerLow=false;   // pivot low must be below the previous confirmed pivot low
input int    InpHoldHours=4;
input double InpStopBufferAtr=0.10;
input double InpMinStopAtr=0.50;
input int    InpAtrPeriod=14;
input double InpRandomProb=0.2;          // mode 3: probability per weekday
input int    InpRandomSeed=1;
input bool   InpLogDrift=false;          // logger: no trades; print 08:00 flags and price at +1..+8 h
input int    InpServerUtcOffsetHours=0;  // Exness server = UTC
input int    InpMaximumDeviationPoints=50;
input long   InpMagic=2110260;

CTrade trade;
int hAtr=INVALID_HANDLE;
datetime lastBar=0,lastDay=0,lastClose=0,driftBase=0;
long days=0,freshLow=0,freshHigh=0,entries=0,skippedStops=0,skippedMargin=0,placeFails=0,closeFails=0,noPivot=0;

datetime LastSunday(int year,int month){            // March and October both have 31 days
   MqlDateTime t={};t.year=year;t.mon=month;t.day=31;
   datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);
   return x-(datetime)(d.day_of_week*86400);
}
datetime NthSunday(int year,int month,int n){
   MqlDateTime t={};t.year=year;t.mon=month;t.day=1;
   datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);
   return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);
}
datetime London(datetime utc){
   MqlDateTime d;TimeToStruct(utc,d);
   datetime on=LastSunday(d.year,3)+3600,off=LastSunday(d.year,10)+3600;
   return utc+((utc>=on&&utc<off)?3600:0);
}
datetime NewYork(datetime utc){                      // DST from 2nd Sunday March 07:00 UTC to 1st Sunday November 06:00 UTC
   MqlDateTime d;TimeToStruct(utc,d);
   datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;
   return utc-5*3600+((utc>=on&&utc<off)?3600:0);
}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
datetime Local(datetime server){return InpClock==0?London(Utc(server)):NewYork(Utc(server));}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
double Atr(){double v[];if(CopyBuffer(hAtr,0,1,1,v)!=1)return EMPTY_VALUE;return v[0];}

bool PivotLow(int k,int n){
   double x=iLow(_Symbol,PERIOD_H1,k);if(x<=0)return false;
   for(int j=1;j<=n;j++){if(k-j<1)return false;if(!(x<iLow(_Symbol,PERIOD_H1,k-j))||!(x<iLow(_Symbol,PERIOD_H1,k+j)))return false;}
   return true;
}
bool PivotHigh(int k,int n){
   double x=iHigh(_Symbol,PERIOD_H1,k);if(x<=0)return false;
   for(int j=1;j<=n;j++){if(k-j<1)return false;if(!(x>iHigh(_Symbol,PERIOD_H1,k-j))||!(x>iHigh(_Symbol,PERIOD_H1,k+j)))return false;}
   return true;
}
int FreshLow(int n,int window,bool lowerLow){       // shift of the most recent qualifying pivot low, or -1
   for(int k=n+1;k<=n+window;k++){
      if(!PivotLow(k,n))continue;
      if(!lowerLow)return k;
      for(int p=k+1;p<=k+200;p++)if(PivotLow(p,n))return iLow(_Symbol,PERIOD_H1,k)<iLow(_Symbol,PERIOD_H1,p)?k:-1;
      return -1;
   }
   return -1;
}
int FreshHigh(int n,int window){
   for(int k=n+1;k<=n+window;k++)if(PivotHigh(k,n))return k;
   return -1;
}
int LatestLow(int n){for(int k=n+1;k<=n+200;k++)if(PivotLow(k,n))return k;return -1;}

bool HasPosition(){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}
   return false;
}

bool Open(bool buy,double stopPrice,double atr,string cm){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double entry=buy?q.ask:q.bid,dist=buy?entry-stopPrice:stopPrice-entry;
   dist=MathMax(dist,InpMinStopAtr*atr);
   double sl=Price(buy?entry-dist:entry+dist);
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
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){placeFails++;PrintFormat("EUR8_PLACE_FAIL %s code=%u",cm,trade.ResultRetcode());return false;}
   PrintFormat("EUR8_ENTRY %s entry=%.5f sl=%.5f atr=%.5f stop_atr=%.2f lots=%.2f risk=%.2f",cm,entry,sl,atr,dist/atr,volume,goal);
   return true;
}

bool InTradeSession(){
   datetime now=TimeCurrent(),from=0,to=0;MqlDateTime d;TimeToStruct(now,d);long sec=(long)(now%86400);
   for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,from,to);i++)
      if(sec>=(long)from&&sec<(long)to)return true;
   return false;
}

void TimeExits(){
   datetime now=TimeCurrent();if(now-lastClose<30||!InTradeSession())return;
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol||PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      if(now-(datetime)PositionGetInteger(POSITION_TIME)<(long)InpHoldHours*3600)continue;
      lastClose=now;
      if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
         if(trade.ResultRetcode()!=TRADE_RETCODE_POSITION_CLOSED&&trade.ResultRetcode()!=TRADE_RETCODE_MARKET_CLOSED){closeFails++;PrintFormat("EUR8_CLOSE_FAIL code=%u",trade.ResultRetcode());}}
   }
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpHoldHours<=0||InpFractal<1||InpFreshWindow<1||InpMode<0||InpMode>3||InpRandomProb<0||InpRandomProb>1)return INIT_PARAMETERS_INCORRECT;
   hAtr=iATR(_Symbol,PERIOD_H1,InpAtrPeriod);if(hAtr==INVALID_HANDLE)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   MathSrand(InpRandomSeed);
   PrintFormat("EUR8_SPEC symbol=%s digits=%d contract=%.0f vol_min=%.2f step=%.2f clock=%d hour=%d mode=%d fractal=%d window=%d lower_low=%d hold=%d log=%d p=%.5f seed=%d",
               _Symbol,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),
               InpClock,InpEntryHour,InpMode,InpFractal,InpFreshWindow,InpRequireLowerLow,InpHoldHours,InpLogDrift,InpRandomProb,InpRandomSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   if(!InpLogDrift)TimeExits();
   datetime bar=iTime(_Symbol,PERIOD_H1,0);
   if(bar==0||bar==lastBar)return;
   lastBar=bar;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0)return;
   if(InpLogDrift&&driftBase>0&&bar>driftBase&&bar<=driftBase+8*3600&&(bar-driftBase)%3600==0)
      PrintFormat("EUR8_DRIFT base=%I64d h=%d bid=%.5f",(long)driftBase,(int)((bar-driftBase)/3600),q.bid);
   datetime loc=Local(bar);MqlDateTime l;TimeToStruct(loc,l);
   if(l.hour!=InpEntryHour||l.min!=0||l.day_of_week<1||l.day_of_week>5)return;
   datetime day=loc-loc%86400;if(day==lastDay)return;lastDay=day;days++;
   double atr=Atr();if(atr==EMPTY_VALUE||atr<=0)return;
   int kl=FreshLow(InpFractal,InpFreshWindow,InpRequireLowerLow),kh=FreshHigh(InpFractal,InpFreshWindow);
   if(kl>0)freshLow++;
   if(kh>0)freshHigh++;
   if(InpLogDrift){
      driftBase=bar;
      PrintFormat("EUR8_DRIFT base=%I64d h=0 bid=%.5f atr=%.5f low2=%d high2=%d low3=%d low2w4=%d low2ll=%d dow=%d",(long)bar,q.bid,atr,
                  FreshLow(2,1,false)>0,FreshHigh(2,1)>0,FreshLow(3,1,false)>0,FreshLow(2,4,false)>0,FreshLow(2,1,true)>0,l.day_of_week);
      return;
   }
   if(HasPosition())return;
   if(InpMode==0&&kl>0){
      if(Open(true,iLow(_Symbol,PERIOD_H1,kl)-InpStopBufferAtr*atr,atr,"EUR8 LOW"))entries++;
   }
   else if(InpMode==1&&kh>0){
      if(Open(false,iHigh(_Symbol,PERIOD_H1,kh)+InpStopBufferAtr*atr,atr,"EUR8 HIGH SHORT"))entries++;
   }
   else if(InpMode==2||(InpMode==3&&MathRand()/32768.0<InpRandomProb)){
      int k=LatestLow(InpFractal);
      if(k<0)noPivot++;
      double stop=k>0?iLow(_Symbol,PERIOD_H1,k)-InpStopBufferAtr*atr:q.ask;
      if(Open(true,stop,atr,InpMode==2?"EUR8 ALL":"EUR8 RNG"))entries++;
   }
}

void OnDeinit(const int reason){
   PrintFormat("EUR8_SUMMARY days=%I64d fresh_low=%I64d fresh_high=%I64d entries=%I64d no_pivot=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d close_fails=%I64d",
               days,freshLow,freshHigh,entries,noPivot,skippedStops,skippedMargin,placeFails,closeFails);
}
