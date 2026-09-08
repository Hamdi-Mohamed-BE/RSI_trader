#property copyright "Calyx Volatility Compression Expansion research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_VC_SESSION { VC_ALL_DAY=0, VC_ASIA=1, VC_LONDON=2, VC_NEW_YORK=3, VC_OVERLAP=4, VC_LONDON_NEW_YORK=5 };
enum ENUM_VC_COMPRESSION { VC_ATR_RATIO=0, VC_BB_PERCENTILE=1, VC_NARROW_RANGE=2, VC_BB_KELTNER=3 };
enum ENUM_VC_CONFIRMATION { VC_CLOSE=0, VC_BODY=1, VC_VOLUME=2, VC_BODY_VOLUME=3 };
enum ENUM_VC_TREND { VC_TREND_NONE=0, VC_EMA50=1, VC_EMA200=2, VC_EMA50_200=3 };
enum ENUM_VC_DIRECTION { VC_BOTH=0, VC_LONG_ONLY=1, VC_SHORT_ONLY=2 };
enum ENUM_VC_STOP { VC_RANGE=0, VC_ATR=1, VC_SIGNAL=2, VC_SWING5=3 };
enum ENUM_VC_MANAGEMENT { VC_NONE=0, VC_BREAKEVEN=1, VC_ATR_TRAIL=2, VC_DYNAMIC_M15_50_20=3 };

input group "Compression breakout signal"
input ENUM_TIMEFRAMES       InpSignalTimeframe=PERIOD_M30;
input ENUM_VC_SESSION       InpSession=VC_ALL_DAY;
input ENUM_VC_COMPRESSION   InpCompression=VC_ATR_RATIO;
input double                InpCompressionValue=0.65;
input int                   InpRangeBars=12;
input int                   InpArmBars=6;
input double                InpBreakoutBufferATR=0.10;
input ENUM_VC_CONFIRMATION  InpConfirmation=VC_CLOSE;
input ENUM_VC_TREND         InpTrendFilter=VC_EMA50;
input ENUM_VC_DIRECTION     InpDirection=VC_BOTH;
input int                   InpMaximumTradesPerDay=2;

input group "Stop, target and management"
input int                   InpMaximumHoldBars=12;
input ENUM_VC_STOP          InpStopMode=VC_ATR;
input double                InpStopValue=1.25;
input double                InpRewardRisk=2.0;
input ENUM_VC_MANAGEMENT    InpManagement=VC_NONE;
input double                InpRiskPercent=1.0;

input group "Execution and safety"
input double                InpMaximumSpreadRiskPercent=20.0;
input int                   InpMaximumDeviationPoints=100;
input long                  InpMagic=969060600;
input bool                  InpTesterOnly=true;
input int                   InpTesterServerUTCOffsetHours=0;
input bool                  InpUseAutomaticLiveServerOffset=true;
input int                   InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_signal_bar=0;
datetime g_last_manage_bar=0;
datetime g_last_m15_bar=0;
int g_atr5=INVALID_HANDLE,g_atr14=INVALID_HANDLE,g_atr20=INVALID_HANDLE,g_atr50=INVALID_HANDLE;
int g_ema50=INVALID_HANDLE,g_ema200=INVALID_HANDLE;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime x={0};x.year=year;x.mon=month;x.day=1;x.hour=12;
   datetime first=StructToTime(x);TimeToStruct(first,x);
   return 1+((7-x.day_of_week)%7)+(occurrence-1)*7;
}

int LastSunday(const int year,const int month)
{
   MqlDateTime x={0};x.year=year;x.mon=month+1;x.day=1;x.hour=12;
   if(month==12){x.year=year+1;x.mon=1;}
   datetime last=StructToTime(x)-86400;TimeToStruct(last,x);return x.day-x.day_of_week;
}

int NewYorkUTCOffset(const datetime utc)
{
   MqlDateTime x;TimeToStruct(utc,x);MqlDateTime a={0},b={0};
   a.year=x.year;a.mon=3;a.day=NthSunday(x.year,3,2);a.hour=7;
   b.year=x.year;b.mon=11;b.day=NthSunday(x.year,11,1);b.hour=6;
   return (utc>=StructToTime(a) && utc<StructToTime(b) ? -4 : -5);
}

int LondonUTCOffset(const datetime utc)
{
   MqlDateTime x;TimeToStruct(utc,x);MqlDateTime a={0},b={0};
   a.year=x.year;a.mon=3;a.day=LastSunday(x.year,3);a.hour=1;
   b.year=x.year;b.mon=10;b.day=LastSunday(x.year,10);b.hour=1;
   return (utc>=StructToTime(a) && utc<StructToTime(b) ? 1 : 0);
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER))return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset)return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();if(server<=0)server=TimeCurrent();datetime utc=TimeGMT();
   if(utc<=0)return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime value){return value-ServerUTCOffsetSeconds();}

