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

enum ENUM_NOISE_DIRECTION
{
   NOISE_BOTH=0,
   NOISE_LONG_ONLY=1,
   NOISE_SHORT_ONLY=2
};

enum ENUM_NOISE_STOP
{
   NOISE_STOP_STRUCTURAL=0,
   NOISE_STOP_PERCENT=1,
   NOISE_STOP_ATR=2
};

enum ENUM_NOISE_EXIT
{
   NOISE_EXIT_BAND_AND_VWAP=0,
   NOISE_EXIT_BAND_ONLY=1,
   NOISE_EXIT_VWAP_ONLY=2,
   NOISE_EXIT_OPPOSITE_BAND=3,
   NOISE_EXIT_TIME_ONLY=4
};

enum ENUM_NOISE_REGIME
{
   NOISE_REGIME_NONE=0,
   NOISE_REGIME_EMA50=1,
   NOISE_REGIME_EMA200=2,
   NOISE_REGIME_EMA50_SLOPE=3
};

input group "Raw Zarattini-Aziz-Barbon paper rules"
input bool   InpEnableTrading=false;
input int    InpNoiseLookbackSessions=14;
input double InpVolatilityMultiplier=1.0;
input int    InpDecisionFrequencyMinutes=30;
input double InpTargetDailyVolatilityPercent=2.0;
input double InpMaximumNotionalLeverage=4.0;
input bool   InpRequireRegularNYSEDay=true;

input group "Calyx pipeline risk, stops and exits"
input bool   InpUseCalyxRisk=false;
input double InpRiskPercent=1.0;
input ENUM_NOISE_DIRECTION InpDirectionMode=NOISE_BOTH;
input ENUM_NOISE_STOP InpStopMode=NOISE_STOP_STRUCTURAL;
input double InpStopPercent=0.75;
input ENUM_TIMEFRAMES InpStopATRTimeframe=PERIOD_M30;
input int    InpStopATRPeriod=14;
input double InpStopATRMultiplier=1.0;
input double InpTargetR=0.0;
input ENUM_NOISE_EXIT InpExitMode=NOISE_EXIT_BAND_AND_VWAP;
input double InpBreakEvenAtR=0.0;
input double InpTrailStartR=0.0;
input ENUM_TIMEFRAMES InpTrailATRTimeframe=PERIOD_M30;
input int    InpTrailATRPeriod=14;
input double InpTrailATRMultiplier=1.0;

input group "Calyx pipeline session and filters"
input bool   InpSkipLunch=false;
input int    InpLunchStartNewYorkHour=12;
input int    InpLunchStartNewYorkMinute=0;
input int    InpLunchEndNewYorkHour=14;
input int    InpLunchEndNewYorkMinute=0;
input ENUM_NOISE_REGIME InpRegimeMode=NOISE_REGIME_NONE;
input double InpMinimumDailyATRPercent=0.0;
input double InpMaximumDailyATRPercent=0.0;
input double InpMinimumADX=0.0;
input ENUM_TIMEFRAMES InpADXTimeframe=PERIOD_M30;
input int    InpADXPeriod=14;
input double InpMinimumRelativeVolume=0.0;

input group "New York regular session"
input int    InpOpenNewYorkHour=9;
input int    InpOpenNewYorkMinute=30;
input int    InpFirstDecisionNewYorkHour=10;
input int    InpFirstDecisionNewYorkMinute=0;
input int    InpLastDecisionNewYorkHour=15;
input int    InpLastDecisionNewYorkMinute=30;
input int    InpCloseNewYorkHour=16;
input int    InpCloseNewYorkMinute=0;

input group "Execution"
input int    InpMaxDeviationBrokerPoints=50;
input long   InpMagic=982009901;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input ENUM_TESTER_SERVER_CLOCK InpTesterServerClock=TESTER_CLOCK_UTC;
input int    InpTesterManualUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
long   g_session_key=0;
long   g_last_decision_key=0;
long   g_last_timed_close_key=0;
double g_session_open=0.0;
double g_session_volume=0.0;
double g_session_start_equity=0.0;
double g_initial_risk=0.0;

