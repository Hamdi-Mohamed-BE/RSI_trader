#property strict
#property version "1.00"
#property description "Research only (2026-11-11). CRT Alpha sweep setup (NINZA video + product page) on USTEC: M15 C1 body >= 50%, C2 sweeps CRH/CRL and closes back inside,"
#property description "C3 window: price tests premium/discount (midline), MAIN = on a Renko reversal brick (4.5 / 0.75 points). TP opposite boundary, SL beyond the wick. RULES.md."
#include <Trade/Trade.mqh>

input bool   InpUseRenko=true;          // MAIN: signal only on a reversal brick that touched the zone; false = PLAIN (first zone touch)
input double InpReversalPoints=4.5;     // ninZaRenko 18 ticks x 0.25 (ASSUMPTION)
input double InpTrendPoints=0.75;       // ninZaRenko 3 ticks x 0.25 (ASSUMPTION)
input double InpBodyMinPct=50.0;        // C1 body >= this % of its range (page)
input double InpStopBufferPoints=0.5;   // beyond the sweep wick
input int    InpSession=0;              // 0 all hours, 1 New York 09:30-16:00 ET
input double InpRiskPercent=1.0;        // % of equity; lots rounded UP to the step (broker minimum if needed)
input int    InpRandomMode=0;           // control: 1 = random direction at each trigger, same TP/SL distances
input int    InpRandomSeed=1;
input int    InpServerUtcOffsetHours=0; // Exness server = UTC
input int    InpMaximumDeviationPoints=1000;
input long   InpMagic=2911110;

CTrade trade;
datetime lastHtf=0,c3Start=0,c3End=0;
bool armed=false,aSell=false;double crh=0,crl=0,mid=0,aSL=0,aTP=0;
// Renko state (bid)
double rkClose=0,formHi=0,formLo=0;int rkDir=0;bool rkInit=false;
long setups=0,bodyRejected=0,colorRejected=0,triggers=0,expired=0,sessionBlocked=0,posBlocked=0,skippedStops=0,skippedMargin=0,placeFails=0,marketClosed=0,entries=0,revUp=0,revDown=0,outsideRange=0;

datetime NthSunday(int year,int month,int n){MqlDateTime t={};t.year=year;t.mon=month;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
datetime NewYork(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;return utc-5*3600+((utc>=on&&utc<off)?3600:0);}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
int NyMinutes(datetime s){MqlDateTime n;TimeToStruct(NewYork(Utc(s)),n);return n.hour*60+n.min;}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
bool InSession(datetime s){if(InpSession==0)return true;int m=NyMinutes(s);return m>=570&&m<960;}

bool HasPosition(){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}
   return false;
}

// Renko on bid: trend bricks continue the direction every InpTrendPoints; a reversal brick needs InpReversalPoints against the last brick close.
// Returns +1 if an UP reversal brick completed on this tick, -1 for a DOWN reversal brick, 0 otherwise. hiOut/loOut = extremes of the forming brick.
int RenkoUpdate(double p,double &hiOut,double &loOut){
   if(!rkInit){rkClose=p;rkDir=0;formHi=p;formLo=p;rkInit=true;return 0;}
   formHi=MathMax(formHi,p);formLo=MathMin(formLo,p);hiOut=formHi;loOut=formLo;
   int ev=0;bool brick=false;
   if(rkDir>=0){
      while(p>=rkClose+InpTrendPoints){rkClose+=InpTrendPoints;rkDir=1;brick=true;}
      if(rkDir==1&&p<=rkClose-InpReversalPoints){rkClose-=InpReversalPoints;rkDir=-1;ev=-1;brick=true;revDown++;while(p<=rkClose-InpTrendPoints)rkClose-=InpTrendPoints;}
      else if(rkDir==0&&p<=rkClose-InpTrendPoints){rkDir=-1;while(p<=rkClose-InpTrendPoints)rkClose-=InpTrendPoints;brick=true;}
   }
   else{
      while(p<=rkClose-InpTrendPoints){rkClose-=InpTrendPoints;brick=true;}
      if(p>=rkClose+InpReversalPoints){rkClose+=InpReversalPoints;rkDir=1;ev=1;brick=true;revUp++;while(p>=rkClose+InpTrendPoints)rkClose+=InpTrendPoints;}
   }
   if(brick){formHi=p;formLo=p;}
   return ev;
}