bool SessionAllows(const datetime server)
{
   datetime utc=ServerToUTC(server);MqlDateTime u,l,n;TimeToStruct(utc,u);
   TimeToStruct(utc+LondonUTCOffset(utc)*3600,l);TimeToStruct(utc+NewYorkUTCOffset(utc)*3600,n);
   int um=u.hour*60+u.min,lm=l.hour*60+l.min,nm=n.hour*60+n.min;
   bool asia=(um>=0 && um<480),london=(lm>=480 && lm<990),ny=(nm>=570 && nm<960),overlap=(london && ny);
   if(InpSession==VC_ALL_DAY)return true;
   if(InpSession==VC_ASIA)return asia;
   if(InpSession==VC_LONDON)return london;
   if(InpSession==VC_NEW_YORK)return ny;
   if(InpSession==VC_OVERLAP)return overlap;
   return london || ny;
}

double NormalizePrice(const double raw)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return NormalizeDouble(MathRound(raw/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<minimum || minimum<=0 || step<=0)return 0.0;
   return NormalizeDouble(MathFloor((MathMin(raw,maximum)+1e-12)/step)*step,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double pnl=0;if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,pnl) || pnl==0)return 0.0;
   return NormalizeVolume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/MathAbs(pnl));
}

bool ReadBuffer(const int handle,const int shift,double &value)
{
   double data[1];if(CopyBuffer(handle,0,shift,1,data)!=1)return false;value=data[0];return MathIsValidNumber(value);
}

double TrueRangeAt(const int shift)
{
   double high=iHigh(_Symbol,InpSignalTimeframe,shift),low=iLow(_Symbol,InpSignalTimeframe,shift),previous=iClose(_Symbol,InpSignalTimeframe,shift+1);
   if(high<=0 || low<=0 || previous<=0)return 0.0;
   return MathMax(high-low,MathMax(MathAbs(high-previous),MathAbs(low-previous)));
}

bool MeanStd(const int shift,const int count,double &mean,double &deviation)
{
   double closes[];ArraySetAsSeries(closes,true);if(CopyClose(_Symbol,InpSignalTimeframe,shift,count,closes)!=count)return false;
   mean=0;for(int i=0;i<count;i++)mean+=closes[i];mean/=count;if(mean<=0)return false;
   double variance=0;for(int i=0;i<count;i++){double d=closes[i]-mean;variance+=d*d;}deviation=MathSqrt(variance/count);return true;
}

double BandWidth(const int shift)
{
   double mean=0,deviation=0;if(!MeanStd(shift,20,mean,deviation))return DBL_MAX;return 4.0*deviation/mean;
}

bool IsCompression(const int shift)
{
   if(InpCompression==VC_ATR_RATIO)
   {
      double fast=0,slow=0;if(!ReadBuffer(g_atr5,shift,fast) || !ReadBuffer(g_atr50,shift,slow) || slow<=0)return false;
      return fast/slow<=InpCompressionValue;
   }
   if(InpCompression==VC_BB_PERCENTILE)
   {
      double current=BandWidth(shift);if(current==DBL_MAX)return false;int valid=0,less=0;
      for(int i=0;i<100;i++){double value=BandWidth(shift+i);if(value==DBL_MAX)continue;valid++;if(value<=current)less++;}
      return valid>=80 && (double)less/valid<=InpCompressionValue;
   }
   if(InpCompression==VC_NARROW_RANGE)
   {
      int count=(int)MathRound(InpCompressionValue);double current=TrueRangeAt(shift);if(current<=0)return false;
      for(int i=1;i<count;i++){double value=TrueRangeAt(shift+i);if(value>0 && value<current)return false;}return true;
   }
   double mean=0,deviation=0,atr=0;if(!MeanStd(shift,20,mean,deviation) || !ReadBuffer(g_atr20,shift,atr) || atr<=0)return false;
   return 2.0*deviation<=InpCompressionValue*atr;
}

bool CompressionRange(const int shift,double &high,double &low)
{
   MqlRates bars[];ArraySetAsSeries(bars,true);if(CopyRates(_Symbol,InpSignalTimeframe,shift,InpRangeBars,bars)!=InpRangeBars)return false;
   high=-DBL_MAX;low=DBL_MAX;for(int i=0;i<ArraySize(bars);i++){high=MathMax(high,bars[i].high);low=MathMin(low,bars[i].low);}return high>low;
}

bool FindArmedRange(double &high,double &low)
{
   for(int shift=2;shift<=InpArmBars+1;shift++)if(IsCompression(shift) && CompressionRange(shift,high,low))return true;
   return false;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--){ulong value=PositionGetTicket(i);if(value>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=value;return true;}}
   return false;
}

