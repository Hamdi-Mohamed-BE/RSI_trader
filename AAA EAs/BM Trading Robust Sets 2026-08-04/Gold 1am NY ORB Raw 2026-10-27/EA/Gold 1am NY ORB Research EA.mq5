#property strict
#property version "1.10"
#property description "Research only (2026-10-27). Gold 1am New York ORB from a pasted clip: 01:00-01:15 NY range, 5m close beyond it 01:15-03:40,"
#property description "stop at the opposite edge, 0.5R target, max 2 trades/day (one per direction), reverse, force close 06:00 NY. Rules: RULES.md."
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;         // % of equity per trade; lots rounded UP to the step (minimum lot if needed)
input double InpRewardRisk=0.5;
input bool   InpReverse=true;
input double InpMaxLots=2.0;             // clip: 20 MGC contracts = 2.0 lots XAUUSD
input int    InpRandomMode=0;            // control: 0 off; 1 random direction at every signal (same stop distance / RR)
input int    InpRandomSeed=1;
input double InpMinRangePoints=10;
input int    InpVolFilter=0;          // Addendum 1: 0 off; 1 width >= K*ATR(D1); 2 width <= K*ATR(D1); 3 ATR(D1) > 50-day median; 4 ATR(D1) < median
input double InpVolK=0.10;
input int    InpServerUtcOffsetHours=0;  // Exness server = UTC
input int    InpMaximumDeviationPoints=1000;
input long   InpMagic=2710280;

CTrade trade;
int hAtrD1=INVALID_HANDLE;long volSkipped=0;
datetime lastBar=0,lastClose=0;
int rangeDay=0,tradesToday=0;bool longUsed=false,shortUsed=false;double rHigh=0,rLow=0;bool rangeOk=false;
long days=0,signals=0,entries=0,reverses=0,forceCloses=0,skippedStops=0,skippedMargin=0,placeFails=0,marketClosed=0,closeFails=0;

datetime NthSunday(int year,int month,int n){MqlDateTime t={};t.year=year;t.mon=month;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
datetime NewYork(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;return utc-5*3600+((utc>=on&&utc<off)?3600:0);}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
int NyMinutes(datetime server){MqlDateTime n;TimeToStruct(NewYork(Utc(server)),n);return n.hour*60+n.min;}
int NyDay(datetime server){MqlDateTime n;TimeToStruct(NewYork(Utc(server)),n);return n.year*10000+n.mon*100+n.day;}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}

bool OwnPosition(ulong &ticket,bool &buy){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=t;buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;return true;}}
   return false;
}

bool Open(bool buy,double sl){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double entry=buy?q.ask:q.bid,dist=MathAbs(entry-sl);
   if((buy&&sl>=q.bid)||(!buy&&sl<=q.ask)){skippedStops++;return false;}    // price already beyond the stop
   double tp=Price(buy?entry+InpRewardRisk*dist:entry-InpRewardRisk*dist);sl=Price(sl);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   double ref=buy?q.bid:q.ask;
   if(MathAbs(ref-sl)<=gap||MathAbs(tp-ref)<=gap){skippedStops++;return false;}
   double unit=0,margin=0;ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeDouble(MathMin(InpMaxLots,MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step)),8);
   if(!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   trade.SetExpertMagicNumber(InpMagic);
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,tp,"GORB1"):trade.Sell(volume,_Symbol,0,sl,tp,"GORB1");
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){if(trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED)marketClosed++;else{placeFails++;PrintFormat("GORB_PLACE_FAIL code=%u",trade.ResultRetcode());}return false;}
   entries++;PrintFormat("GORB_ENTRY %s entry=%.2f sl=%.2f tp=%.2f range=%.2f-%.2f lots=%.2f risk=%.2f",buy?"buy":"sell",entry,sl,tp,rLow,rHigh,volume,goal);
   return true;
}

bool VolOk(double width){                               // Addendum 1 filters; ATR(14) D1 of yesterday (shift 1)
   double a[];if(CopyBuffer(hAtrD1,0,1,50,a)!=50)return false;
   double atr=a[49];
   if(InpVolFilter==1)return width>=InpVolK*atr;
   if(InpVolFilter==2)return width<=InpVolK*atr;
   ArraySort(a);double med=(a[24]+a[25])/2;
   return InpVolFilter==3?atr>med:atr<med;
}