int NthWeekdayOfMonth(const int year,const int month,const int weekday,const int occurrence)
{
   MqlDateTime first={0};
   first.year=year; first.mon=month; first.day=1; first.hour=12;
   datetime value=StructToTime(first); TimeToStruct(value,first);
   return 1+((weekday-first.day_of_week+7)%7)+(occurrence-1)*7;
}

int LastWeekdayOfMonth(const int year,const int month,const int weekday)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month+1; p.day=1; p.hour=12;
   if(month==12) { p.year=year+1; p.mon=1; }
   datetime value=StructToTime(p)-86400; TimeToStruct(value,p);
   return p.day-((p.day_of_week-weekday+7)%7);
}

int LastSunday(const int year,const int month)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=31; p.hour=12;
   while(p.day>28)
   {
      datetime value=StructToTime(p); TimeToStruct(value,p);
      if(p.day_of_week==0) return p.day;
      p.day--;
   }
   return p.day;
}

datetime EasterSunday(const int year)
{
   int a=year%19,b=year/100,c=year%100,d=b/4,e=b%4,f=(b+8)/25,g=(b-f+1)/3;
   int h=(19*a+b-d-g+15)%30,i=c/4,k=c%4,l=(32+2*e+2*i-h-k)%7,m=(a+11*h+22*l)/451;
   int month=(h+l-7*m+114)/31,day=((h+l-7*m+114)%31)+1;
   MqlDateTime p={0}; p.year=year; p.mon=month; p.day=day; p.hour=12;
   return StructToTime(p);
}

bool IsObservedFixedHoliday(const MqlDateTime &p,const int month,const int day)
{
   MqlDateTime fixed={0}; fixed.year=p.year; fixed.mon=month; fixed.day=day; fixed.hour=12;
   datetime value=StructToTime(fixed); TimeToStruct(value,fixed);
   int observed=day;
   if(fixed.day_of_week==6) observed=day-1;
   else if(fixed.day_of_week==0) observed=day+1;
   return p.mon==month && p.day==observed;
}

bool IsNewYearObserved(const MqlDateTime &p)
{
   if(IsObservedFixedHoliday(p,1,1)) return true;
   if(p.mon==12 && p.day==31)
   {
      MqlDateTime next={0}; next.year=p.year+1; next.mon=1; next.day=1; next.hour=12;
      datetime value=StructToTime(next); TimeToStruct(value,next);
      return next.day_of_week==6;
   }
   return false;
}

bool IsNYSEHoliday(const MqlDateTime &p)
{
   if(p.day_of_week==0 || p.day_of_week==6) return true;
   if(IsNewYearObserved(p)) return true;
   if(p.mon==1 && p.day==NthWeekdayOfMonth(p.year,1,1,3)) return true;
   if(p.mon==2 && p.day==NthWeekdayOfMonth(p.year,2,1,3)) return true;
   MqlDateTime good_friday; TimeToStruct(EasterSunday(p.year)-2*86400,good_friday);
   if(p.mon==good_friday.mon && p.day==good_friday.day) return true;
   if(p.mon==5 && p.day==LastWeekdayOfMonth(p.year,5,1)) return true;
   if(p.year>=2022 && IsObservedFixedHoliday(p,6,19)) return true;
   if(IsObservedFixedHoliday(p,7,4)) return true;
   if(p.mon==9 && p.day==NthWeekdayOfMonth(p.year,9,1,1)) return true;
   if(p.mon==11 && p.day==NthWeekdayOfMonth(p.year,11,4,4)) return true;
   if(IsObservedFixedHoliday(p,12,25)) return true;
   if(p.year==2025 && p.mon==1 && p.day==9) return true;
   return false;
}

bool IsNYSEEarlyClose(const MqlDateTime &p)
{
   int thanksgiving=NthWeekdayOfMonth(p.year,11,4,4);
   if(p.mon==11 && p.day==thanksgiving+1 && p.day_of_week==5) return true;
   if(p.mon==12 && p.day==24 && p.day_of_week>=1 && p.day_of_week<=4) return true;
   if(p.mon==7 && p.day==3 && p.day_of_week>=1 && p.day_of_week<=4) return true;
   return false;
}

