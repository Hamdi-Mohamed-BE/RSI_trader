#property copyright "Calyx raw paper-replication research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_TESTER_SERVER_CLOCK
{
   TESTER_CLOCK_UTC=0,
   TESTER_CLOCK_EET_EEST=1,
   TESTER_CLOCK_MANUAL=2
};

input group "Raw paper rule"
input bool   InpEnableTrading=false;
input int    InpFastTrailEMA=20;
input int    InpEntryTrailEMA=50;
input int    InpRegimeEMA=200;
input int    InpATRPeriod=14;
input double InpRegimeBoundaryPercent=0.10;
input double InpVolumeMultiple=1.10;
input int    InpVolumeMAPeriod=20;
input double InpMinimumRangeATR=0.80;
input double InpStopBufferATR=0.50;
input double InpTargetR=3.00;
input double InpTightenAtR=2.50;
input bool   InpUseCompressedVWAPPartial=true;
input int    InpCompressedBars=5;
input double InpCompressedMaxRangeATR=0.60;
input double InpCompressedVWAPDistancePercent=0.15;

input group "Session and paper risk"
input int    InpSessionStartUTCHour=13;
input int    InpSessionStartUTCMinute=30;
input int    InpSessionEndUTCHour=20;
input int    InpSessionEndUTCMinute=0;
input double InpRiskPercent=1.0;
input int    InpMaxConsecutiveSessionLosses=3;
input double InpDailyLossLimitPercent=3.0;
input bool   InpUsePaper2024NewsExclusion=true;
input int    InpNewsBufferMinutes=15;
input int    InpMaxDeviationBrokerPoints=30;

input group "Identity"
input long   InpMagic=981009801;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input ENUM_TESTER_SERVER_CLOCK InpTesterServerClock=TESTER_CLOCK_UTC; // Exness tester strategy timestamps are UTC
input int    InpTesterManualUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_ema20=INVALID_HANDLE;
int g_ema50=INVALID_HANDLE;
int g_ema200=INVALID_HANDLE;
int g_atr=INVALID_HANDLE;
datetime g_last_bar=0;
bool g_partial_done=false;

int LastSunday(const int year,const int month)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=31; p.hour=12;
   while(p.day>28)
   {
      datetime value=StructToTime(p);
      TimeToStruct(value,p);
      if(p.day_of_week==0) return p.day;
      p.day--;
   }
   return p.day;
}

int EuropeUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=LastSunday(p.year,3); start.hour=1;
   finish.year=p.year; finish.mon=10; finish.day=LastSunday(p.year,10); finish.hour=1;
   return (utc_time>=StructToTime(start) && utc_time<StructToTime(finish) ? 3 : 2);
}

int AutomaticLiveOffsetSeconds()
{
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT();
   if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime server_time)
{
   if(!(bool)MQLInfoInteger(MQL_TESTER))
   {
      int offset=(InpUseAutomaticLiveServerOffset ? AutomaticLiveOffsetSeconds() : InpManualLiveServerUTCOffsetHours*3600);
      return server_time-offset;
   }
   if(InpTesterServerClock==TESTER_CLOCK_UTC) return server_time;
   if(InpTesterServerClock==TESTER_CLOCK_MANUAL) return server_time-InpTesterManualUTCOffsetHours*3600;
   datetime utc_standard=server_time-2*3600;
   return server_time-EuropeUTCOffsetHours(utc_standard)*3600;
}

datetime UTCToServer(const datetime utc_time)
{
   if(!(bool)MQLInfoInteger(MQL_TESTER))
   {
      int offset=(InpUseAutomaticLiveServerOffset ? AutomaticLiveOffsetSeconds() : InpManualLiveServerUTCOffsetHours*3600);
      return utc_time+offset;
   }
   if(InpTesterServerClock==TESTER_CLOCK_UTC) return utc_time;
   if(InpTesterServerClock==TESTER_CLOCK_MANUAL) return utc_time+InpTesterManualUTCOffsetHours*3600;
   return utc_time+EuropeUTCOffsetHours(utc_time)*3600;
}

int MinuteOfDayUTC(const datetime server_time)
{
   MqlDateTime p; TimeToStruct(ServerToUTC(server_time),p);
   return p.hour*60+p.min;
}

int DateKeyUTC(const datetime server_time)
{
   MqlDateTime p; TimeToStruct(ServerToUTC(server_time),p);
   return p.year*10000+p.mon*100+p.day;
}

datetime SessionStartServer(const datetime server_time)
{
   MqlDateTime p; TimeToStruct(ServerToUTC(server_time),p);
   p.hour=InpSessionStartUTCHour; p.min=InpSessionStartUTCMinute; p.sec=0;
   return UTCToServer(StructToTime(p));
}

