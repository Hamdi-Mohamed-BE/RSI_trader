#property strict
#property version   "1.00"
#property description "Raw CFD transfer of Ma, Bouri, Xu and Zhou's precious-metals night effect."

#include <Trade/Trade.mqh>

enum ENUM_NIGHT_EFFECT_ASSET
{
   NIGHT_EFFECT_GOLD=0,
   NIGHT_EFFECT_SILVER=1
};

input bool                    InpEnableTrading=true;
input ENUM_NIGHT_EFFECT_ASSET InpAssetMode=NIGHT_EFFECT_GOLD;
input double                  InpRiskPercent=1.0;
input int                     InpAtrPeriod=14;
input double                  InpEmergencyStopAtrMultiple=2.0;
input int                     InpMaxDeviationPoints=30;
input long                    InpMagic=260909701;
input bool                    InpUseAutomaticLiveServerOffset=true;
input int                     InpTesterServerUTCOffsetHours=0;
input int                     InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_atr_handle=INVALID_HANDLE;
int g_signal_date=0;
int g_signal_direction=0;
long g_last_window_key=0;

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();
   datetime utc=TimeGMT();
   if(server<=0 || utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)(MathRound((double)(server-utc)/1800.0)*1800.0);
}

int DateKey(const MqlDateTime &value)
{
   return value.year*10000+value.mon*100+value.day;
}

datetime UTCDateTime(const MqlDateTime &date_only,const int hour,const int minute)
{
   MqlDateTime value=date_only;
   value.hour=hour;
   value.min=minute;
   value.sec=0;
   return StructToTime(value);
}

bool ReadM15Close(const datetime utc_bar_open,double &open_value,double &close_value)
{
   datetime server_bar_open=utc_bar_open+ServerUTCOffsetSeconds();
   int shift=iBarShift(_Symbol,PERIOD_M15,server_bar_open,true);
   if(shift<0) return false;
   MqlRates bar[1];
   if(CopyRates(_Symbol,PERIOD_M15,shift,1,bar)!=1) return false;
   if(bar[0].time!=server_bar_open) return false;
   open_value=bar[0].open;
   close_value=bar[0].close;
   return true;
}

void CaptureSignal(const datetime now_utc,const MqlDateTime &utc_parts)
{
   if(utc_parts.day_of_week==0 || utc_parts.day_of_week==6) return;
   int today=DateKey(utc_parts);
   if(g_signal_date==today) return;
   datetime signal_end=UTCDateTime(utc_parts,13,30);
   if(now_utc<signal_end) return;
   double first_open=0.0,unused_close=0.0;
   double unused_open=0.0,last_close=0.0;
   if(!ReadM15Close(UTCDateTime(utc_parts,13,0),first_open,unused_close)) return;
   if(!ReadM15Close(UTCDateTime(utc_parts,13,15),unused_open,last_close)) return;
   if(last_close==first_open) return;
   g_signal_date=today;
   g_signal_direction=(last_close>first_open ? 1 : -1);
}

int PreviousTradingDateKey(const datetime now_utc,const MqlDateTime &utc_parts)
{
   datetime candidate=UTCDateTime(utc_parts,0,0)-86400;
   MqlDateTime parts;
   TimeToStruct(candidate,parts);
   while(parts.day_of_week==0 || parts.day_of_week==6)
   {
      candidate-=86400;
      TimeToStruct(candidate,parts);
   }
   return DateKey(parts);
}

bool ActiveTargetWindow(const datetime now_utc,const MqlDateTime &utc_parts,
                        int &window_index,datetime &exit_utc,int &required_signal_date)
{
   window_index=-1;
   exit_utc=0;
   required_signal_date=0;
   int minute_of_day=utc_parts.hour*60+utc_parts.min;
   int today=DateKey(utc_parts);

   if(InpAssetMode==NIGHT_EFFECT_SILVER && minute_of_day>=1050 && minute_of_day<1080)
   {
      window_index=0; // SHFE night interval 10: 01:30-02:00 Beijing.
      exit_utc=UTCDateTime(utc_parts,18,0);
      required_signal_date=today;
      return true;
   }

   int start_minutes[4]={60,180,330,390};
   int end_minutes[4]={90,210,360,420};
   int max_windows=(InpAssetMode==NIGHT_EFFECT_GOLD ? 1 : 4);
   for(int i=0;i<max_windows;i++)
   {
      if(minute_of_day>=start_minutes[i] && minute_of_day<end_minutes[i])
      {
         window_index=i+1; // Gold uses day interval 1; silver uses day 1,5,6,8.
         exit_utc=UTCDateTime(utc_parts,end_minutes[i]/60,end_minutes[i]%60);
         required_signal_date=PreviousTradingDateKey(now_utc,utc_parts);
         return true;
      }
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
   // Never force the broker minimum lot when it would exceed the selected risk.
   if(raw+1e-12<minimum) return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMin(maximum,volume);
   return NormalizeDouble(volume,VolumeDigits(step));
}

bool OpenRawPosition(const int direction,const int window_index)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double atr=CurrentATR();
   if(atr<=0.0) return false;
   bool buy=(direction>0);
   double entry=(buy ? tick.ask : tick.bid);
   double distance=atr*InpEmergencyStopAtrMultiple;
   double stop=(buy ? entry-distance : entry+distance);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   stop=NormalizeDouble(stop,digits);
   ENUM_ORDER_TYPE order_type=(buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double volume=RiskVolume(order_type,entry,stop);
   if(volume<=0.0) return false;
   string comment=StringFormat("Raw night effect window %d",window_index);
   return (buy ? trade.Buy(volume,_Symbol,0.0,stop,0.0,comment)
               : trade.Sell(volume,_Symbol,0.0,stop,0.0,comment));
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
   datetime now_server=TimeCurrent();
   datetime now_utc=now_server-ServerUTCOffsetSeconds();
   MqlDateTime utc_parts;
   TimeToStruct(now_utc,utc_parts);
   CaptureSignal(now_utc,utc_parts);

   int window_index=0;
   datetime exit_utc=0;
   int required_signal_date=0;
   bool in_window=ActiveTargetWindow(now_utc,utc_parts,window_index,exit_utc,required_signal_date);
   ulong ticket=0;
   if(SelectOurPosition(ticket))
   {
      if(!in_window || now_utc>=exit_utc)
         trade.PositionClose(ticket,InpMaxDeviationPoints);
      return;
   }
   if(!InpEnableTrading || !in_window) return;
   if(g_signal_date!=required_signal_date || g_signal_direction==0) return;
   long window_key=(long)required_signal_date*10+window_index;
   if(g_last_window_key==window_key) return;
   if(OpenRawPosition(g_signal_direction,window_index)) g_last_window_key=window_key;
}