bool IsRegularSession(const MqlDateTime &p)
{
   if(p.day_of_week<1 || p.day_of_week>5) return false;
   if(!InpRequireRegularNYSEDay) return true;
   return !IsNYSEHoliday(p) && !IsNYSEEarlyClose(p);
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
   datetime server=TimeTradeServer(); if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT(); if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
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

int NewYorkOffsetForLocal(const datetime local_time)
{
   MqlDateTime p; TimeToStruct(local_time,p);
   int march=NthWeekdayOfMonth(p.year,3,0,2),november=NthWeekdayOfMonth(p.year,11,0,1);
   if(p.mon>3 && p.mon<11) return -4;
   if(p.mon<3 || p.mon>11) return -5;
   if(p.mon==3) return (p.day>march || (p.day==march && p.hour>=2)) ? -4 : -5;
   return (p.day<november || (p.day==november && p.hour<2)) ? -4 : -5;
}

datetime NewYorkLocalToUTC(const datetime local_time)
{
   return local_time-NewYorkOffsetForLocal(local_time)*3600;
}

datetime UTCToNewYork(const datetime utc_time)
{
   MqlDateTime u; TimeToStruct(utc_time,u);
   int march=NthWeekdayOfMonth(u.year,3,0,2),november=NthWeekdayOfMonth(u.year,11,0,1);
   MqlDateTime start={0},finish={0};
   start.year=u.year; start.mon=3; start.day=march; start.hour=7;
   finish.year=u.year; finish.mon=11; finish.day=november; finish.hour=6;
   int offset=(utc_time>=StructToTime(start) && utc_time<StructToTime(finish)) ? -4 : -5;
   return utc_time+offset*3600;
}

datetime ServerToNewYork(const datetime server_time)
{
   return UTCToNewYork(ServerToUTC(server_time));
}

long DateKey(const datetime value)
{
   MqlDateTime p; TimeToStruct(value,p);
   return (long)p.year*10000+(long)p.mon*100+p.day;
}

datetime LocalDateTime(const MqlDateTime &date_parts,const int minutes)
{
   MqlDateTime p=date_parts;
   p.hour=minutes/60; p.min=minutes%60; p.sec=0;
   return StructToTime(p);
}

bool ExactMinuteBar(const datetime local_time,MqlRates &bar)
{
   datetime server_time=UTCToServer(NewYorkLocalToUTC(local_time));
   int shift=iBarShift(_Symbol,PERIOD_M1,server_time,false);
   if(shift<0) return false;
   MqlRates one[1];
   if(CopyRates(_Symbol,PERIOD_M1,shift,1,one)!=1) return false;
   if(MathAbs((double)(one[0].time-server_time))>90.0) return false;
   bar=one[0];
   return bar.open>0.0 && bar.close>0.0;
}

bool PreviousRegularClose(const MqlDateTime &today,double &close_price)
{
   datetime today_local=LocalDateTime(today,12*60);
   for(int delta=1;delta<=20;delta++)
   {
      datetime candidate=today_local-delta*86400;
      MqlDateTime p; TimeToStruct(candidate,p);
      if(!IsRegularSession(p)) continue;
      MqlRates bar;
      if(ExactMinuteBar(LocalDateTime(p,15*60+59),bar))
      {
         close_price=bar.close;
         return true;
      }
   }
   return false;
}

bool NoiseSigma(const MqlDateTime &today,const int sample_minute,double &sigma)
{
   datetime today_local=LocalDateTime(today,12*60);
   double total=0.0;
   int found=0;
   for(int delta=1;delta<=InpNoiseLookbackSessions*3+15 && found<InpNoiseLookbackSessions;delta++)
   {
      datetime candidate=today_local-delta*86400;
      MqlDateTime p; TimeToStruct(candidate,p);
      if(!IsRegularSession(p)) continue;
      MqlRates opening,sample;
      if(!ExactMinuteBar(LocalDateTime(p,InpOpenNewYorkHour*60+InpOpenNewYorkMinute),opening)) continue;
      if(!ExactMinuteBar(LocalDateTime(p,sample_minute),sample)) continue;
      total+=MathAbs(sample.close/opening.open-1.0);
      found++;
   }
   if(found<InpNoiseLookbackSessions) return false;
   sigma=total/found;
   return sigma>0.0 && MathIsValidNumber(sigma);
}

bool SessionVWAP(const MqlDateTime &today,const int sample_minute,double &vwap)
{
   datetime local_from=LocalDateTime(today,InpOpenNewYorkHour*60+InpOpenNewYorkMinute);
   datetime local_to=LocalDateTime(today,sample_minute);
   datetime from=UTCToServer(NewYorkLocalToUTC(local_from));
   datetime to=UTCToServer(NewYorkLocalToUTC(local_to))+59;
   MqlRates rates[];
   int count=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
   if(count<2) return false;
   double weighted=0.0,total_volume=0.0;
   for(int i=0;i<count;i++)
   {
      double volume=(rates[i].real_volume>0 ? (double)rates[i].real_volume : (double)rates[i].tick_volume);
      if(volume<=0.0) continue;
      double typical=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      weighted+=typical*volume;
      total_volume+=volume;
   }
   if(total_volume<=0.0) return false;
   vwap=weighted/total_volume;
   return vwap>0.0 && MathIsValidNumber(vwap);
}

bool RecentDailyVolatility(const MqlDateTime &today,double &volatility)
{
   datetime today_local=LocalDateTime(today,12*60);
   double closes[]; ArrayResize(closes,InpNoiseLookbackSessions+1);
   int found=0;
   for(int delta=1;delta<=50 && found<InpNoiseLookbackSessions+1;delta++)
   {
      datetime candidate=today_local-delta*86400;
      MqlDateTime p; TimeToStruct(candidate,p);
      if(!IsRegularSession(p)) continue;
      MqlRates close_bar;
      if(!ExactMinuteBar(LocalDateTime(p,15*60+59),close_bar)) continue;
      closes[found++]=close_bar.close;
   }
   if(found<InpNoiseLookbackSessions+1) return false;
   double returns[]; ArrayResize(returns,InpNoiseLookbackSessions);
   double mean=0.0;
   for(int i=0;i<InpNoiseLookbackSessions;i++)
   {
      returns[i]=closes[i]/closes[i+1]-1.0;
      mean+=returns[i];
   }
   mean/=InpNoiseLookbackSessions;
   double sum=0.0;
   for(int i=0;i<InpNoiseLookbackSessions;i++) sum+=(returns[i]-mean)*(returns[i]-mean);
   volatility=MathSqrt(sum/(InpNoiseLookbackSessions-1));
   return volatility>0.0 && MathIsValidNumber(volatility);
}

bool IndicatorValue(const int handle,const int buffer_number,const int shift,double &value)
{
   if(handle==INVALID_HANDLE) return false;
   double buffer[];
   if(CopyBuffer(handle,buffer_number,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return MathIsValidNumber(value) && value>0.0;
}

bool ATRValue(const ENUM_TIMEFRAMES timeframe,const int period,double &value)
{
   int handle=iATR(_Symbol,timeframe,period);
   if(handle==INVALID_HANDLE) return false;
   bool ok=IndicatorValue(handle,0,1,value);
   IndicatorRelease(handle);
   return ok;
}

bool EMAValue(const int period,const int shift,double &value)
{
   int handle=iMA(_Symbol,PERIOD_D1,period,0,MODE_EMA,PRICE_CLOSE);
   if(handle==INVALID_HANDLE) return false;
   bool ok=IndicatorValue(handle,0,shift,value);
   IndicatorRelease(handle);
   return ok;
}

bool ADXValue(double &value)
{
   int handle=iADX(_Symbol,InpADXTimeframe,InpADXPeriod);
   if(handle==INVALID_HANDLE) return false;
   bool ok=IndicatorValue(handle,0,1,value);
   IndicatorRelease(handle);
   return ok;
}

double RelativeVolumeAtMinute(const MqlDateTime &today,const int sample_minute,const long current_volume)
{
   if(InpMinimumRelativeVolume<=0.0) return 999.0;
   datetime today_local=LocalDateTime(today,12*60);
   double total=0.0;
   int found=0;
   for(int delta=1;delta<=InpNoiseLookbackSessions*3+15 && found<InpNoiseLookbackSessions;delta++)
   {
      datetime candidate=today_local-delta*86400;
      MqlDateTime p; TimeToStruct(candidate,p);
      if(!IsRegularSession(p)) continue;
      MqlRates bar;
      if(!ExactMinuteBar(LocalDateTime(p,sample_minute),bar)) continue;
      long volume=(bar.real_volume>0 ? bar.real_volume : bar.tick_volume);
      if(volume<=0) continue;
      total+=(double)volume;
      found++;
   }
   if(found<InpNoiseLookbackSessions || total<=0.0) return 0.0;
   return (double)current_volume/(total/found);
}

bool DirectionAllowed(const int direction)
{
   if(direction>0) return InpDirectionMode==NOISE_BOTH || InpDirectionMode==NOISE_LONG_ONLY;
   if(direction<0) return InpDirectionMode==NOISE_BOTH || InpDirectionMode==NOISE_SHORT_ONLY;
   return false;
}

bool PassesPipelineFilters(const int direction,const double price,const MqlDateTime &today,
                           const int sample_minute,const long sample_volume)
{
   if(!DirectionAllowed(direction)) return false;
   if(InpRegimeMode!=NOISE_REGIME_NONE)
   {
      int period=(InpRegimeMode==NOISE_REGIME_EMA200 ? 200 : 50);
      double current=0.0,prior=0.0;
      if(!EMAValue(period,1,current)) return false;
      if(direction>0 && price<=current) return false;
      if(direction<0 && price>=current) return false;
      if(InpRegimeMode==NOISE_REGIME_EMA50_SLOPE)
      {
         if(!EMAValue(period,6,prior)) return false;
         if(direction>0 && current<=prior) return false;
         if(direction<0 && current>=prior) return false;
      }
   }
   if(InpMinimumDailyATRPercent>0.0 || InpMaximumDailyATRPercent>0.0)
   {
      double atr=0.0;
      if(!ATRValue(PERIOD_D1,InpStopATRPeriod,atr) || price<=0.0) return false;
      double percent=atr/price*100.0;
      if(InpMinimumDailyATRPercent>0.0 && percent<InpMinimumDailyATRPercent) return false;
      if(InpMaximumDailyATRPercent>0.0 && percent>InpMaximumDailyATRPercent) return false;
   }
   if(InpMinimumADX>0.0)
   {
      double adx=0.0;
      if(!ADXValue(adx) || adx<InpMinimumADX) return false;
   }
   long usable_volume=sample_volume;
   if(usable_volume<0) usable_volume=0;
   if(InpMinimumRelativeVolume>0.0 &&
      RelativeVolumeAtMinute(today,sample_minute,usable_volume)<InpMinimumRelativeVolume) return false;
   return true;
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   int digits=0; double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9) { probe*=10.0; digits++; }
   return NormalizeDouble(volume,digits);
}

double PriceToTick(const double value)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return value;
   return NormalizeDouble(MathRound(value/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double MinimumStopDistance()
{
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   return MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point,tick);
}

double RiskVolume(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_loss)) return 0.0;
   one_lot_loss=MathAbs(one_lot_loss);
   if(one_lot_loss<=0.0) return 0.0;
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(budget/one_lot_loss);
}

double PaperVolume(const MqlDateTime &today,const double open_price)
{
   double volatility=0.0;
   if(!RecentDailyVolatility(today,volatility)) return 0.0;
   double target=InpTargetDailyVolatilityPercent/100.0;
   double leverage=MathMin(InpMaximumNotionalLeverage,target/volatility);
   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(open_price<=0.0 || contract<=0.0 || leverage<=0.0) return 0.0;
   return NormalizeVolume(g_session_start_equity*leverage/(open_price*contract));
}

bool OurPosition(ulong &ticket,long &type)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      ticket=candidate;
      type=PositionGetInteger(POSITION_TYPE);
      return true;
   }
   return false;
}