double PriceToTick(const double value)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return value;
   return NormalizeDouble(MathRound(value/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double one_lot=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   double loss=MathAbs(one_lot);
   if(loss<=0.0) return 0.0;
   return NormalizeVolume((AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0)/loss);
}

bool OurPosition(ulong &ticket,long &type,double &entry,double &volume,double &tp)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong current=PositionGetTicket(i);
      if(current>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=current;
         type=PositionGetInteger(POSITION_TYPE);
         entry=PositionGetDouble(POSITION_PRICE_OPEN);
         volume=PositionGetDouble(POSITION_VOLUME);
         tp=PositionGetDouble(POSITION_TP);
         return true;
      }
   }
   return false;
}

bool HasPosition()
{
   ulong ticket=0; long type=0; double entry=0.0,volume=0.0,tp=0.0;
   return OurPosition(ticket,type,entry,volume,tp);
}

bool BufferValue(const int handle,const int shift,double &value)
{
   double values[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,values)!=1 || values[0]<=0.0) return false;
   value=values[0];
   return true;
}

bool SessionVWAP(const datetime bar_open_server,double &vwap)
{
   datetime start=SessionStartServer(bar_open_server);
   MqlRates bars[];
   int count=CopyRates(_Symbol,PERIOD_M15,start,bar_open_server,bars);
   if(count<=0) return false;
   double weighted=0.0,total=0.0;
   for(int i=0;i<count;i++)
   {
      int minute=MinuteOfDayUTC(bars[i].time);
      int session_start=InpSessionStartUTCHour*60+InpSessionStartUTCMinute;
      int session_end=InpSessionEndUTCHour*60+InpSessionEndUTCMinute;
      if(DateKeyUTC(bars[i].time)!=DateKeyUTC(bar_open_server) || minute<session_start || minute>=session_end || bars[i].time>bar_open_server)
         continue;
      double volume=(bars[i].real_volume>0 ? (double)bars[i].real_volume : (double)bars[i].tick_volume);
      if(volume<=0.0) continue;
      double typical=(bars[i].high+bars[i].low+bars[i].close)/3.0;
      weighted+=typical*volume;
      total+=volume;
   }
   if(total<=0.0) return false;
   vwap=weighted/total;
   return vwap>0.0;
}

bool VolumeConfirmed(const long signal_volume)
{
   if(InpVolumeMAPeriod<=0) return false;
   double total=0.0;
   for(int shift=1;shift<=InpVolumeMAPeriod;shift++)
      total+=(double)iVolume(_Symbol,PERIOD_M15,shift);
   double average=total/InpVolumeMAPeriod;
   return average>0.0 && (double)signal_volume>InpVolumeMultiple*average;
}

bool BullishRejection(const MqlRates &signal,const MqlRates &prior)
{
   double body=MathAbs(signal.close-signal.open);
   double lower=MathMin(signal.open,signal.close)-signal.low;
   double upper=signal.high-MathMax(signal.open,signal.close);
   bool pin=(lower>=2.0*body && upper<=0.5*lower);
   bool engulf=(signal.close>signal.open && prior.close<prior.open && signal.close>prior.open && signal.open<prior.close);
   return pin || engulf;
}

bool BearishRejection(const MqlRates &signal,const MqlRates &prior)
{
   double body=MathAbs(signal.close-signal.open);
   double lower=MathMin(signal.open,signal.close)-signal.low;
   double upper=signal.high-MathMax(signal.open,signal.close);
   bool pin=(upper>=2.0*body && lower<=0.5*upper);
   bool engulf=(signal.close<signal.open && prior.close>prior.open && signal.close<prior.open && signal.open>prior.close);
   return pin || engulf;
}

bool DateInList(const int key,const int &dates[])
{
   for(int i=0;i<ArraySize(dates);i++) if(dates[i]==key) return true;
   return false;
}

