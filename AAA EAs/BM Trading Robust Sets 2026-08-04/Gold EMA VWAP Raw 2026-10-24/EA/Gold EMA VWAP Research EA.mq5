#property strict
#property version "1.00"
#property description "Research only (2026-10-24). XAUUSD EMA + VWAP: A = EMA5/13 cross with VWAP/ADX/separation filters, stop at the"
#property description "EMA intersection, 2R; B = EMA9 crosses session VWAP with EMA9/21 trend and VWAP slope, 1.5 ATR stop, 2R. Rules: RULES.md."
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;         // % of equity per trade; lots rounded UP to the step (minimum lot if needed)
input int    InpMode=0;                  // 0 = A (EMA cross + VWAP filter); 1 = B (EMA crosses VWAP)
input int    InpFastEMA=5;
input int    InpSlowEMA=13;
input bool   InpUseVwapFilter=true;      // A: long only above VWAP, short only below
input bool   InpUseAdx=true;             // A
input int    InpAdxPeriod=14;
input double InpAdxMin=20.0;
input bool   InpUseSeparation=true;      // A: |fast - slow| >= InpSepAtr * ATR at the signal bar
input double InpSepAtr=0.10;
input bool   InpUseTrend=true;           // B: fast EMA above / below slow EMA
input bool   InpUseSlope=true;           // B: |VWAP[1] - VWAP[2]| / VWAP[2] >= InpSlopePct %
input double InpSlopePct=0.01;
input int    InpStopMode=0;              // 0 = EMA intersection (A); 1 = ATR multiple (B)
input double InpStopAtr=1.5;
input double InpMinStopAtr=0.25;
input double InpRR=2.0;
input int    InpAtrPeriod=14;
input int    InpVwapAnchor=0;            // 0 = session (reset after a >= 30 min bar gap); 1 = server midnight
input bool   InpRandomDirection=false;   // control: same signal times, coin-flip direction
input int    InpRandomSeed=1;
input int    InpMaximumDeviationPoints=50;
input long   InpMagic=2410260;

CTrade trade;
int hFast=INVALID_HANDLE,hSlow=INVALID_HANDLE,hAtr=INVALID_HANDLE,hAdx=INVALID_HANDLE;
datetime lastBar=0;
long bars=0,signals=0,entries=0,busy=0,floors=0,sessionSkips=0,skippedStops=0,skippedMargin=0,placeFails=0,randomFlips=0;

double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
double Buf(int h,int buffer,int shift){double v[];if(CopyBuffer(h,buffer,shift,1,v)!=1)return EMPTY_VALUE;return v[0];}

bool NewSession(const MqlRates &newer,const MqlRates &older){
   if(InpVwapAnchor==1){MqlDateTime a,b;TimeToStruct(newer.time,a);TimeToStruct(older.time,b);return a.day_of_year!=b.day_of_year||a.year!=b.year;}
   return newer.time-older.time>=30*60;
}

// VWAP at closed bars 1 and 2 (series shifts), and whether bar 2 belongs to the same session as bar 1.
bool Vwap(double &v1,double &v2,bool &same){
   MqlRates r[];ArraySetAsSeries(r,true);
   int n=CopyRates(_Symbol,_Period,0,800,r);if(n<10)return false;
   int start1=-1;
   for(int i=1;i<n-1;i++)if(NewSession(r[i],r[i+1])){start1=i;break;}
   if(start1<0)return false;
   same=start1>=2;
   double pv=0,vol=0;
   for(int i=start1;i>=1;i--){
      double w=(double)r[i].tick_volume;if(w<=0)w=1;
      pv+=(r[i].high+r[i].low+r[i].close)/3.0*w;vol+=w;
      if(i==2)v2=pv/vol;
   }
   v1=pv/vol;
   if(!same)v2=v1;
   return vol>0;
}

bool HasPosition(){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}
   return false;
}