int TradesToday(const datetime server)
{
   datetime utc=ServerToUTC(server);MqlDateTime x;TimeToStruct(utc,x);x.hour=0;x.min=0;x.sec=0;
   datetime from=StructToTime(x)+ServerUTCOffsetSeconds();if(!HistorySelect(from,server))return 0;int count=0;
   for(int i=HistoryDealsTotal()-1;i>=0;i--){ulong deal=HistoryDealGetTicket(i);if(deal>0 && HistoryDealGetString(deal,DEAL_SYMBOL)==_Symbol && HistoryDealGetInteger(deal,DEAL_MAGIC)==InpMagic && HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN)count++;}
   return count;
}

bool TrendAllows(const int side,const double close)
{
   if(InpTrendFilter==VC_TREND_NONE)return true;double ema50=0,ema200=0;
   if(!ReadBuffer(g_ema50,1,ema50))return false;
   if(InpTrendFilter==VC_EMA50)return side*(close-ema50)>0;
   if(!ReadBuffer(g_ema200,1,ema200))return false;
   if(InpTrendFilter==VC_EMA200)return side*(close-ema200)>0;
   return side*(close-ema50)>0 && side*(ema50-ema200)>0;
}

bool ConfirmationAllows(const int side,const MqlRates &signal,const double atr)
{
   bool body=side*(signal.close-signal.open)>=0.30*atr;double total=0;
   for(int shift=2;shift<22;shift++)total+=(double)iVolume(_Symbol,InpSignalTimeframe,shift);
   bool volume=(total>0 && (double)signal.tick_volume>=1.2*(total/20.0));
   if(InpConfirmation==VC_CLOSE)return true;
   if(InpConfirmation==VC_BODY)return body;
   if(InpConfirmation==VC_VOLUME)return volume;
   return body && volume;
}

bool SpreadOK(const double risk)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick) || risk<=0)return false;return 100.0*(tick.ask-tick.bid)/risk<=InpMaximumSpreadRiskPercent;
}

bool EnterTrade(const int side,const MqlRates &signal,const double range_high,const double range_low,const double atr)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return false;double entry=(side>0?tick.ask:tick.bid),raw_stop=0;
   if(InpStopMode==VC_RANGE)raw_stop=(side>0?range_low-InpStopValue*atr:range_high+InpStopValue*atr);
   else if(InpStopMode==VC_ATR)raw_stop=entry-side*InpStopValue*atr;
   else if(InpStopMode==VC_SIGNAL)raw_stop=(side>0?signal.low-InpStopValue*atr:signal.high+InpStopValue*atr);
   else
   {
      double extreme=(side>0?DBL_MAX:-DBL_MAX);
      for(int shift=1;shift<=5;shift++)extreme=(side>0?MathMin(extreme,iLow(_Symbol,InpSignalTimeframe,shift)):MathMax(extreme,iHigh(_Symbol,InpSignalTimeframe,shift)));
      raw_stop=(side>0?extreme-InpStopValue*atr:extreme+InpStopValue*atr);
   }
   double risk=(side>0?entry-raw_stop:raw_stop-entry);if(risk<=0 || risk>6.0*atr || !SpreadOK(risk))return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(risk<MathMax(minimum,0.10*atr))return false;double stop=NormalizePrice(raw_stop),target=NormalizePrice(entry+side*InpRewardRisk*risk);
   ENUM_ORDER_TYPE type=(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double lots=LotsForRisk(type,entry,stop);if(lots<=0)return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(side>0?trade.Buy(lots,_Symbol,0,stop,target,"Compression expansion"):trade.Sell(lots,_Symbol,0,stop,target,"Compression expansion"));
   if(!sent)Print("Compression entry failed: ",trade.ResultRetcodeDescription());return sent;
}

