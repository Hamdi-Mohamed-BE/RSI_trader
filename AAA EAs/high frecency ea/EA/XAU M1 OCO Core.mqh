#include <Trade/Trade.mqh>

input group "Distances"
input bool InpUseATRDistances=false;
input int InpATRPeriod=14;
input double InpEntryOffsetPrice=0.40;
input double InpStopDistancePrice=0.50;
input double InpTrailStartPrice=0.80;
input double InpTrailDistancePrice=0.45;
input double InpEntryOffsetATR=0.25;
input double InpStopDistanceATR=0.75;
input double InpTrailStartATR=1.00;
input double InpTrailDistanceATR=0.45;
input bool InpUsePreviousRangeForStop=false;
input double InpPreviousRangeStopMultiplier=1.00;
input double InpMinimumStopPrice=0.25;
input double InpMaximumStopPrice=3.00;

input group "Signal quality"
input double InpMinimumPreviousRangeATR=0.00;
input int InpVolumeAverageBars=20;
input double InpMinimumVolumeRatio=0.00;
input double InpMaximumSpreadPrice=0.50;
input bool InpUseSessionFilter=false;
input int InpSessionStartHour=12;
input int InpSessionEndHour=18;

input group "Order lifecycle"
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input bool InpUseVirtualOCO=true;
input bool InpUsePreviousBarTriggers=true;
input int InpMaximumHoldingMinutes=180;
input bool InpReplacePendingEachNewBar=true;
input int InpMaximumDeviationPoints=50;
input int InpCooldownAfterWinSeconds=60;
input int InpCooldownAfterLossSeconds=300;
input int InpMaximumTradesPerDay=12;
input double InpMaximumDailyLossMoney=3.00;
input double InpBrokerSafetyBufferPrice=0.10;
input double InpMinimumTrailStepPrice=0.10;

input group "Dynamic lot sizing"
input double InpBaseLot=0.04;
input double InpReferenceBalance=10000.0;
input bool InpScaleLotWithEquity=true;
input double InpMinimumConfiguredLot=0.01;
input double InpMaximumConfiguredLot=1.00;

input group "Identity"
input long InpMagic=864010;

CTrade g_oco_trade;
int g_oco_atr=INVALID_HANDLE;
datetime g_oco_last_bar=0;
datetime g_oco_last_attempt=0;
datetime g_oco_last_diagnostic=0;
datetime g_oco_last_exit=0;
datetime g_oco_day_start=0;
datetime g_oco_last_modify=0;
double g_oco_last_exit_profit=0.0;
double g_oco_daily_profit=0.0;
double g_oco_daily_start_balance=0.0;
int g_oco_daily_trades=0;
bool g_oco_virtual_armed=false;
double g_oco_virtual_buy_trigger=0.0;
double g_oco_virtual_sell_trigger=0.0;
double g_oco_virtual_stop_distance=0.0;
string g_oco_last_status="Starting";

datetime OCO_StartOfDay(const datetime value)
{
   MqlDateTime parts;
   TimeToStruct(value,parts);
   parts.hour=0;
   parts.min=0;
   parts.sec=0;
   return StructToTime(parts);
}

void OCO_RefreshDailyState()
{
   datetime now=TimeCurrent();
   datetime day_start=OCO_StartOfDay(now);
   double profit=0.0;
   int trades=0;
   datetime last_exit=0;
   double last_exit_profit=0.0;
   if(HistorySelect(day_start,now))
   {
      int total=HistoryDealsTotal();
      for(int index=0;index<total;index++)
      {
         ulong deal=HistoryDealGetTicket(index);
         if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
            HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
         ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
         if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL) continue;
         double deal_profit=HistoryDealGetDouble(deal,DEAL_PROFIT)+
                            HistoryDealGetDouble(deal,DEAL_SWAP)+
                            HistoryDealGetDouble(deal,DEAL_COMMISSION)+
                            HistoryDealGetDouble(deal,DEAL_FEE);
         profit+=deal_profit;
         ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
         if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
         {
            trades++;
            datetime deal_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
            if(deal_time>=last_exit)
            {
               last_exit=deal_time;
               last_exit_profit=deal_profit;
            }
         }
      }
   }
   g_oco_day_start=day_start;
   g_oco_daily_profit=profit;
   g_oco_daily_trades=trades;
   g_oco_daily_start_balance=MathMax(0.01,AccountInfoDouble(ACCOUNT_BALANCE)-profit);
   if(last_exit>0)
   {
      g_oco_last_exit=last_exit;
      g_oco_last_exit_profit=last_exit_profit;
   }
}