void ForceClose(){
   ulong t;bool buy;if(!OwnPosition(t,buy))return;
   datetime now=TimeCurrent();if(now-lastClose<30)return;
   int openDay=NyDay((datetime)PositionGetInteger(POSITION_TIME)),today=NyDay(now);
   if(today==openDay&&NyMinutes(now)<6*60)return;           // close at the first tick >= 06:00 NY (or on a later NY day after a gap)
   lastClose=now;
   if(trade.PositionClose(t)&&trade.ResultRetcode()==TRADE_RETCODE_DONE)forceCloses++;
   else if(trade.ResultRetcode()!=TRADE_RETCODE_MARKET_CLOSED)closeFails++;
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpRewardRisk<=0||InpRandomMode<0||InpRandomMode>1)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);MathSrand(InpRandomSeed);
   if(InpVolFilter<0||InpVolFilter>4)return INIT_PARAMETERS_INCORRECT;
   if(InpVolFilter>0){hAtrD1=iATR(_Symbol,PERIOD_D1,14);if(hAtrD1==INVALID_HANDLE)return INIT_FAILED;}
   PrintFormat("GORB_SPEC symbol=%s digits=%d contract=%.2f vol_min=%.2f step=%.2f stops_level=%d rr=%.2f reverse=%d random=%d seed=%d",_Symbol,_Digits,
      SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),
      (int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),InpRewardRisk,InpReverse,InpRandomMode,InpRandomSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   ForceClose();
   datetime bar=iTime(_Symbol,PERIOD_M5,0);
   if(bar==0||bar==lastBar)return;
   lastBar=bar;
   datetime prev=iTime(_Symbol,PERIOD_M5,1);if(prev==0)return;
   int day=NyDay(prev),mins=NyMinutes(prev);
   if(day!=rangeDay){rangeDay=day;tradesToday=0;longUsed=false;shortUsed=false;rangeOk=false;rHigh=0;rLow=0;days++;}
   if(mins==1*60+10){                                      // the 01:10 bar just closed: range = 01:00, 01:05, 01:10 bars
      double h=-1,l=1e18;int n=0;
      for(int i=1;i<=3;i++){datetime t=iTime(_Symbol,PERIOD_M5,i);if(t==0||NyDay(t)!=day)continue;int m=NyMinutes(t);
         if(m>=60&&m<=70){h=MathMax(h,iHigh(_Symbol,PERIOD_M5,i));l=MathMin(l,iLow(_Symbol,PERIOD_M5,i));n++;}}
      rangeOk=n==3&&h-l>=InpMinRangePoints*_Point;if(rangeOk){rHigh=h;rLow=l;}
      if(rangeOk&&InpVolFilter>0&&!VolOk(h-l)){rangeOk=false;volSkipped++;}
      return;
   }
   if(!rangeOk||mins<75||mins>215||tradesToday>=2)return;  // signal bars opening 01:15..03:35 NY (closing by 03:40)
   double c=iClose(_Symbol,PERIOD_M5,1);
   bool up=c>rHigh,dn=c<rLow;if(!up&&!dn)return;
   signals++;
   bool buy=up;
   if(InpRandomMode==1)buy=(MathRand()%2==0);
   ulong t;bool posBuy;bool has=OwnPosition(t,posBuy);
   if(has){
      if(!InpReverse||posBuy==buy)return;
      if((buy&&longUsed)||(!buy&&shortUsed))return;
      if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;return;}
      reverses++;
   }
   if((buy&&longUsed)||(!buy&&shortUsed))return;
   double dist=rHigh-rLow,sl;
   if(InpRandomMode==1){MqlTick q;SymbolInfoTick(_Symbol,q);sl=buy?q.ask-dist:q.bid+dist;}     // control: same distance as the range
   else sl=buy?rLow:rHigh;
   if(Open(buy,sl)){tradesToday++;if(buy)longUsed=true;else shortUsed=true;}
}

void OnDeinit(const int reason){
   PrintFormat("GORB_SUMMARY days=%I64d signals=%I64d entries=%I64d reverses=%I64d force_closes=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d market_closed=%I64d close_fails=%I64d vol_skipped=%I64d",
               days,signals,entries,reverses,forceCloses,skippedStops,skippedMargin,placeFails,marketClosed,closeFails,volSkipped);
}