void CloseOurPosition()
{
   ulong ticket=0; long type=-1;
   if(OurPosition(ticket,type)) trade.PositionClose(ticket);
}

void TimedCloseOncePerMinute(const datetime now_ny,const int minute)
{
   long key=DateKey(now_ny)*10000+minute;
   if(key==g_last_timed_close_key) return;
   g_last_timed_close_key=key;
   CloseOurPosition();
}

bool PrepareSession(const MqlDateTime &today)
{
   long key=(long)today.year*10000+(long)today.mon*100+today.day;
   if(g_session_key==key && g_session_open>0.0 && (InpUseCalyxRisk || g_session_volume>0.0)) return true;
   g_session_key=key;
   g_session_open=0.0;
   g_session_volume=0.0;
   g_session_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsRegularSession(today)) return false;
   MqlRates opening;
   if(!ExactMinuteBar(LocalDateTime(today,InpOpenNewYorkHour*60+InpOpenNewYorkMinute),opening)) return false;
   g_session_open=opening.open;
   g_session_volume=(InpUseCalyxRisk ? 1.0 : PaperVolume(today,g_session_open));
   return g_session_volume>0.0;
}

bool IsDecisionMinute(const int minute)
{
   int first=InpFirstDecisionNewYorkHour*60+InpFirstDecisionNewYorkMinute;
   int last=InpLastDecisionNewYorkHour*60+InpLastDecisionNewYorkMinute;
   return minute>=first && minute<=last && ((minute-first)%InpDecisionFrequencyMinutes)==0;
}