bool OCO_RiskGate(string &reason)
{
   datetime now=TimeCurrent();
   if(g_oco_day_start!=OCO_StartOfDay(now)) OCO_RefreshDailyState();
   if(InpMaximumTradesPerDay>0 && g_oco_daily_trades>=InpMaximumTradesPerDay)
   {
      reason="PAUSED: daily trade limit reached ("+IntegerToString(g_oco_daily_trades)+").";
      return false;
   }
   if(InpMaximumDailyLossMoney>0.0 && g_oco_daily_profit<=-InpMaximumDailyLossMoney)
   {
      reason="PAUSED: daily loss guard reached ("+DoubleToString(g_oco_daily_profit,2)+" USD).";
      return false;
   }
   int cooldown=(g_oco_last_exit_profit<0.0 ? InpCooldownAfterLossSeconds : InpCooldownAfterWinSeconds);
   if(g_oco_last_exit>0 && cooldown>0 && now-g_oco_last_exit<cooldown)
   {
      reason="COOLDOWN: "+IntegerToString(cooldown-(int)(now-g_oco_last_exit))+" seconds remaining.";
      return false;
   }
   reason="";
   return true;
}

void OCO_Status(const string message,const bool force_log=false)
{
   bool changed=(message!=g_oco_last_status);
   g_oco_last_status=message;
   Comment("HIGH FREQUENCY OCO\n",message,
           "\nMode: ",(InpUseVirtualOCO ? "virtual one-shot" : "server pending pair"),
           "\nPending orders: ",OCO_CountPending(),
           " | Daily trades: ",g_oco_daily_trades,
           " | Daily P/L: ",DoubleToString(g_oco_daily_profit,2)," USD",
           "\nBase lot / current lot: ",DoubleToString(InpBaseLot,2)," / ",DoubleToString(OCO_CurrentLot(),2));
   datetime now=TimeCurrent();
   if(force_log || changed || now-g_oco_last_diagnostic>=60)
   {
      Print("OCO STATUS: ",message);
      g_oco_last_diagnostic=now;
   }
}

bool OCO_TradingPermissionsOK()
{
   // MT5 Strategy Tester is intentionally independent of the terminal's
   // live Algo Trading toolbar switch.
   if(MQLInfoInteger(MQL_TESTER)) return true;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      OCO_Status("BLOCKED: MT5 Algo Trading is OFF. Turn the toolbar Algo Trading button ON.");
      return false;
   }
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      OCO_Status("BLOCKED: Allow Algo Trading is disabled for this EA/chart.");
      return false;
   }
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) || !AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
   {
      OCO_Status("BLOCKED: this broker account does not currently permit EA trading.");
      return false;
   }
   return true;
}

double OCO_NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double OCO_NormalizeLot(const double requested)
{
   double minimum=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),InpMinimumConfiguredLot);
   double maximum=MathMin(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),InpMaximumConfiguredLot);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || maximum<minimum) return 0.0;
   double lots=MathFloor(MathMin(requested,maximum)/step+1e-9)*step;
   if(lots<minimum) lots=minimum;
   return NormalizeDouble(lots,8);
}

double OCO_CurrentLot()
{
   double requested=InpBaseLot;
   if(InpScaleLotWithEquity && InpReferenceBalance>0.0)
      requested*=AccountInfoDouble(ACCOUNT_EQUITY)/InpReferenceBalance;
   return OCO_NormalizeLot(requested);
}

bool OCO_ReadATR(const int shift,double &atr)
{
   double values[];
   if(g_oco_atr==INVALID_HANDLE || CopyBuffer(g_oco_atr,0,shift,1,values)!=1) return false;
   atr=values[0];
   return atr>0.0;
}

bool OCO_IsSessionOpen(const datetime time)
{
   if(!InpUseSessionFilter) return true;
   MqlDateTime parts;
   TimeToStruct(time,parts);
   if(InpSessionStartHour==InpSessionEndHour) return true;
   if(InpSessionStartHour<InpSessionEndHour)
      return parts.hour>=InpSessionStartHour && parts.hour<InpSessionEndHour;
   return parts.hour>=InpSessionStartHour || parts.hour<InpSessionEndHour;
}

