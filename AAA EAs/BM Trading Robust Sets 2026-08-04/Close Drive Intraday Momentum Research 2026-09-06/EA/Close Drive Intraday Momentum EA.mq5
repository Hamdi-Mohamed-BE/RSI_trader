#property copyright "Calyx close-drive intraday momentum research EA"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_CLOSE_DRIVE_STOP
{
   STOP_SIGNAL_CANDLE=0,
   STOP_ATR=1,
   STOP_OPENING_RANGE=2
};

enum ENUM_CLOSE_DRIVE_EXIT
{
   EXIT_SESSION_CLOSE=0,
   EXIT_FIXED_RR=1
};

input group "Signal"
input ENUM_TIMEFRAMES InpDecisionTimeframe=PERIOD_M5;
input bool InpIncludeOvernightReturn=true;
input int InpEntryHourNY=15;
input int InpEntryMinuteNY=30;
input double InpMinimumOpeningMoveATR=0.25;
input bool InpRequireSameDirectionAtEntry=true;
input bool InpUseVWAPConfirmation=false;
input bool InpAllowLong=true;
input bool InpAllowShort=true;

input group "Risk, stop and target"
input double InpRiskPercent=1.0;
input ENUM_CLOSE_DRIVE_STOP InpStopMode=STOP_ATR;
input int InpATRPeriod=14;
input ENUM_TIMEFRAMES InpATRTimeframe=PERIOD_M15;
input double InpStopATR=1.0;
input double InpStopBufferATR=0.10;
input double InpMaximumStopATR=3.0;
input ENUM_CLOSE_DRIVE_EXIT InpExitMode=EXIT_SESSION_CLOSE;
input double InpRewardRisk=1.0;
input int InpCloseHourNY=15;
input int InpCloseMinuteNY=55;

input group "Trade management"
input bool InpUseBreakEven=false;
input double InpBreakEvenAtR=0.50;
input double InpBreakEvenLockR=0.0;
input bool InpUseATRTrailing=false;
input double InpTrailStartAtR=0.75;
input double InpTrailATR=1.0;
input bool InpUseDynamicM15Stop=false;
input double InpDynamicTriggerR=0.50;
input double InpDynamicLockR=0.20;

input group "Time and execution"
input bool InpAutoServerUtcOffsetLive=true;
input int InpServerUtcOffsetHours=0;
input double InpMaximumSpreadATR=0.20;
input int InpMaximumDeviationPoints=80;
input long InpMagic=969060001;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar=0;

double NormalizePrice(const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double value)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   double lots=MathFloor(value/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return MathMin(lots,maximum);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot=0.0;
   if(cash<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   return NormalizeLots(cash/one_lot);
}

bool ReadATR(const int shift,double &value)
{
   double values[];
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,shift,1,values)!=1) return false;
   value=values[0];
   return value>0.0;
}

int ServerUtcOffsetSeconds()
{
   if(!InpAutoServerUtcOffsetLive || (bool)MQLInfoInteger(MQL_TESTER)) return InpServerUtcOffsetHours*3600;
   datetime server=TimeTradeServer(),utc=TimeGMT();
   if(server<=0 || utc<=0) return InpServerUtcOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime BuildUtcTime(const int year,const int month,const int day,const int hour)
{
   MqlDateTime value; ZeroMemory(value);
   value.year=year; value.mon=month; value.day=day; value.hour=hour;
   return StructToTime(value);
}

int NthSunday(const int year,const int month,const int nth)
{
   MqlDateTime first; TimeToStruct(BuildUtcTime(year,month,1,0),first);
   return 1+((7-first.day_of_week)%7)+(nth-1)*7;
}

int NewYorkUtcOffsetHours(const datetime utc_time)
{
   MqlDateTime parts; TimeToStruct(utc_time,parts);
   datetime start=BuildUtcTime(parts.year,3,NthSunday(parts.year,3,2),7);
   datetime finish=BuildUtcTime(parts.year,11,NthSunday(parts.year,11,1),6);
   return (utc_time>=start && utc_time<finish ? -4 : -5);
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc_time=server_time-ServerUtcOffsetSeconds();
   return utc_time+NewYorkUtcOffsetHours(utc_time)*3600;
}

int NewYorkDateKey(const datetime server_time)
{
   MqlDateTime ny; TimeToStruct(ServerToNewYork(server_time),ny);
   return ny.year*10000+ny.mon*100+ny.day;
}

bool NewYorkParts(const datetime server_time,MqlDateTime &ny)
{
   if(server_time<=0) return false;
   TimeToStruct(ServerToNewYork(server_time),ny);
   return true;
}

bool IsNewYorkMinute(const datetime server_time,const int hour,const int minute)
{
   MqlDateTime ny; if(!NewYorkParts(server_time,ny)) return false;
   return ny.day_of_week>=1 && ny.day_of_week<=5 && ny.hour==hour && ny.min==minute;
}

bool IsHolidayWindow(const datetime server_time)
{
   MqlDateTime ny; NewYorkParts(server_time,ny);
   // Conservative holiday exclusion: shortened US cash sessions have no close drive.
   if(ny.mon==7 && ny.day>=2 && ny.day<=5) return true;
   if(ny.mon==12 && ny.day>=23 && ny.day<=26) return true;
   if(ny.mon==11 && ny.day_of_week==5 && ny.day>=23 && ny.day<=29) return true;
   return false;
}

bool IsAtOrAfterClose(const datetime server_time)
{
   MqlDateTime ny; if(!NewYorkParts(server_time,ny)) return false;
   if(ny.day_of_week<1 || ny.day_of_week>5) return false;
   return ny.hour>InpCloseHourNY || (ny.hour==InpCloseHourNY && ny.min>=InpCloseMinuteNY);
}

bool NearBrokerSessionEnd()
{
   MqlDateTime now; TimeToStruct(TimeCurrent(),now);
   int seconds=now.hour*3600+now.min*60+now.sec;
   for(uint index=0;index<20;index++)
   {
      datetime from=0,to=0;
      if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)now.day_of_week,index,from,to)) break;
      int start=(int)((long)from%86400),end=(int)((long)to%86400);
      if(end==0) end=86400;
      if(end<=start) end+=86400;
      if(seconds>=start && seconds<end && seconds>=end-300) return true;
   }
   return false;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ticket=PositionGetTicket(index);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   ticket=0; return false;
}

