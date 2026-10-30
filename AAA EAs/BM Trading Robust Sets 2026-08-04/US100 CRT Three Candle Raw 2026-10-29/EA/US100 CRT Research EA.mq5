#property strict
#property version "1.00"
#property description "Research only (2026-10-29). CRT three-candle setup from a pasted interview: C2 sweeps C1's low/high and closes back inside,"
#property description "C3 breaks C2's high/low (direct or rebreak), TP = C1's opposite extreme, SL for 1.5R, NY 09:30-12:00 ET, first trigger of the day. RULES.md."
#include <Trade/Trade.mqh>

input int    InpTimeframe=0;            // 0 = ALL (first of M15/M30/H1), 15, 30, 60
input int    InpEntryMode=1;            // 0 DIRECT (first break), 1 REBREAK (break, M1 close back through, break again)
input bool   InpUseBias=true;           // H1 sweep/break bias (RULES.md)
input int    InpSession=0;              // 0 New York 09:30-12:00 ET, 1 Asia 20:00-22:00 ET
input int    InpMaxTradesPerDay=1;
input bool   InpSkipMonday=false;
input double InpRewardRisk=1.5;
input double InpRiskPercent=1.0;        // % of equity; lots rounded UP to the step (broker minimum if needed)
input int    InpRandomMode=0;           // control: 1 = random direction at each trigger, same TP/SL distances
input int    InpRandomSeed=1;
input int    InpServerUtcOffsetHours=0; // Exness server = UTC
input int    InpMaximumDeviationPoints=1000;
input long   InpMagic=2910290;

CTrade trade;
ENUM_TIMEFRAMES TFS[3]={PERIOD_M15,PERIOD_M30,PERIOD_H1};
bool use[3];datetime lastHtf[3];
bool armed[3],abuy[3];double aL[3],aTP[3],aSL[3];datetime aEnd[3],aStart[3];int stage[3];
datetime lastM1=0,lastH1=0;int bias=0;double swHi=0,swLo=0;
int curDay=0,tradesToday=0;
long setups[3],triggers[3],expired[3],biasBlocked=0,posBlocked=0,sessionBlocked=0,skippedStops=0,skippedMargin=0,placeFails=0,marketClosed=0,entries=0,biasEvents=0;

datetime NthSunday(int year,int month,int n){MqlDateTime t={};t.year=year;t.mon=month;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
datetime NewYork(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;return utc-5*3600+((utc>=on&&utc<off)?3600:0);}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
int NyMinutes(datetime s){MqlDateTime n;TimeToStruct(NewYork(Utc(s)),n);return n.hour*60+n.min;}
int NyDay(datetime s){MqlDateTime n;TimeToStruct(NewYork(Utc(s)),n);return n.year*10000+n.mon*100+n.day;}
int NyWeekday(datetime s){MqlDateTime n;TimeToStruct(NewYork(Utc(s)),n);return n.day_of_week;}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
bool InSession(datetime s){int m=NyMinutes(s);return InpSession==0?(m>=570&&m<720):(m>=1200&&m<1320);}

bool HasPosition(){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}
   return false;
}

void UpdateBias(){                                           // on each new H1 bar: confirmed 2+2 fractal swings, then sweep / break events
   datetime h=iTime(_Symbol,PERIOD_H1,0);if(h==0||h==lastH1)return;lastH1=h;
   double hi[],lo[],cl[];
   if(CopyHigh(_Symbol,PERIOD_H1,1,5,hi)!=5||CopyLow(_Symbol,PERIOD_H1,1,5,lo)!=5||CopyClose(_Symbol,PERIOD_H1,1,1,cl)!=1)return;
   // arrays are oldest-first: index 0 = shift 5 ... index 4 = shift 1; the fractal candidate is shift 3 = index 2
   if(hi[2]>hi[0]&&hi[2]>hi[1]&&hi[2]>hi[3]&&hi[2]>hi[4])swHi=hi[2];
   if(lo[2]<lo[0]&&lo[2]<lo[1]&&lo[2]<lo[3]&&lo[2]<lo[4])swLo=lo[2];
   double H=hi[4],L=lo[4],C=cl[0];int before=bias;
   if(swLo>0&&L<swLo&&C>swLo)bias=1;
   else if(swHi>0&&H>swHi&&C<swHi)bias=-1;
   else if(swLo>0&&C<swLo)bias=-1;
   else if(swHi>0&&C>swHi)bias=1;
   if(bias!=before)biasEvents++;
}

void Arm(int k){                                             // a new HTF bar opened on TFS[k]: C2 = shift 1, C1 = shift 2, C3 = shift 0
   ENUM_TIMEFRAMES tf=TFS[k];
   double h1=iHigh(_Symbol,tf,2),l1=iLow(_Symbol,tf,2),h2=iHigh(_Symbol,tf,1),l2=iLow(_Symbol,tf,1),c2=iClose(_Symbol,tf,1);
   armed[k]=false;stage[k]=0;
   if(h1<=0||h2<=0)return;
   bool bull=l2<l1&&c2>l1&&c2<h1&&h2<h1, bear=h2>h1&&c2<h1&&c2>l1&&l2>l1;
   if(bull==bear)return;                                     // none, or both sides swept
   setups[k]++;
   if(InpUseBias&&((bull&&bias!=1)||(bear&&bias!=-1))){biasBlocked++;return;}
   double L=bull?h2:l2,TP=bull?h1:l1,dist=MathAbs(TP-L);if(dist<=0)return;
   armed[k]=true;abuy[k]=bull;aL[k]=L;aTP[k]=TP;aSL[k]=bull?L-dist/InpRewardRisk:L+dist/InpRewardRisk;
   aStart[k]=iTime(_Symbol,tf,0);aEnd[k]=aStart[k]+PeriodSeconds(tf);
}