bool OCO_HasOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ticket=PositionGetTicket(index);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   ticket=0;
   return false;
}

bool OCO_IsOurPending()
{
   if(OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_MAGIC)!=InpMagic) return false;
   ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
   return type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_SELL_STOP;
}

int OCO_CountPending()
{
   int count=0;
   for(int index=OrdersTotal()-1;index>=0;index--)
   {
      if(OrderGetTicket(index)>0 && OCO_IsOurPending()) count++;
   }
   return count;
}

void OCO_DeletePending()
{
   g_oco_trade.SetExpertMagicNumber((ulong)InpMagic);
   for(int index=OrdersTotal()-1;index>=0;index--)
   {
      ulong ticket=OrderGetTicket(index);
      if(ticket>0 && OCO_IsOurPending() && !g_oco_trade.OrderDelete(ticket))
         Print("OCO pending deletion failed: ",g_oco_trade.ResultRetcodeDescription());
   }
}

double OCO_AveragePriorVolume(MqlRates &rates[],const int start,const int count)
{
   double total=0.0;
   for(int index=start;index<start+count;index++) total+=(double)rates[index].tick_volume;
   return count>0 ? total/count : 0.0;
}

bool OCO_SignalPasses(const double atr,MqlRates &previous)
{
   int required=MathMax(InpVolumeAverageBars+3,4);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M1,0,required,rates)!=required) return false;
   previous=rates[1];
   double range=previous.high-previous.low;
   if(InpMinimumPreviousRangeATR>0.0 && range<InpMinimumPreviousRangeATR*atr) return false;
   if(InpMinimumVolumeRatio>0.0)
   {
      double average=OCO_AveragePriorVolume(rates,2,InpVolumeAverageBars);
      if(average>0.0 && (double)previous.tick_volume<average*InpMinimumVolumeRatio) return false;
   }
   return true;
}

void OCO_Distances(const double atr,const double previous_range,
                   double &offset,double &stop,double &trail_start,double &trail_distance)
{
   offset=InpUseATRDistances ? InpEntryOffsetATR*atr : InpEntryOffsetPrice;
   stop=InpUseATRDistances ? InpStopDistanceATR*atr : InpStopDistancePrice;
   trail_start=InpUseATRDistances ? InpTrailStartATR*atr : InpTrailStartPrice;
   trail_distance=InpUseATRDistances ? InpTrailDistanceATR*atr : InpTrailDistancePrice;
   if(InpUsePreviousRangeForStop) stop=previous_range*InpPreviousRangeStopMultiplier;
   stop=MathMax(InpMinimumStopPrice,MathMin(InpMaximumStopPrice,stop));
}