string RiskKey(const ulong identifier)
{
   return "CALYX.CLOSEDRIVE."+(string)InpMagic+"."+(string)identifier+".R";
}

void StoreInitialRisk()
{
   ulong ticket=0; if(!SelectOurPosition(ticket)) return;
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   double risk=MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
   if(identifier>0 && risk>0.0) GlobalVariableSet(RiskKey(identifier),risk);
}

double InitialRisk()
{
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   string key=RiskKey(identifier);
   if(identifier>0 && GlobalVariableCheck(key)) return GlobalVariableGet(key);
   return MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
}

bool AlreadyTradedToday(const int date_key)
{
   datetime now=TimeCurrent();
   if(!HistorySelect(now-4*86400,now+3600)) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if((entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT) && NewYorkDateKey((datetime)HistoryDealGetInteger(deal,DEAL_TIME))==date_key) return true;
   }
   return false;
}

bool FindOpeningData(const int date_key,double &open_price,double &close_price,double &range_high,double &range_low,double &vwap)
{
   MqlRates rates[]; ArraySetAsSeries(rates,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,0,1800,rates);
   if(copied<=0) return false;
   bool found_open=false,found_close=false;
   double previous_close=0.0;
   int opening_bars=0;
   double pv=0.0,volume=0.0;
   range_high=-DBL_MAX; range_low=DBL_MAX;
   for(int i=copied-1;i>=0;i--)
   {
      MqlDateTime ny; if(!NewYorkParts(rates[i].time,ny)) continue;
      int key=ny.year*10000+ny.mon*100+ny.day;
      int minutes=ny.hour*60+ny.min;
      // Chronological iteration retains the latest completed prior cash close.
      if(key<date_key && minutes==955) previous_close=rates[i].close;
      if(key!=date_key) continue;
      if(minutes==570) { open_price=rates[i].open; found_open=true; }
      if(minutes>=570 && minutes<600)
      {
         opening_bars++;
         range_high=MathMax(range_high,rates[i].high);
         range_low=MathMin(range_low,rates[i].low);
      }
      if(minutes==595) { close_price=rates[i].close; found_close=true; }
      if(minutes>=570 && minutes<InpEntryHourNY*60+InpEntryMinuteNY)
      {
         double weight=(double)MathMax((long)1,rates[i].tick_volume);
         pv+=((rates[i].high+rates[i].low+rates[i].close)/3.0)*weight;
         volume+=weight;
      }
   }
   if(volume>0.0) vwap=pv/volume;
   if(InpIncludeOvernightReturn)
   {
      if(previous_close<=0.0) return false;
      open_price=previous_close;
   }
   return found_open && found_close && opening_bars==6 && range_high>range_low && volume>0.0;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool SendEntry(const int direction,const double atr,const double range_high,const double range_low)
{
   MqlRates signal[]; ArraySetAsSeries(signal,true);
   if(CopyRates(_Symbol,InpDecisionTimeframe,0,2,signal)!=2) return false;
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=0.0;
   if(InpStopMode==STOP_SIGNAL_CANDLE) stop=(direction>0 ? signal[1].low-InpStopBufferATR*atr : signal[1].high+InpStopBufferATR*atr);
   else if(InpStopMode==STOP_OPENING_RANGE) stop=(direction>0 ? range_low-InpStopBufferATR*atr : range_high+InpStopBufferATR*atr);
   else stop=entry-direction*InpStopATR*atr;
   // A structural level already behind the proposed direction is not a stop.
   if(direction*(entry-stop)<=0.0) return false;
   double distance=MathAbs(entry-stop);
   if(distance>InpMaximumStopATR*atr) stop=entry-direction*InpMaximumStopATR*atr;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(MathAbs(entry-stop)<gap) stop=entry-direction*gap;
   stop=NormalizePrice(stop); distance=MathAbs(entry-stop);
   double target=(InpExitMode==EXIT_FIXED_RR ? NormalizePrice(entry+direction*InpRewardRisk*distance) : 0.0);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) { Print("CloseDrive skipped: risk-sized volume below broker minimum."); return false; }
   g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetTypeFillingBySymbol(_Symbol); g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"CloseDrive long") : g_trade.Sell(lots,_Symbol,0.0,stop,target,"CloseDrive short"));
   if(sent) StoreInitialRisk(); else Print("CloseDrive rejected: ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ProcessSignal()
{
   datetime current_bar=iTime(_Symbol,InpDecisionTimeframe,0);
   if(NearBrokerSessionEnd()) return;
   if(IsHolidayWindow(current_bar)) return;
   if(!IsNewYorkMinute(current_bar,InpEntryHourNY,InpEntryMinuteNY)) return;
   int date_key=NewYorkDateKey(current_bar);
   ulong ticket=0; if(SelectOurPosition(ticket) || AlreadyTradedToday(date_key)) return;
   double atr=0.0; if(!ReadATR(1,atr) || !SpreadPasses(atr)) return;
   double opening=0.0,opening_close=0.0,range_high=0.0,range_low=0.0,vwap=0.0;
   if(!FindOpeningData(date_key,opening,opening_close,range_high,range_low,vwap)) return;
   double move=opening_close-opening;
   if(move==0.0 || MathAbs(move)<InpMinimumOpeningMoveATR*atr) return;
   int direction=(move>0.0 ? 1 : -1);
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   double current=(direction>0 ? tick.ask : tick.bid);
   if(InpRequireSameDirectionAtEntry && (direction>0 ? current<=opening : current>=opening)) return;
   if(InpUseVWAPConfirmation && (direction>0 ? current<=vwap : current>=vwap)) return;
   if((direction>0 && !InpAllowLong) || (direction<0 && !InpAllowShort)) return;
   SendEntry(direction,atr,range_high,range_low);
}

void ManagePosition()
{
   ulong ticket=0; if(!SelectOurPosition(ticket)) return;
   if(IsAtOrAfterClose(TimeCurrent()) || NearBrokerSessionEnd() || NewYorkDateKey((datetime)PositionGetInteger(POSITION_TIME))!=NewYorkDateKey(TimeCurrent()))
   {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints)) Print("CloseDrive timed close failed: ",g_trade.ResultRetcodeDescription());
      return;
   }
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   double atr=0.0; if(!ReadATR(0,atr)) return;
   bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
   double open=PositionGetDouble(POSITION_PRICE_OPEN),stop=PositionGetDouble(POSITION_SL);
   double current=(buy ? tick.bid : tick.ask),risk=InitialRisk();
   if(risk<=0.0) return;
   double favorable=(buy ? current-open : open-current);
   double candidate=stop;
   bool has_candidate=false;
   if(InpUseDynamicM15Stop && favorable>=InpDynamicTriggerR*risk)
   {
      double close15=iClose(_Symbol,PERIOD_M15,1);
      if(iTime(_Symbol,PERIOD_M15,1)<(datetime)PositionGetInteger(POSITION_TIME)) return;
      if((buy && close15>=open+InpDynamicTriggerR*risk) || (!buy && close15<=open-InpDynamicTriggerR*risk))
      { candidate=open+(buy ? 1.0 : -1.0)*InpDynamicLockR*risk; has_candidate=true; }
   }
   if(InpUseBreakEven && favorable>=InpBreakEvenAtR*risk)
   { double be=open+(buy ? 1.0 : -1.0)*InpBreakEvenLockR*risk; candidate=(has_candidate ? (buy ? MathMax(candidate,be) : MathMin(candidate,be)) : be); has_candidate=true; }
   if(InpUseATRTrailing && favorable>=InpTrailStartAtR*risk)
   { double trail=current+(buy ? -1.0 : 1.0)*InpTrailATR*atr; candidate=(has_candidate ? (buy ? MathMax(candidate,trail) : MathMin(candidate,trail)) : trail); has_candidate=true; }
   if(!has_candidate) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   candidate=(buy ? MathMin(candidate,tick.bid-gap) : MathMax(candidate,tick.ask+gap)); candidate=NormalizePrice(candidate);
   bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
   if(improves && !g_trade.PositionModify(ticket,candidate,PositionGetDouble(POSITION_TP))) Print("CloseDrive stop update failed: ",g_trade.ResultRetcodeDescription());
}

int OnInit()
{
   if(InpEntryHourNY<9 || InpEntryHourNY>15 || InpEntryMinuteNY<0 || InpEntryMinuteNY>59 || InpRiskPercent<=0.0 || InpATRPeriod<2 || InpStopATR<=0.0 || InpMaximumStopATR<=0.0 || InpRewardRisk<0.5 || InpCloseHourNY<InpEntryHourNY) return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpATRTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar=iTime(_Symbol,InpDecisionTimeframe,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   ManagePosition();
   datetime bar=iTime(_Symbol,InpDecisionTimeframe,0);
   if(bar<=0 || bar==g_last_bar) return;
   g_last_bar=bar;
   ProcessSignal();
}