// dist = signal's stop distance from the signal side's entry; the same distance is used if the control flips direction.
bool Open(bool buy,double dist,double atr,string cm){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   if(dist<InpMinStopAtr*atr){dist=InpMinStopAtr*atr;floors++;}
   double entry=buy?q.ask:q.bid;
   double sl=Price(buy?entry-dist:entry+dist),tp=Price(buy?entry+InpRR*dist:entry-InpRR*dist);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   if((buy&&q.bid-sl<=gap)||(!buy&&sl-q.ask<=gap)){skippedStops++;return false;}
   ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;double unit=0,margin=0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeDouble(MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step),8);
   if(volume>mx||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   trade.SetExpertMagicNumber(InpMagic);
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,tp,cm):trade.Sell(volume,_Symbol,0,sl,tp,cm);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){placeFails++;PrintFormat("GEV_PLACE_FAIL %s code=%u",cm,trade.ResultRetcode());return false;}
   PrintFormat("GEV_ENTRY %s entry=%.2f sl=%.2f tp=%.2f atr=%.2f stop_atr=%.2f lots=%.2f risk=%.2f",cm,entry,sl,tp,atr,dist/atr,volume,goal);
   return true;
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpMode<0||InpMode>1||InpFastEMA<1||InpSlowEMA<=InpFastEMA||InpRR<=0||InpStopMode<0||InpStopMode>1||InpVwapAnchor<0||InpVwapAnchor>1)
      return INIT_PARAMETERS_INCORRECT;
   hFast=iMA(_Symbol,_Period,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);hSlow=iMA(_Symbol,_Period,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   hAtr=iATR(_Symbol,_Period,InpAtrPeriod);hAdx=iADX(_Symbol,_Period,InpAdxPeriod);
   if(hFast==INVALID_HANDLE||hSlow==INVALID_HANDLE||hAtr==INVALID_HANDLE||hAdx==INVALID_HANDLE)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   MathSrand(InpRandomSeed);
   PrintFormat("GEV_SPEC symbol=%s tf=%s digits=%d contract=%.0f vol_min=%.2f step=%.2f mode=%d ema=%d/%d vwapf=%d adx=%d sep=%d trend=%d slope=%d stop=%d stop_atr=%.2f rr=%.2f anchor=%d random=%d seed=%d",
               _Symbol,EnumToString(_Period),_Digits,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),
               InpMode,InpFastEMA,InpSlowEMA,InpUseVwapFilter,InpUseAdx,InpUseSeparation,InpUseTrend,InpUseSlope,InpStopMode,InpStopAtr,InpRR,InpVwapAnchor,InpRandomDirection,InpRandomSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime bar=iTime(_Symbol,_Period,0);
   if(bar==0||bar==lastBar)return;
   lastBar=bar;bars++;
   MqlDateTime d;TimeToStruct(bar,d);if(d.day_of_week<1||d.day_of_week>5)return;
   double f1=Buf(hFast,0,1),f2=Buf(hFast,0,2),s1=Buf(hSlow,0,1),s2=Buf(hSlow,0,2),atr=Buf(hAtr,0,1);
   if(f1==EMPTY_VALUE||f2==EMPTY_VALUE||s1==EMPTY_VALUE||s2==EMPTY_VALUE||atr==EMPTY_VALUE||atr<=0)return;
   double v1=0,v2=0;bool same=false;if(!Vwap(v1,v2,same))return;
   double c1=iClose(_Symbol,_Period,1);
   int dir=0;double dist=0;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   if(InpMode==0){
      bool up=f2<=s2&&f1>s1,dn=f2>=s2&&f1<s1;if(!up&&!dn)return;
      if(InpUseVwapFilter&&((up&&!(c1>v1))||(dn&&!(c1<v1))))return;
      if(InpUseAdx){double adx=Buf(hAdx,0,1);if(adx==EMPTY_VALUE||adx<InpAdxMin)return;}
      if(InpUseSeparation&&MathAbs(f1-s1)<InpSepAtr*atr)return;
      dir=up?1:-1;
      double den=(f1-f2)-(s1-s2),x=den!=0?(s2-f2)/den:1.0;x=MathMax(0.0,MathMin(1.0,x));
      double cross=f2+x*(f1-f2);
      dist=InpStopMode==0?(dir>0?q.ask-cross:cross-q.bid):InpStopAtr*atr;
   }
   else{
      if(!same){bool any=(f2<=v2&&f1>v1)||(f2>=v2&&f1<v1);if(any)sessionSkips++;return;}
      bool up=f2<=v2&&f1>v1,dn=f2>=v2&&f1<v1;if(!up&&!dn)return;
      if(InpUseTrend&&((up&&!(f1>s1))||(dn&&!(f1<s1))))return;
      if(InpUseSlope&&(v2<=0||MathAbs(v1-v2)/v2*100.0<InpSlopePct))return;
      dir=up?1:-1;
      dist=InpStopMode==1?InpStopAtr*atr:(dir>0?q.ask-(f2+s2)/2:(f2+s2)/2-q.bid);
   }
   signals++;
   if(HasPosition()){busy++;return;}
   if(InpRandomDirection){int flip=MathRand()%2;if(flip==1){dir=-dir;randomFlips++;}}
   if(Open(dir>0,dist,atr,(InpMode==0?"GEV A":"GEV B")+(InpRandomDirection?" RND":"")+(dir>0?" L":" S")))entries++;
}

void OnDeinit(const int reason){
   PrintFormat("GEV_SUMMARY bars=%I64d signals=%I64d entries=%I64d busy=%I64d floors=%I64d session_skips=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d random_flips=%I64d",
               bars,signals,entries,busy,floors,sessionSkips,skippedStops,skippedMargin,placeFails,randomFlips);
}