struct NoiseSignal
{
   int direction;
   int sample_minute;
   double close;
   double upper;
   double lower;
   double vwap;
   long volume;
};

bool BuildSignal(const MqlDateTime &today,const int decision_minute,NoiseSignal &state)
{
   state.direction=0;
   state.sample_minute=decision_minute-1;
   MqlRates sample;
   if(!ExactMinuteBar(LocalDateTime(today,state.sample_minute),sample)) return false;
   double sigma=0.0,previous_close=0.0;
   if(!NoiseSigma(today,state.sample_minute,sigma)) return false;
   if(!SessionVWAP(today,state.sample_minute,state.vwap)) return false;
   if(!PreviousRegularClose(today,previous_close)) return false;
   state.close=sample.close;
   state.volume=(sample.real_volume>0 ? sample.real_volume : sample.tick_volume);
   state.upper=MathMax(g_session_open,previous_close)*(1.0+InpVolatilityMultiplier*sigma);
   state.lower=MathMin(g_session_open,previous_close)*(1.0-InpVolatilityMultiplier*sigma);
   if(state.close>state.upper && state.close>state.vwap) state.direction=1;
   else if(state.close<state.lower && state.close<state.vwap) state.direction=-1;
   return true;
}

bool ShouldExit(const int current,const NoiseSignal &state)
{
   if(InpExitMode==NOISE_EXIT_TIME_ONLY) return false;
   if(InpExitMode==NOISE_EXIT_BAND_AND_VWAP)
      return current>0 ? state.close<=MathMax(state.upper,state.vwap) : state.close>=MathMin(state.lower,state.vwap);
   if(InpExitMode==NOISE_EXIT_BAND_ONLY)
      return current>0 ? state.close<=state.upper : state.close>=state.lower;
   if(InpExitMode==NOISE_EXIT_VWAP_ONLY)
      return current>0 ? state.close<=state.vwap : state.close>=state.vwap;
   return current>0 ? state.close<=state.lower : state.close>=state.upper;
}