bool OCO_PlaceCycle()
{
   if(!OCO_TradingPermissionsOK()) return false;
   string risk_reason="";
   if(!OCO_RiskGate(risk_reason))
   {
      g_oco_virtual_armed=false;
      if(OCO_CountPending()>0) OCO_DeletePending();
      OCO_Status(risk_reason);
      return false;
   }
   if(!OCO_IsSessionOpen(TimeCurrent()))
   {
      OCO_Status("WAITING: outside the configured session.");
      return false;
   }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
   {
      OCO_Status("WAITING: no live quote is available for "+_Symbol+".");
      return false;
   }
   if(InpMaximumSpreadPrice>0.0 && tick.ask-tick.bid>InpMaximumSpreadPrice)
   {
      OCO_Status("WAITING: spread "+DoubleToString(tick.ask-tick.bid,2)+
                 " exceeds the configured maximum "+DoubleToString(InpMaximumSpreadPrice,2)+".");
      return false;
   }
   double atr=0.0;
   if(!OCO_ReadATR(1,atr))
   {
      OCO_Status("WAITING: XAUUSD M1 history/ATR is not ready yet.");
      return false;
   }
   MqlRates previous;
   if(!OCO_SignalPasses(atr,previous))
   {
      OCO_Status("WAITING: M1 history or the optional signal-quality filter is not ready.");
      return false;
   }

   double offset=0.0,stop_distance=0.0,trail_start=0.0,trail_distance=0.0;
   OCO_Distances(atr,previous.high-previous.low,offset,stop_distance,trail_start,trail_distance);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   broker_gap=MathMax(broker_gap,point);
   offset=MathMax(offset,broker_gap);
   stop_distance=MathMax(stop_distance,broker_gap);

   double buy_entry=0.0;
   double sell_entry=0.0;
   if(InpUsePreviousBarTriggers)
   {
      buy_entry=MathMax(previous.high+offset,tick.ask+broker_gap);
      sell_entry=MathMin(previous.low-offset,tick.bid-broker_gap);
   }
   else
   {
      buy_entry=tick.ask+offset;
      sell_entry=tick.bid-offset;
   }
   buy_entry=OCO_NormalizePrice(buy_entry);
   sell_entry=OCO_NormalizePrice(sell_entry);
   double buy_sl=OCO_NormalizePrice(buy_entry-stop_distance);
   double sell_sl=OCO_NormalizePrice(sell_entry+stop_distance);
   double lots=OCO_CurrentLot();
   if(lots<=0.0)
   {
      OCO_Status("BLOCKED: broker lot limits do not allow the configured volume.");
      return false;
   }

   if(InpUseVirtualOCO)
   {
      g_oco_virtual_buy_trigger=buy_entry;
      g_oco_virtual_sell_trigger=sell_entry;
      g_oco_virtual_stop_distance=stop_distance;
      g_oco_virtual_armed=true;
      OCO_Status("ARMED: virtual OCO at "+DoubleToString(buy_entry,_Digits)+
                 " / "+DoubleToString(sell_entry,_Digits)+". Only one market order can be sent.",true);
      return true;
   }

   g_oco_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_oco_trade.SetTypeFillingBySymbol(_Symbol);
   g_oco_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool buy_ok=true;
   bool sell_ok=true;
   string buy_result="disabled";
   string sell_result="disabled";
   if(InpAllowLong)
   {
      buy_ok=g_oco_trade.BuyStop(lots,buy_entry,_Symbol,buy_sl,0.0,ORDER_TIME_GTC,0,"OCO reel buy");
      buy_result=IntegerToString((int)g_oco_trade.ResultRetcode())+" "+g_oco_trade.ResultRetcodeDescription();
   }
   if(InpAllowShort)
   {
      sell_ok=g_oco_trade.SellStop(lots,sell_entry,_Symbol,sell_sl,0.0,ORDER_TIME_GTC,0,"OCO reel sell");
      sell_result=IntegerToString((int)g_oco_trade.ResultRetcode())+" "+g_oco_trade.ResultRetcodeDescription();
   }
   if((InpAllowLong && !buy_ok) || (InpAllowShort && !sell_ok))
   {
      OCO_Status("BLOCKED: pending order rejected. Buy: "+buy_result+" | Sell: "+sell_result,true);
      OCO_DeletePending();
      return false;
   }
   OCO_Status("ACTIVE: OCO pair placed at "+DoubleToString(buy_entry,_Digits)+
              " / "+DoubleToString(sell_entry,_Digits)+" using "+DoubleToString(lots,2)+" lot.",true);
   return buy_ok || sell_ok;
}