void ManagePosition(const bool new_signal_bar,const bool new_m15_bar)
{
   ulong ticket=0;if(!SelectOurPosition(ticket))return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);long side_type=PositionGetInteger(POSITION_TYPE);int side=(side_type==POSITION_TYPE_BUY?1:-1);
   if(TimeTradeServer()-opened>=InpMaximumHoldBars*PeriodSeconds(InpSignalTimeframe)){trade.PositionClose(ticket,InpMaximumDeviationPoints);return;}
   bool should_manage=(InpManagement==VC_DYNAMIC_M15_50_20?new_m15_bar:new_signal_bar);if(!should_manage || InpManagement==VC_NONE)return;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN),stop=PositionGetDouble(POSITION_SL),target=PositionGetDouble(POSITION_TP),initial=(InpRewardRisk>0?MathAbs(target-entry)/InpRewardRisk:MathAbs(entry-stop));
   if(initial<=0)return;ENUM_TIMEFRAMES frame=(InpManagement==VC_DYNAMIC_M15_50_20?PERIOD_M15:InpSignalTimeframe);double close=iClose(_Symbol,frame,1),atr=0;if(close<=0)return;
   double progress=side*(close-entry)/initial,candidate=stop;
   if(InpManagement==VC_BREAKEVEN && progress>=1.0)candidate=entry;
   else if(InpManagement==VC_ATR_TRAIL && progress>=1.0){if(!ReadBuffer(g_atr14,1,atr))return;candidate=close-side*1.5*atr;}
   else if(InpManagement==VC_DYNAMIC_M15_50_20 && progress>=0.5*InpRewardRisk)candidate=entry+side*0.2*InpRewardRisk*initial;
   else return;
   candidate=NormalizePrice(candidate);bool improves=(side>0?candidate>stop:candidate<stop);MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
   if(improves && (side>0?candidate<tick.bid:candidate>tick.ask))trade.PositionModify(ticket,candidate,target);
}

void CheckSignal()
{
   ulong ticket=0;if(SelectOurPosition(ticket) || TradesToday(TimeTradeServer())>=InpMaximumTradesPerDay)return;
   MqlRates bars[];ArraySetAsSeries(bars,true);if(CopyRates(_Symbol,InpSignalTimeframe,1,2,bars)!=2)return;
   MqlRates signal=bars[0],previous=bars[1];if(!SessionAllows(signal.time))return;double range_high=0,range_low=0,atr=0;
   if(!FindArmedRange(range_high,range_low) || !ReadBuffer(g_atr14,1,atr) || atr<=0)return;
   double upper=range_high+InpBreakoutBufferATR*atr,lower=range_low-InpBreakoutBufferATR*atr;int side=0;
   if(signal.close>upper && previous.close<=upper)side=1;else if(signal.close<lower && previous.close>=lower)side=-1;
   if(side==0 || (InpDirection==VC_LONG_ONLY && side<0) || (InpDirection==VC_SHORT_ONLY && side>0))return;
   if(!ConfirmationAllows(side,signal,atr) || !TrendAllows(side,signal.close))return;
   EnterTrade(side,signal,range_high,range_low,atr);
}

int OnInit()
{
   if(InpTesterOnly && !(bool)MQLInfoInteger(MQL_TESTER)){Print("Tester-only research preset is enabled.");return INIT_FAILED;}
   if(InpRiskPercent!=1.0 || InpRangeBars<2 || InpArmBars<1 || InpMaximumHoldBars<1 || InpRewardRisk<0.5)return INIT_PARAMETERS_INCORRECT;
   g_atr5=iATR(_Symbol,InpSignalTimeframe,5);g_atr14=iATR(_Symbol,InpSignalTimeframe,14);g_atr20=iATR(_Symbol,InpSignalTimeframe,20);g_atr50=iATR(_Symbol,InpSignalTimeframe,50);
   g_ema50=iMA(_Symbol,InpSignalTimeframe,50,0,MODE_EMA,PRICE_CLOSE);g_ema200=iMA(_Symbol,InpSignalTimeframe,200,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr5==INVALID_HANDLE || g_atr14==INVALID_HANDLE || g_atr20==INVALID_HANDLE || g_atr50==INVALID_HANDLE || g_ema50==INVALID_HANDLE || g_ema200==INVALID_HANDLE)return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);g_last_signal_bar=iTime(_Symbol,InpSignalTimeframe,0);g_last_m15_bar=iTime(_Symbol,PERIOD_M15,0);return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr5!=INVALID_HANDLE)IndicatorRelease(g_atr5);if(g_atr14!=INVALID_HANDLE)IndicatorRelease(g_atr14);if(g_atr20!=INVALID_HANDLE)IndicatorRelease(g_atr20);if(g_atr50!=INVALID_HANDLE)IndicatorRelease(g_atr50);
   if(g_ema50!=INVALID_HANDLE)IndicatorRelease(g_ema50);if(g_ema200!=INVALID_HANDLE)IndicatorRelease(g_ema200);
}

void OnTick()
{
   datetime signal_bar=iTime(_Symbol,InpSignalTimeframe,0),m15_bar=iTime(_Symbol,PERIOD_M15,0);
   bool new_signal=(signal_bar>0 && signal_bar!=g_last_signal_bar),new_m15=(m15_bar>0 && m15_bar!=g_last_m15_bar);
   if(new_signal)g_last_signal_bar=signal_bar;if(new_m15)g_last_m15_bar=m15_bar;
   ManagePosition(new_signal,new_m15);if(new_signal)CheckSignal();
}