bool PipelineStopDistance(const int direction,const double entry,const NoiseSignal &state,double &distance)
{
   if(InpStopMode==NOISE_STOP_STRUCTURAL)
   {
      double anchor=(direction>0 ? MathMax(state.upper,state.vwap) : MathMin(state.lower,state.vwap));
      distance=(direction>0 ? entry-anchor : anchor-entry);
   }
   else if(InpStopMode==NOISE_STOP_PERCENT)
      distance=entry*InpStopPercent/100.0;
   else
   {
      double atr=0.0;
      if(!ATRValue(InpStopATRTimeframe,InpStopATRPeriod,atr)) return false;
      distance=atr*InpStopATRMultiplier;
   }
   distance=MathMax(distance,MinimumStopDistance());
   return distance>0.0 && MathIsValidNumber(distance);
}

bool OpenDirection(const int direction,const MqlDateTime &today,const NoiseSignal &state)
{
   if(direction==0 || g_session_volume<=0.0 || !DirectionAllowed(direction)) return false;
   if(InpUseCalyxRisk && !PassesPipelineFilters(direction,state.close,today,state.sample_minute,state.volume)) return false;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=(direction>0 ? ask : bid);
   if(entry<=0.0) return false;
   double stop=0.0,target=0.0,volume=g_session_volume;
   if(InpUseCalyxRisk)
   {
      double distance=0.0;
      if(!PipelineStopDistance(direction,entry,state,distance)) return false;
      double minimum=MinimumStopDistance();
      if(direction>0) stop=MathMin(entry-distance,bid-minimum);
      else stop=MathMax(entry+distance,ask+minimum);
      stop=PriceToTick(stop);
      distance=MathAbs(entry-stop);
      if(distance<=0.0) return false;
      if(InpTargetR>0.0) target=PriceToTick(direction>0 ? entry+distance*InpTargetR : entry-distance*InpTargetR);
      volume=RiskVolume(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,entry,stop);
      if(volume<=0.0) return false;
      g_initial_risk=distance;
   }
   bool opened=(direction>0
      ? trade.Buy(volume,_Symbol,0.0,stop,target,InpUseCalyxRisk ? "Calyx noise boundary long" : "Raw noise-band VWAP long")
      : trade.Sell(volume,_Symbol,0.0,stop,target,InpUseCalyxRisk ? "Calyx noise boundary short" : "Raw noise-band VWAP short"));
   if(!opened) g_initial_risk=0.0;
   return opened;
}