void Arm(){
   armed=false;
   double o1=iOpen(_Symbol,PERIOD_M15,2),h1=iHigh(_Symbol,PERIOD_M15,2),l1=iLow(_Symbol,PERIOD_M15,2),c1=iClose(_Symbol,PERIOD_M15,2);
   double h2=iHigh(_Symbol,PERIOD_M15,1),l2=iLow(_Symbol,PERIOD_M15,1),c2=iClose(_Symbol,PERIOD_M15,1);
   if(h1<=0||h2<=0||h1<=l1)return;
   bool sell=h2>h1&&c2<h1&&c2>l1&&l2>=l1, buy=l2<l1&&c2>l1&&c2<h1&&h2<=h1;
   if(sell==buy)return;                                       // none, or both sides swept
   setups++;
   if(MathAbs(c1-o1)<InpBodyMinPct/100.0*(h1-l1)){bodyRejected++;return;}
   if((sell&&c1<=o1)||(buy&&c1>=o1)){colorRejected++;return;}
   crh=h1;crl=l1;mid=(h1+l1)/2.0;aSell=sell;
   aSL=sell?h2+InpStopBufferPoints:l2-InpStopBufferPoints;aTP=sell?crl:crh;
   c3Start=iTime(_Symbol,PERIOD_M15,0);c3End=c3Start+PeriodSeconds(PERIOD_M15);armed=true;
}

bool Open(bool buy,double sl,double tp){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double entry=buy?q.ask:q.bid;
   if((buy&&(sl>=q.bid||tp<=q.ask))||(!buy&&(sl<=q.ask||tp>=q.bid))){skippedStops++;return false;}
   sl=Price(sl);tp=Price(tp);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   double ref=buy?q.bid:q.ask;
   if(MathAbs(ref-sl)<=gap||MathAbs(tp-ref)<=gap){skippedStops++;return false;}
   double unit=0,margin=0;ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeDouble(MathMin(mx,MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step)),8);
   if(!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   trade.SetExpertMagicNumber(InpMagic);
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,tp,"CRTA"):trade.Sell(volume,_Symbol,0,sl,tp,"CRTA");
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){if(trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED)marketClosed++;else{placeFails++;PrintFormat("CRTA_PLACE_FAIL code=%u",trade.ResultRetcode());}return false;}
   entries++;
   PrintFormat("CRTA_ENTRY %s entry=%.2f crh=%.2f crl=%.2f mid=%.2f sl=%.2f tp=%.2f lots=%.2f risk=%.2f renko=%d",buy?"buy":"sell",entry,crh,crl,mid,sl,tp,volume,goal,InpUseRenko);
   return true;
}

void Trigger(){
   triggers++;armed=false;
   datetime now=TimeCurrent();
   if(!InSession(now)){sessionBlocked++;return;}
   if(HasPosition()){posBlocked++;return;}
   bool buy=!aSell;double sl=aSL,tp=aTP;
   if(InpRandomMode==1&&(MathRand()%2==1)){                  // control: opposite direction, same distances from the fill
      MqlTick q;SymbolInfoTick(_Symbol,q);double e0=buy?q.ask:q.bid,rw=MathAbs(tp-e0),rk=MathAbs(e0-sl);
      buy=!buy;double e=buy?q.ask:q.bid;tp=buy?e+rw:e-rw;sl=buy?e-rk:e+rk;
   }
   Open(buy,sl,tp);
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpReversalPoints<=0||InpTrendPoints<=0||InpSession<0||InpSession>1)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   if(_Period!=PERIOD_M1)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);MathSrand(InpRandomSeed);
   PrintFormat("CRTA_SPEC symbol=%s digits=%d vol_min=%.2f step=%.2f stops_level=%d renko=%d rev=%.2f trend=%.2f body=%.0f buf=%.2f session=%d random=%d seed=%d",
      _Symbol,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
      InpUseRenko,InpReversalPoints,InpTrendPoints,InpBodyMinPct,InpStopBufferPoints,InpSession,InpRandomMode,InpRandomSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0)return;
   double bhi=q.bid,blo=q.bid;int ev=RenkoUpdate(q.bid,bhi,blo);
   datetime b=iTime(_Symbol,PERIOD_M15,0);
   if(b!=0&&b!=lastHtf){if(armed)expired++;lastHtf=b;Arm();}
   if(!armed)return;
   if(TimeCurrent()>=c3End){armed=false;expired++;return;}
   bool fire=false;
   if(InpUseRenko){
      if(aSell&&ev==-1&&bhi>=mid)fire=true;                   // bearish reversal brick that touched the premium zone
      if(!aSell&&ev==1&&blo<=mid)fire=true;                   // bullish reversal brick that touched the discount zone
   }
   else fire=aSell?q.bid>=mid:q.ask<=mid;
   if(!fire)return;
   if((aSell&&q.bid>=aSL)||(!aSell&&q.ask<=aSL)){outsideRange++;armed=false;return;}
   Trigger();
}

void OnDeinit(const int reason){
   PrintFormat("CRTA_SUMMARY setups=%I64d body_rejected=%I64d color_rejected=%I64d triggers=%I64d expired=%I64d session_blocked=%I64d position_blocked=%I64d outside_range=%I64d entries=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d market_closed=%I64d rev_up=%I64d rev_down=%I64d",
      setups,bodyRejected,colorRejected,triggers,expired,sessionBlocked,posBlocked,outsideRange,entries,skippedStops,skippedMargin,placeFails,marketClosed,revUp,revDown);
}