bool NearPaperNews2024(const datetime server_time)
{
   if(!InpUsePaper2024NewsExclusion) return false;
   datetime utc=ServerToUTC(server_time);
   MqlDateTime p; TimeToStruct(utc,p);
   if(p.year!=2024) return false;
   int key=p.year*10000+p.mon*100+p.day;
   int nfp[]={20240105,20240202,20240308,20240405,20240503,20240607,20240705,20240802,20240906,20241004,20241101,20241206};
   int cpi[]={20240111,20240213,20240312,20240410,20240515,20240612,20240711,20240814,20240911,20241010,20241113,20241211};
   int fomc[]={20240131,20240320,20240501,20240612,20240731,20240918,20241107,20241218};
   int gdp[]={20240125,20240228,20240328,20240425,20240530,20240627,20240725,20240829,20240926,20241030,20241127,20241219};
   int event_hour=-1,event_minute=30;
   if(DateInList(key,nfp) || DateInList(key,cpi) || DateInList(key,gdp))
   {
      // 08:30 New York: 13:30 UTC in standard time and 12:30 UTC in daylight time.
      bool dst=(p.mon>3 && p.mon<11) || (p.mon==3 && p.day>=10) || (p.mon==11 && p.day<3);
      event_hour=(dst ? 12 : 13);
   }
   if(DateInList(key,fomc))
   {
      bool dst=(p.mon>3 && p.mon<11) || (p.mon==3 && p.day>=10) || (p.mon==11 && p.day<3);
      event_hour=(dst ? 18 : 19); event_minute=0;
   }
   if(event_hour<0) return false;
   int delta=MathAbs((p.hour*60+p.min)-(event_hour*60+event_minute));
   return delta<=InpNewsBufferMinutes;
}

void SessionPerformance(double &realized,int &consecutive_losses,double &session_start_balance)
{
   realized=0.0; consecutive_losses=0;
   datetime start=SessionStartServer(TimeCurrent());
   if(!HistorySelect(start,TimeCurrent()))
   {
      session_start_balance=AccountInfoDouble(ACCOUNT_BALANCE);
      return;
   }
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 || HistoryDealGetString(ticket,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(ticket,DEAL_MAGIC)!=InpMagic)
         continue;
      long entry=HistoryDealGetInteger(ticket,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY) continue;
      double pnl=HistoryDealGetDouble(ticket,DEAL_PROFIT)+HistoryDealGetDouble(ticket,DEAL_SWAP)+HistoryDealGetDouble(ticket,DEAL_COMMISSION);
      realized+=pnl;
      if(pnl<0.0) consecutive_losses++;
      else if(pnl>0.0) consecutive_losses=0;
   }
   session_start_balance=AccountInfoDouble(ACCOUNT_BALANCE)-realized;
}

bool RiskGateOpen()
{
   double realized=0.0,start_balance=0.0; int consecutive=0;
   SessionPerformance(realized,consecutive,start_balance);
   if(consecutive>=InpMaxConsecutiveSessionLosses) return false;
   if(start_balance>0.0 && realized<=-start_balance*InpDailyLossLimitPercent/100.0) return false;
   return true;
}

bool CompressedAtVWAP()
{
   for(int shift=1;shift<=InpCompressedBars;shift++)
   {
      MqlRates bar[1];
      if(CopyRates(_Symbol,PERIOD_M15,shift,1,bar)!=1) return false;
      double atr=0.0,vwap=0.0;
      if(!BufferValue(g_atr,shift,atr) || !SessionVWAP(bar[0].time,vwap)) return false;
      if(bar[0].high-bar[0].low>InpCompressedMaxRangeATR*atr) return false;
      if(MathAbs(bar[0].close-vwap)/vwap*100.0>InpCompressedVWAPDistancePercent) return false;
   }
   return true;
}