void ManagePipelinePosition()
{
   if(!InpUseCalyxRisk) return;
   ulong ticket=0; long type=-1;
   if(!OurPosition(ticket,type) || !PositionSelectByTicket(ticket)) { g_initial_risk=0.0; return; }
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   if(entry<=0.0 || stop<=0.0) return;
   if(g_initial_risk<=0.0) g_initial_risk=MathAbs(entry-stop);
   if(g_initial_risk<=0.0) return;
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double price=(type==POSITION_TYPE_BUY ? bid : ask);
   double favorable=(type==POSITION_TYPE_BUY ? price-entry : entry-price);
   double achieved=favorable/g_initial_risk;
   double proposed=stop;
   if(InpBreakEvenAtR>0.0 && achieved>=InpBreakEvenAtR)
   {
      if(type==POSITION_TYPE_BUY) proposed=MathMax(proposed,entry);
      else proposed=MathMin(proposed,entry);
   }
   if(InpTrailStartR>0.0 && InpTrailATRMultiplier>0.0 && achieved>=InpTrailStartR)
   {
      double atr=0.0;
      if(ATRValue(InpTrailATRTimeframe,InpTrailATRPeriod,atr))
      {
         double trail=(type==POSITION_TYPE_BUY ? price-atr*InpTrailATRMultiplier : price+atr*InpTrailATRMultiplier);
         if(type==POSITION_TYPE_BUY) proposed=MathMax(proposed,trail);
         else proposed=MathMin(proposed,trail);
      }
   }
   double minimum=MinimumStopDistance();
   if(type==POSITION_TYPE_BUY) proposed=MathMin(proposed,bid-minimum);
   else proposed=MathMax(proposed,ask+minimum);
   proposed=PriceToTick(proposed);
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   bool improves=(type==POSITION_TYPE_BUY ? proposed>stop+tick/2.0 : proposed<stop-tick/2.0);
   if(improves) trade.PositionModify(ticket,proposed,target);
}