bool OCO_TriggerVirtualOrder()
{
   if(!InpUseVirtualOCO || !g_oco_virtual_armed) return false;
   string risk_reason="";
   if(!OCO_RiskGate(risk_reason))
   {
      g_oco_virtual_armed=false;
      OCO_Status(risk_reason);
      return false;
   }
   if(!OCO_IsSessionOpen(TimeCurrent()))
   {
      g_oco_virtual_armed=false;
      OCO_Status("WAITING: outside the configured session.");
      return false;
   }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   double spread=tick.ask-tick.bid;
   if(InpMaximumSpreadPrice>0.0 && spread>InpMaximumSpreadPrice)
   {
      OCO_Status("WAITING: spread "+DoubleToString(spread,2)+" exceeds the configured maximum.");
      return false;
   }
   bool trigger_buy=InpAllowLong && tick.ask>=g_oco_virtual_buy_trigger;
   bool trigger_sell=InpAllowShort && tick.bid<=g_oco_virtual_sell_trigger;
   if(!trigger_buy && !trigger_sell) return false;

   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   broker_gap=MathMax(broker_gap+InpBrokerSafetyBufferPrice,point);
   double lots=OCO_CurrentLot();
   if(lots<=0.0) return false;
   g_oco_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_oco_trade.SetTypeFillingBySymbol(_Symbol);
   g_oco_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=false;
   if(trigger_buy)
   {
      double sl=OCO_NormalizePrice(MathMin(tick.ask-g_oco_virtual_stop_distance,tick.bid-broker_gap));
      sent=g_oco_trade.Buy(lots,_Symbol,0.0,sl,0.0,"OCO virtual buy");
   }
   else if(trigger_sell)
   {
      double sl=OCO_NormalizePrice(MathMax(tick.bid+g_oco_virtual_stop_distance,tick.ask+broker_gap));
      sent=g_oco_trade.Sell(lots,_Symbol,0.0,sl,0.0,"OCO virtual sell");
   }
   if(sent)
   {
      g_oco_virtual_armed=false;
      g_oco_last_attempt=TimeCurrent();
      OCO_Status("ENTRY SENT: virtual OCO triggered one protected market order.",true);
      return true;
   }
   OCO_Status("ENTRY REJECTED: "+g_oco_trade.ResultRetcodeDescription(),true);
   g_oco_last_attempt=TimeCurrent();
   return false;
}

