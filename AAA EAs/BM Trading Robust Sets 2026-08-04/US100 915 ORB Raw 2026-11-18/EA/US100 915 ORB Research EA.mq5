#property strict
#property version "1.20"
#property description "Research only (2026-11-18). US100 9:15 NY ORB (pasted reel): M15, range = the 09:15 NY bar, body close beyond it, stop at the breakout candle,"
#property description "0.5R target, one trade a day, EMA 200 trend filter. RULES.md. Controls: random direction / random entry."
#include <Trade/Trade.mqh>

input int    InpRangeStartMin=555;     // NY minute of the range bar (09:15)
input int    InpFirstSignalMin=570;    // first signal bar open (09:30)
input int    InpLastSignalMin=930;     // last signal bar open (15:30, closes 15:45)
input double InpRewardRisk=0.5;
input int    InpTrendEMA=200;          // 0 = no trend filter
input int    InpBodyMode=0;            // 0 close beyond the edge, 1 whole body (open and close) beyond it
input int    InpFlatMin=-1;            // -1 hold to SL/TP; else close at the first tick >= this NY minute
input double InpMinRange=1.0;          // index points
input int    InpMaxTrades=1;           // trades per NY day (1 = the reel). Addendum 1: 3 with re-entry after a retest
input double InpAtrMult=0;             // Addendum 4: skip the day if range > this x ATR (0 = off)
input int    InpAtrPeriod=14;
input int    InpRetest=0;              // Addendum 1: 1 = after an entry, a new breakout needs a bar that trades back into the range first
input double InpRiskPercent=1.0;       // % of balance, lots rounded DOWN
input int    InpControl=0;             // 0 none, 1 random direction, 2 random entry (rate per bar, side of EMA)
input double InpRandomRate=0.05;
input int    InpSeed=1;
input int    InpServerUtcOffsetHours=0; // Exness server = UTC
input int    InpDeviationPoints=100;
input long   InpMagic=1811201;

CTrade g_trade; int hEma=INVALID_HANDLE,hAtr=INVALID_HANDLE; datetime g_last=0,g_lastClose=0;
int g_day=0,g_count=0; bool g_traded=false,g_rangeOk=false,g_armed=true; double g_hi=0,g_lo=0;
long g_volSkip=0,g_days=0,g_signals=0,g_filtered=0,g_entries=0,g_skipStop=0,g_skipLots=0,g_fails=0,g_flats=0;