void ClosePosition(const ulong ticket,const string reason)
{
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   if(!trade.PositionClose(ticket,InpMaxDeviationBrokerPoints))
      Print(reason," close failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void ManagePositionOnClosedBar()
{
   ulong ticket=0; long type=0; double entry=0.0,volume=0.0,tp=0.0;
   if(!OurPosition(ticket,type,entry,volume,tp))
   {
      g_partial_done=false;
      return;
   }
   MqlRates signal[1];
   if(CopyRates(_Symbol,PERIOD_M15,1,1,signal)!=1) return;
   double initial_r=(tp>0.0 ? MathAbs(tp-entry)/InpTargetR : 0.0);
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   double favorable=(type==POSITION_TYPE_BUY ? tick.bid-entry : entry-tick.ask);
   double floating_r=(initial_r>0.0 ? favorable/initial_r : 0.0);
   double trail=0.0;
   int handle=(floating_r>=InpTightenAtR ? g_ema20 : g_ema50);
   if(!BufferValue(handle,1,trail)) return;
   bool adverse=(type==POSITION_TYPE_BUY ? signal[0].close<trail : signal[0].close>trail);
   if(adverse)
   {
      ClosePosition(ticket,"EMA trail");
      return;
   }
   if(InpUseCompressedVWAPPartial && !g_partial_done && CompressedAtVWAP())
   {
      double half=NormalizeVolume(volume*0.5);
      if(half>0.0 && half<volume)
      {
         trade.SetExpertMagicNumber((ulong)InpMagic);
         trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
         if(trade.PositionClosePartial(ticket,half,InpMaxDeviationBrokerPoints)) g_partial_done=true;
      }
   }
}

void EvaluateEntry()
{
   if(!InpEnableTrading || HasPosition() || !RiskGateOpen()) return;
   MqlRates bars[2];
   if(CopyRates(_Symbol,PERIOD_M15,1,2,bars)!=2) return;
   MqlRates signal=bars[1],prior=bars[0];
   datetime signal_end=signal.time+15*60;
   int minute=MinuteOfDayUTC(signal_end);
   int session_start=InpSessionStartUTCHour*60+InpSessionStartUTCMinute;
   int session_end=InpSessionEndUTCHour*60+InpSessionEndUTCMinute;
   if(minute<=session_start || minute>=session_end || NearPaperNews2024(signal_end)) return;

   double ema50=0.0,ema200=0.0,atr=0.0,vwap=0.0;
   if(!BufferValue(g_ema50,1,ema50) || !BufferValue(g_ema200,1,ema200) || !BufferValue(g_atr,1,atr) || !SessionVWAP(signal.time,vwap)) return;
   if(MathAbs(signal.close-ema200)/ema200*100.0<=InpRegimeBoundaryPercent) return;
   if(!VolumeConfirmed(signal.tick_volume) || signal.high-signal.low<InpMinimumRangeATR*atr) return;

   int direction=0;
   if(signal.close>ema200 && signal.close>vwap && MathMin(signal.low,prior.low)<=ema50 && ema50<=signal.close && BullishRejection(signal,prior))
      direction=1;
   else if(signal.close<ema200 && signal.close<vwap && MathMax(signal.high,prior.high)>=ema50 && ema50>=signal.close && BearishRejection(signal,prior))
      direction=-1;
   if(direction==0) return;

   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? signal.low-InpStopBufferATR*atr : signal.high+InpStopBufferATR*atr);
   stop=PriceToTick(stop);
   if((direction>0 && stop>=entry) || (direction<0 && stop<=entry)) return;
   double risk_distance=MathAbs(entry-stop);
   double target=PriceToTick(entry+direction*InpTargetR*risk_distance);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0) return;

   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   bool ok=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,"Raw Gold VWAP EMA") : trade.Sell(lots,_Symbol,0.0,stop,target,"Raw Gold VWAP EMA"));
   if(!ok) Print("Paper entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   else g_partial_done=false;
}

void CloseAtSessionEnd()
{
   int minute=MinuteOfDayUTC(TimeCurrent());
   int session_end=InpSessionEndUTCHour*60+InpSessionEndUTCMinute;
   if(minute<session_end) return;
   ulong ticket=0; long type=0; double entry=0.0,volume=0.0,tp=0.0;
   if(OurPosition(ticket,type,entry,volume,tp)) ClosePosition(ticket,"Session end");
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>100.0 || InpFastTrailEMA<2 || InpEntryTrailEMA<2 || InpRegimeEMA<2 ||
      InpATRPeriod<2 || InpVolumeMAPeriod<2 || InpStopBufferATR<=0.0 || InpTargetR<=0.0 || InpTightenAtR<=0.0 ||
      InpSessionStartUTCHour*60+InpSessionStartUTCMinute>=InpSessionEndUTCHour*60+InpSessionEndUTCMinute || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   g_ema20=iMA(_Symbol,PERIOD_M15,InpFastTrailEMA,0,MODE_EMA,PRICE_CLOSE);
   g_ema50=iMA(_Symbol,PERIOD_M15,InpEntryTrailEMA,0,MODE_EMA,PRICE_CLOSE);
   g_ema200=iMA(_Symbol,PERIOD_M15,InpRegimeEMA,0,MODE_EMA,PRICE_CLOSE);
   g_atr=iATR(_Symbol,PERIOD_M15,InpATRPeriod);
   if(g_ema20==INVALID_HANDLE || g_ema50==INVALID_HANDLE || g_ema200==INVALID_HANDLE || g_atr==INVALID_HANDLE) return INIT_FAILED;
   g_last_bar=iTime(_Symbol,PERIOD_M15,0);
   if(!InpEnableTrading) Print("Raw research gate is OFF. Load the research SET deliberately.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_ema20!=INVALID_HANDLE) IndicatorRelease(g_ema20);
   if(g_ema50!=INVALID_HANDLE) IndicatorRelease(g_ema50);
   if(g_ema200!=INVALID_HANDLE) IndicatorRelease(g_ema200);
   if(g_atr!=INVALID_HANDLE) IndicatorRelease(g_atr);
}

void OnTick()
{
   CloseAtSessionEnd();
   datetime current=iTime(_Symbol,PERIOD_M15,0);
   if(current>0 && current!=g_last_bar)
   {
      g_last_bar=current;
      ManagePositionOnClosedBar();
      EvaluateEntry();
   }
}
