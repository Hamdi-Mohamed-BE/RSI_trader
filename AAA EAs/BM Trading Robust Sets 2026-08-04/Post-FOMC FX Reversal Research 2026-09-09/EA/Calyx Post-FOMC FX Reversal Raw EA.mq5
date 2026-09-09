#property strict
#property version   "1.00"
#property description "Raw research implementation of Lee and Wang's post-FOMC FX return window."

#include <Trade/Trade.mqh>

input bool   InpEnableTrading=true;
input bool   InpUsdIsBase=false;
input double InpRiskPercent=1.0;
input int    InpAtrPeriod=14;
input double InpEmergencyStopAtrMultiple=10.0;
input int    InpMaxDeviationPoints=30;
input long   InpMagic=260909601;
input bool   InpUseAutomaticLiveServerOffset=true;
input int    InpTesterServerUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_atr_handle=INVALID_HANDLE;
int g_last_event_key=0;

int g_fomc_dates[]={
   20210127,20210317,20210428,20210616,20210728,20210922,20211103,20211215,
   20220126,20220316,20220504,20220615,20220727,20220921,20221102,20221214,
   20230201,20230322,20230503,20230614,20230726,20230920,20231101,20231213,
   20240131,20240320,20240501,20240612,20240731,20240918,20241107,20241218,
   20250129,20250319,20250507,20250618,20250730,20250917,20251029,20251210,
   20260128,20260318,20260429,20260617,20260729
};

int DaysInMonth(const int year,const int month)
{
   if(month==2)
      return ((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28;
   if(month==4 || month==6 || month==9 || month==11) return 30;
   return 31;
}

int NthSunday(const int year,const int month,const int ordinal)
{
   MqlDateTime value={0};
   value.year=year;
   value.mon=month;
   value.day=1;
   datetime first=StructToTime(value);
   MqlDateTime first_parts;
   TimeToStruct(first,first_parts);
   int first_sunday=1+((7-first_parts.day_of_week)%7);
   return first_sunday+(ordinal-1)*7;
}

bool NewYorkDateUsesDST(const MqlDateTime &ny)
{
   int march_start=NthSunday(ny.year,3,2);
   int november_end=NthSunday(ny.year,11,1);
   if(ny.mon<3 || ny.mon>11) return false;
   if(ny.mon>3 && ny.mon<11) return true;
   if(ny.mon==3) return ny.day>=march_start;
   return ny.day<november_end;
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();
   datetime utc=TimeGMT();
   if(server<=0 || utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)(MathRound((double)(server-utc)/1800.0)*1800.0);
}

datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime ny=source;
   datetime local_value=StructToTime(ny);
   int ny_offset=(NewYorkDateUsesDST(ny) ? -4 : -5);
   datetime utc=local_value-ny_offset*3600;
   return utc+ServerUTCOffsetSeconds();
}

void EventTimes(const int event_key,datetime &entry_time,datetime &exit_time)
{
   MqlDateTime announcement={0};
   announcement.year=event_key/10000;
   announcement.mon=(event_key/100)%100;
   announcement.day=event_key%100;
   announcement.hour=14;
   datetime local_announcement=StructToTime(announcement);
   MqlDateTime entry_parts,exit_parts;
   TimeToStruct(local_announcement+12*3600,entry_parts);
   TimeToStruct(local_announcement+24*3600,exit_parts);
   entry_time=NewYorkToServer(entry_parts);
   exit_time=NewYorkToServer(exit_parts);
}

bool CurrentEventWindow(const datetime now,int &event_key,datetime &entry_time,datetime &exit_time)
{
   int count=ArraySize(g_fomc_dates);
   for(int i=count-1;i>=0;i--)
   {
      datetime candidate_entry,candidate_exit;
      EventTimes(g_fomc_dates[i],candidate_entry,candidate_exit);
      if(now>=candidate_entry && now<candidate_exit)
      {
         event_key=g_fomc_dates[i];
         entry_time=candidate_entry;
         exit_time=candidate_exit;
         return true;
      }
      if(now>=candidate_exit) break;
   }
   return false;
}

bool SelectOurPosition(ulong &ticket)
{
   ticket=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if((long)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      ticket=candidate;
      return true;
   }
   return false;
}

bool PositionEventExit(const ulong ticket,datetime &exit_time)
{
   if(!PositionSelectByTicket(ticket)) return false;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   int count=ArraySize(g_fomc_dates);
   for(int i=count-1;i>=0;i--)
   {
      datetime candidate_entry,candidate_exit;
      EventTimes(g_fomc_dates[i],candidate_entry,candidate_exit);
      if(opened>=candidate_entry-300 && opened<candidate_exit)
      {
         exit_time=candidate_exit;
         return true;
      }
      if(opened>=candidate_exit) break;
   }
   return false;
}

double CurrentATR()
{
   if(g_atr_handle==INVALID_HANDLE) return 0.0;
   double values[1];
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1) return 0.0;
   return values[0];
}

int VolumeDigits(const double step)
{
   if(step>=1.0) return 0;
   if(step>=0.1) return 1;
   if(step>=0.01) return 2;
   if(step>=0.001) return 3;
   return 4;
}

double RiskVolume(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   double one_lot_profit=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit)) return 0.0;
   double one_lot_loss=MathAbs(one_lot_profit);
   if(one_lot_loss<=0.0) return 0.0;
   double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) step=minimum;
   double raw=risk_money/one_lot_loss;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   return NormalizeDouble(volume,VolumeDigits(step));
}

bool OpenRawPosition(const int event_key)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double atr=CurrentATR();
   if(atr<=0.0) return false;
   bool buy=InpUsdIsBase;
   double entry=(buy ? tick.ask : tick.bid);
   double distance=atr*InpEmergencyStopAtrMultiple;
   double stop=(buy ? entry-distance : entry+distance);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   stop=NormalizeDouble(stop,digits);
   ENUM_ORDER_TYPE order_type=(buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double volume=RiskVolume(order_type,entry,stop);
   if(volume<=0.0) return false;
   string comment="Raw post-FOMC +12h to +24h";
   bool placed=(buy ? trade.Buy(volume,_Symbol,0.0,stop,0.0,comment)
                    : trade.Sell(volume,_Symbol,0.0,stop,0.0,comment));
   if(placed) g_last_event_key=event_key;
   return placed;
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpAtrPeriod<=0 || InpEmergencyStopAtrMultiple<=0.0 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   g_atr_handle=iATR(_Symbol,PERIOD_H1,InpAtrPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   datetime now=TimeCurrent();
   ulong ticket=0;
   if(SelectOurPosition(ticket))
   {
      datetime exit_time=0;
      if(PositionEventExit(ticket,exit_time) && now>=exit_time)
         trade.PositionClose(ticket,InpMaxDeviationPoints);
      return;
   }
   if(!InpEnableTrading) return;
   int event_key=0;
   datetime entry_time=0,exit_time=0;
   if(!CurrentEventWindow(now,event_key,entry_time,exit_time)) return;
   if(g_last_event_key==event_key) return;
   OpenRawPosition(event_key);
}