void ApplySignal(const MqlDateTime &today,const NoiseSignal &state)
{
   ulong ticket=0; long type=-1;
   bool has_position=OurPosition(ticket,type);
   int current=(has_position ? (type==POSITION_TYPE_BUY ? 1 : -1) : 0);
   if(current!=0)
   {
      if(current==state.direction) return;
      if(!ShouldExit(current,state)) return;
      if(!trade.PositionClose(ticket)) return;
      g_initial_risk=0.0;
   }
   if(state.direction!=0) OpenDirection(state.direction,today,state);
}

void Evaluate()
{
   if(!InpEnableTrading) return;
   ManagePipelinePosition();
   datetime now_server=TimeCurrent();
   datetime now_ny=ServerToNewYork(now_server);
   MqlDateTime today; TimeToStruct(now_ny,today);
   int minute=today.hour*60+today.min;
   int close_minute=InpCloseNewYorkHour*60+InpCloseNewYorkMinute;
   if(minute>=close_minute)
   {
      TimedCloseOncePerMinute(now_ny,minute);
      g_initial_risk=0.0;
      return;
   }
   int lunch_start=InpLunchStartNewYorkHour*60+InpLunchStartNewYorkMinute;
   int lunch_end=InpLunchEndNewYorkHour*60+InpLunchEndNewYorkMinute;
   if(InpSkipLunch && minute>=lunch_start && minute<lunch_end)
   {
      TimedCloseOncePerMinute(now_ny,minute);
      g_initial_risk=0.0;
      return;
   }
   if(!IsDecisionMinute(minute)) return;
   long decision_key=DateKey(now_ny)*10000+minute;
   if(decision_key==g_last_decision_key) return;
   g_last_decision_key=decision_key;
   if(!PrepareSession(today)) { CloseOurPosition(); return; }
   NoiseSignal state;
   if(!BuildSignal(today,minute,state)) { CloseOurPosition(); return; }
   ApplySignal(today,state);
}

int OnInit()
{
   int open_minute=InpOpenNewYorkHour*60+InpOpenNewYorkMinute;
   int first=InpFirstDecisionNewYorkHour*60+InpFirstDecisionNewYorkMinute;
   int last=InpLastDecisionNewYorkHour*60+InpLastDecisionNewYorkMinute;
   int close_minute=InpCloseNewYorkHour*60+InpCloseNewYorkMinute;
   int lunch_start=InpLunchStartNewYorkHour*60+InpLunchStartNewYorkMinute;
   int lunch_end=InpLunchEndNewYorkHour*60+InpLunchEndNewYorkMinute;
   if(InpNoiseLookbackSessions<5 || InpVolatilityMultiplier<=0.0 || InpDecisionFrequencyMinutes<1 ||
      InpTargetDailyVolatilityPercent<=0.0 || InpMaximumNotionalLeverage<=0.0 ||
      InpRiskPercent<=0.0 || InpRiskPercent>10.0 || InpStopPercent<=0.0 ||
      InpStopATRPeriod<2 || InpStopATRMultiplier<=0.0 || InpTargetR<0.0 ||
      InpBreakEvenAtR<0.0 || InpTrailStartR<0.0 || InpTrailATRPeriod<2 || InpTrailATRMultiplier<=0.0 ||
      InpMinimumDailyATRPercent<0.0 || InpMaximumDailyATRPercent<0.0 ||
      (InpMaximumDailyATRPercent>0.0 && InpMinimumDailyATRPercent>InpMaximumDailyATRPercent) ||
      InpMinimumADX<0.0 || InpADXPeriod<2 || InpMinimumRelativeVolume<0.0 ||
      (InpSkipLunch && lunch_end<=lunch_start) ||
      first<=open_minute || last<first || close_minute<=last || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(!InpEnableTrading) Print("Raw research gate is OFF. Load the research SET deliberately.");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   Evaluate();
}