datetime NthSunday(int year,int month,int n){MqlDateTime t={};t.year=year;t.mon=month;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
datetime NewYork(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;return utc-5*3600+((utc>=on&&utc<off)?3600:0);}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
int NyMin(datetime server){MqlDateTime n;TimeToStruct(NewYork(Utc(server)),n);return n.hour*60+n.min;}
int NyDay(datetime server){MqlDateTime n;TimeToStruct(NewYork(Utc(server)),n);return n.year*10000+n.mon*100+n.day;}
double Val(int h,int sh){double b[1];if(h==INVALID_HANDLE||CopyBuffer(h,0,sh,1,b)!=1)return EMPTY_VALUE;return b[0];}
bool HasPos(ulong &t){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong k=PositionGetTicket(i);if(k&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){t=k;return true;}}
   return false;
}
double Lots(ENUM_ORDER_TYPE type,double e,double sl){
   double one=0;if(!OrderCalcProfit(type,_Symbol,1.0,e,sl,one)||MathAbs(one)<=0)return 0;
   double raw=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0/MathAbs(one);
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double v=MathFloor(MathMin(raw,mx)/st+1e-9)*st;return (v<mn?0:v);
}
// dir +1/-1; slPrice = the stop level (MAIN) or 0 to use dist from the fill (controls)
bool Enter(int dir,double slPrice,double dist){
   MqlTick k;if(!SymbolInfoTick(_Symbol,k)||k.ask<=0||k.bid<=0)return false;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);double e=(dir>0?k.ask:k.bid);
   double sl=(slPrice>0?slPrice:e-dir*dist);
   if((dir>0&&sl>=k.bid)||(dir<0&&sl<=k.ask)){g_skipStop++;return false;}
   double r=MathAbs(e-sl),tp=NormalizeDouble(e+dir*InpRewardRisk*r,dg);sl=NormalizeDouble(sl,dg);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   double ref=(dir>0?k.bid:k.ask);if(MathAbs(ref-sl)<=gap||MathAbs(tp-ref)<=gap){g_skipStop++;return false;}
   double v=Lots(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,e,sl);if(v<=0){g_skipLots++;return false;}
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   bool ok=(dir>0?g_trade.Buy(v,_Symbol,0,sl,tp,"ORB915"):g_trade.Sell(v,_Symbol,0,sl,tp,"ORB915"));
   if(!ok||g_trade.ResultRetcode()!=TRADE_RETCODE_DONE){g_fails++;PrintFormat("ORB_FAIL code=%u",g_trade.ResultRetcode());return false;}
   g_entries++;
   PrintFormat("ORB_ENTRY %s lots=%.2f stop=%.2f spread=%.2f range=%.2f-%.2f",dir>0?"buy":"sell",v,r,(double)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)*_Point,g_lo,g_hi);
   return true;
}
void Took(){g_count++;g_armed=false;if(g_count>=InpMaxTrades)g_traded=true;}
void Flat(){
   if(InpFlatMin<0)return;ulong t;if(!HasPos(t))return;datetime now=TimeCurrent();if(now-g_lastClose<30)return;
   int openDay=NyDay((datetime)PositionGetInteger(POSITION_TIME));
   if(NyDay(now)==openDay&&NyMin(now)<InpFlatMin)return;
   g_lastClose=now;if(g_trade.PositionClose(t,InpDeviationPoints)&&g_trade.ResultRetcode()==TRADE_RETCODE_DONE)g_flats++;
}
int OnInit(){
   if(InpMaxTrades<1||InpRetest<0||InpRetest>1||InpRiskPercent<=0||InpRewardRisk<=0||InpControl<0||InpControl>2||InpBodyMode<0||InpBodyMode>1)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   if(InpTrendEMA>0||InpControl==2){hEma=iMA(_Symbol,PERIOD_M15,MathMax(1,InpTrendEMA>0?InpTrendEMA:200),0,MODE_EMA,PRICE_CLOSE);if(hEma==INVALID_HANDLE)return INIT_FAILED;}
   if(InpAtrMult>0){hAtr=iATR(_Symbol,PERIOD_M15,InpAtrPeriod);if(hAtr==INVALID_HANDLE)return INIT_FAILED;}
   g_trade.SetTypeFillingBySymbol(_Symbol);g_trade.SetDeviationInPoints(InpDeviationPoints);MathSrand(InpSeed);
   PrintFormat("ORB_SPEC symbol=%s digits=%d point=%.5f contract=%.2f vol_min=%.2f step=%.2f rr=%.2f ema=%d body=%d flat=%d control=%d rate=%.4f seed=%d",_Symbol,_Digits,_Point,
      SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),InpRewardRisk,InpTrendEMA,InpBodyMode,InpFlatMin,InpControl,InpRandomRate,InpSeed);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r){
   PrintFormat("ORB_SUMMARY vol_skip=%I64d days=%I64d signals=%I64d filtered=%I64d entries=%I64d skip_stop=%I64d skip_lots=%I64d fails=%I64d flats=%I64d",g_volSkip,g_days,g_signals,g_filtered,g_entries,g_skipStop,g_skipLots,g_fails,g_flats);
}
void OnTick(){
   Flat();
   datetime b0=iTime(_Symbol,PERIOD_M15,0);if(b0<=0||b0==g_last)return;g_last=b0;
   datetime b1=iTime(_Symbol,PERIOD_M15,1);if(b1<=0)return;
   int day=NyDay(b1),m=NyMin(b1);
   if(day!=g_day){g_day=day;g_traded=false;g_count=0;g_armed=true;g_rangeOk=false;g_hi=0;g_lo=0;g_days++;}
   if(m==InpRangeStartMin){                                   // the 09:15 bar just closed: it is the range
      double h=iHigh(_Symbol,PERIOD_M15,1),l=iLow(_Symbol,PERIOD_M15,1);
      g_rangeOk=(h-l>=InpMinRange);if(g_rangeOk){g_hi=h;g_lo=l;}
      if(g_rangeOk&&InpAtrMult>0){double a=Val(hAtr,1);if(a==EMPTY_VALUE||h-l>InpAtrMult*a){g_rangeOk=false;g_volSkip++;}}   // Addendum 4
      return;
   }
   if(!g_rangeOk||g_traded||m<InpFirstSignalMin||m>InpLastSignalMin)return;
   double o=iOpen(_Symbol,PERIOD_M15,1),c=iClose(_Symbol,PERIOD_M15,1),h=iHigh(_Symbol,PERIOD_M15,1),l=iLow(_Symbol,PERIOD_M15,1);
   if(InpRetest==1&&!g_armed&&l<=g_hi&&h>=g_lo)g_armed=true;   // Addendum 1: price came back into the range = retest
   ulong t;if(HasPos(t))return;                              // one position at a time (a held trade from an earlier day blocks today)
   if(InpRetest==1&&!g_armed)return;
   double ema=(hEma!=INVALID_HANDLE?Val(hEma,1):EMPTY_VALUE);
   if(InpControl==2){                                         // random entry control: random bar in the window, side of EMA 200, stop = that bar's range
      if(ema==EMPTY_VALUE||c==ema||MathRand()/32767.0>=InpRandomRate)return;
      int side=(c>ema?1:-1);
      if(Enter(side,0,MathMax(h-l,InpMinRange)))Took();
      return;
   }
   bool up=(InpBodyMode==1?MathMin(o,c)>g_hi:c>g_hi),dn=(InpBodyMode==1?MathMax(o,c)<g_lo:c<g_lo);
   if(!up&&!dn)return;
   g_signals++;
   int dir=(up?1:-1);
   if(InpTrendEMA>0){if(ema==EMPTY_VALUE||(dir>0&&c<=ema)||(dir<0&&c>=ema)){g_filtered++;return;}}
   double sl=(dir>0?l:h);
   if(InpControl==1){                                         // random direction: same stop distance from the fill
      MqlTick k;if(!SymbolInfoTick(_Symbol,k))return;
      double dist=MathAbs((dir>0?k.ask:k.bid)-sl);dir=((MathRand()&1)==1?1:-1);
      if(dist>0&&Enter(dir,0,dist))Took();
      return;
   }
   if(Enter(dir,sl,0))Took();
}