void OCO_ManagePosition()
{
   ulong ticket=0;
   if(!OCO_HasOurPosition(ticket)) return;
   if(OCO_CountPending()>0) OCO_DeletePending();
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(InpMaximumHoldingMinutes>0 && TimeCurrent()-opened>=InpMaximumHoldingMinutes*60)
   {
      g_oco_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_oco_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      g_oco_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double atr=0.0;
   if(!OCO_ReadATR(0,atr)) return;
   MqlRates previous;
   if(!OCO_SignalPasses(atr,previous))
   {
      previous.high=0.0;
      previous.low=0.0;
   }
   double offset=0.0,stop_distance=0.0,trail_start=0.0,trail_distance=0.0;
   OCO_Distances(atr,MathMax(0.0,previous.high-previous.low),offset,stop_distance,trail_start,trail_distance);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   broker_gap=MathMax(broker_gap+InpBrokerSafetyBufferPrice,point);

   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double old_sl=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double new_sl=old_sl;
   if(type==POSITION_TYPE_BUY && tick.bid-open>=trail_start)
   {
      double candidate=OCO_NormalizePrice(tick.bid-MathMax(trail_distance,broker_gap));
      if(candidate>open && (old_sl<=0.0 || candidate>old_sl+MathMax(point,InpMinimumTrailStepPrice))) new_sl=candidate;
   }
   else if(type==POSITION_TYPE_SELL && open-tick.ask>=trail_start)
   {
      double candidate=OCO_NormalizePrice(tick.ask+MathMax(trail_distance,broker_gap));
      if(candidate<open && (old_sl<=0.0 || candidate<old_sl-MathMax(point,InpMinimumTrailStepPrice))) new_sl=candidate;
   }
   if(new_sl!=old_sl && TimeCurrent()-g_oco_last_modify>=1)
   {
      g_oco_trade.SetExpertMagicNumber((ulong)InpMagic);
      if(g_oco_trade.PositionModify(ticket,new_sl,target)) g_oco_last_modify=TimeCurrent();
   }
}

int OnInit()
{
   if(InpATRPeriod<2 || InpEntryOffsetPrice<=0.0 || InpStopDistancePrice<=0.0 ||
      InpTrailStartPrice<=0.0 || InpTrailDistancePrice<=0.0 || InpEntryOffsetATR<=0.0 ||
      InpStopDistanceATR<=0.0 || InpTrailStartATR<=0.0 || InpTrailDistanceATR<=0.0 ||
      InpMinimumStopPrice<=0.0 || InpMaximumStopPrice<InpMinimumStopPrice ||
      (!InpAllowLong && !InpAllowShort) || InpBaseLot<=0.0 || InpReferenceBalance<=0.0 ||
      InpMaximumConfiguredLot<InpMinimumConfiguredLot || InpCooldownAfterWinSeconds<0 ||
      InpCooldownAfterLossSeconds<0 || InpMaximumTradesPerDay<0 ||
      InpMaximumDailyLossMoney<0.0 || InpBrokerSafetyBufferPrice<0.0 ||
      InpMinimumTrailStepPrice<0.0 || InpMagic<=0) return INIT_PARAMETERS_INCORRECT;
   // The strategy is M1-specific. Force the live chart to M1 even when MT5
   // restores a stale cached timeframe for the named profile.
   if(!MQLInfoInteger(MQL_TESTER) && _Period!=PERIOD_M1)
   {
      if(!ChartSetSymbolPeriod(0,_Symbol,PERIOD_M1))
         Print("OCO chart timeframe switch to M1 failed. Trading logic still reads PERIOD_M1 directly.");
   }
   g_oco_atr=iATR(_Symbol,PERIOD_M1,InpATRPeriod);
   if(g_oco_atr==INVALID_HANDLE) return INIT_FAILED;
   g_oco_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_oco_trade.SetTypeFillingBySymbol(_Symbol);
   g_oco_last_bar=0;
   g_oco_virtual_armed=false;
   OCO_RefreshDailyState();
   if(InpUseVirtualOCO && OCO_CountPending()>0) OCO_DeletePending();
   EventSetTimer(1);
   OCO_Status("STARTING: waiting for quote and M1 history.",true);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
   if(g_oco_atr!=INVALID_HANDLE) IndicatorRelease(g_oco_atr);
}

void OCO_Run()
{
   OCO_ManagePosition();
   datetime bar=iTime(_Symbol,PERIOD_M1,0);
   bool new_bar=(bar>0 && bar!=g_oco_last_bar);
   if(new_bar) g_oco_last_bar=bar;
   ulong ticket=0;
   if(OCO_HasOurPosition(ticket))
   {
      OCO_Status("ACTIVE: position open; sibling pending order removed and trailing management running.");
      return;
   }
   string risk_reason="";
   if(!OCO_RiskGate(risk_reason))
   {
      g_oco_virtual_armed=false;
      if(OCO_CountPending()>0) OCO_DeletePending();
      OCO_Status(risk_reason);
      return;
   }
   if(new_bar && InpReplacePendingEachNewBar)
   {
      OCO_DeletePending();
      g_oco_virtual_armed=false;
   }
   if(InpUseVirtualOCO && g_oco_virtual_armed)
   {
      if(!OCO_TriggerVirtualOrder())
         OCO_Status("ARMED: waiting for one virtual breakout at "+
                    DoubleToString(g_oco_virtual_buy_trigger,_Digits)+" / "+
                    DoubleToString(g_oco_virtual_sell_trigger,_Digits)+".");
      return;
   }
   int pending=OCO_CountPending();
   if(pending>0)
   {
      OCO_Status("ACTIVE: "+IntegerToString(pending)+" OCO pending orders waiting for price.");
      return;
   }
   datetime now=TimeCurrent();
   if(now-g_oco_last_attempt<5) return;
   g_oco_last_attempt=now;
   OCO_PlaceCycle();
}

void OnTick(){ OCO_Run(); }
void OnTimer(){ OCO_Run(); }

void OnTradeTransaction(const MqlTradeTransaction &transaction,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0) return;
   if(!HistoryDealSelect(transaction.deal)) return;
   if(HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol ||
      HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=InpMagic) return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(transaction.deal,DEAL_ENTRY);
   if(entry==DEAL_ENTRY_IN)
   {
      g_oco_virtual_armed=false;
      OCO_DeletePending();
      return;
   }
   if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
   {
      g_oco_last_exit=(datetime)HistoryDealGetInteger(transaction.deal,DEAL_TIME);
      g_oco_last_exit_profit=HistoryDealGetDouble(transaction.deal,DEAL_PROFIT)+
                             HistoryDealGetDouble(transaction.deal,DEAL_SWAP)+
                             HistoryDealGetDouble(transaction.deal,DEAL_COMMISSION)+
                             HistoryDealGetDouble(transaction.deal,DEAL_FEE);
      OCO_RefreshDailyState();
      g_oco_virtual_armed=false;
      Print("OCO EXIT: net=",DoubleToString(g_oco_last_exit_profit,2),
            " daily=",DoubleToString(g_oco_daily_profit,2),
            " trades=",g_oco_daily_trades);
   }
}