bool Open(int k,bool buy,double sl,double tp){
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
   string cm=StringFormat("CRT%d",(int)(PeriodSeconds(TFS[k])/60));
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,tp,cm):trade.Sell(volume,_Symbol,0,sl,tp,cm);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){if(trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED)marketClosed++;else{placeFails++;PrintFormat("CRT_PLACE_FAIL code=%u",trade.ResultRetcode());}return false;}
   entries++;
   PrintFormat("CRT_ENTRY tf=M%d %s entry=%.2f L=%.2f sl=%.2f tp=%.2f lots=%.2f risk=%.2f mode=%d",(int)(PeriodSeconds(TFS[k])/60),buy?"buy":"sell",entry,aL[k],sl,tp,volume,goal,InpEntryMode);
   return true;
}

void Trigger(int k){
   triggers[k]++;
   datetime now=TimeCurrent();
   if(!InSession(now)){sessionBlocked++;return;}             // the trigger time must be inside the session window
   if(HasPosition()){posBlocked++;return;}
   bool buy=abuy[k];double sl=aSL[k],tp=aTP[k];
   if(InpRandomMode==1&&(MathRand()%2==1)){                  // control: opposite direction, same distances from the fill
      MqlTick q;SymbolInfoTick(_Symbol,q);double rw=MathAbs(aTP[k]-aL[k]),rk=MathAbs(aL[k]-aSL[k]);
      buy=!buy;double e=buy?q.ask:q.bid;tp=buy?e+rw:e-rw;sl=buy?e-rk:e+rk;
   }
   if(Open(k,buy,sl,tp)){
      tradesToday++;
      if(tradesToday>=InpMaxTradesPerDay)for(int j=0;j<3;j++)armed[j]=false;    // first trigger of the day wins; the rest are cancelled
   }
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpRewardRisk<=0||InpEntryMode<0||InpEntryMode>1||InpSession<0||InpSession>1||InpMaxTradesPerDay<1)return INIT_PARAMETERS_INCORRECT;
   if(InpTimeframe!=0&&InpTimeframe!=15&&InpTimeframe!=30&&InpTimeframe!=60)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   if(_Period!=PERIOD_M1)return INIT_FAILED;
   use[0]=InpTimeframe==0||InpTimeframe==15;use[1]=InpTimeframe==0||InpTimeframe==30;use[2]=InpTimeframe==0||InpTimeframe==60;
   for(int k=0;k<3;k++){lastHtf[k]=0;armed[k]=false;setups[k]=0;triggers[k]=0;expired[k]=0;}
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);MathSrand(InpRandomSeed);
   PrintFormat("CRT_SPEC symbol=%s digits=%d vol_min=%.2f step=%.2f stops_level=%d tf=%d mode=%d bias=%d session=%d max=%d skipmon=%d rr=%.2f random=%d seed=%d",
      _Symbol,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
      InpTimeframe,InpEntryMode,InpUseBias,InpSession,InpMaxTradesPerDay,InpSkipMonday,InpRewardRisk,InpRandomMode,InpRandomSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime now=TimeCurrent();
   int day=NyDay(now);if(day!=curDay){curDay=day;tradesToday=0;}
   if(InpUseBias)UpdateBias();
   bool dayOpen=tradesToday<InpMaxTradesPerDay&&!(InpSkipMonday&&NyWeekday(now)==1);
   for(int k=0;k<3;k++){
      if(!use[k])continue;
      datetime b=iTime(_Symbol,TFS[k],0);
      if(b!=0&&b!=lastHtf[k]){
         if(armed[k])expired[k]++;
         lastHtf[k]=b;armed[k]=false;
         if(dayOpen)Arm(k);
      }
   }
   datetime m1=iTime(_Symbol,PERIOD_M1,0);bool newM1=m1!=0&&m1!=lastM1;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   for(int k=0;k<3;k++){
      if(!use[k]||!armed[k])continue;
      if(now>=aEnd[k]){armed[k]=false;expired[k]++;continue;}
      if(!dayOpen){armed[k]=false;continue;}
      if(InpEntryMode==1&&stage[k]==1&&newM1){                // pullback: an M1 bar inside C3 closed back through L
         datetime pb=iTime(_Symbol,PERIOD_M1,1);double c=iClose(_Symbol,PERIOD_M1,1);
         if(pb>=aStart[k]&&((abuy[k]&&c<aL[k])||(!abuy[k]&&c>aL[k])))stage[k]=2;
      }
      bool cross=abuy[k]?q.ask>=aL[k]:q.bid<=aL[k];
      if(!cross)continue;
      if(InpEntryMode==0||stage[k]==2){armed[k]=false;Trigger(k);}
      else if(stage[k]==0)stage[k]=1;                         // first break: wait for the pullback
   }
   if(newM1)lastM1=m1;
}

void OnDeinit(const int reason){
   PrintFormat("CRT_SUMMARY setups15=%I64d setups30=%I64d setups60=%I64d triggers15=%I64d triggers30=%I64d triggers60=%I64d expired15=%I64d expired30=%I64d expired60=%I64d bias_blocked=%I64d session_blocked=%I64d position_blocked=%I64d entries=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d market_closed=%I64d bias_events=%I64d",
      setups[0],setups[1],setups[2],triggers[0],triggers[1],triggers[2],expired[0],expired[1],expired[2],biasBlocked,sessionBlocked,posBlocked,entries,skippedStops,skippedMargin,placeFails,marketClosed,biasEvents);
}
