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
input int InpMaximumHoldingMinutes=180;
input bool InpReplacePendingEachNewBar=true;
input int InpMaximumDeviationPoints=50;

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
string g_oco_last_status="Starting";

void OCO_Status(const string message,const bool force_log=false)
{
   bool changed=(message!=g_oco_last_status);
   g_oco_last_status=message;
   Comment("HIGH FREQUENCY OCO\n",message,
           "\nPending orders: ",OCO_CountPending(),
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

#ifdef OCO_CURRENT_PRICE
   double buy_entry=tick.ask+offset;
   double sell_entry=tick.bid-offset;
#else
   double buy_entry=MathMax(previous.high+offset,tick.ask+broker_gap);
   double sell_entry=MathMin(previous.low-offset,tick.bid-broker_gap);
#endif
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
   broker_gap=MathMax(broker_gap,point);

   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double old_sl=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double new_sl=old_sl;
   if(type==POSITION_TYPE_BUY && tick.bid-open>=trail_start)
   {
      double candidate=OCO_NormalizePrice(tick.bid-MathMax(trail_distance,broker_gap));
      if(candidate>open && (old_sl<=0.0 || candidate>old_sl+point)) new_sl=candidate;
   }
   else if(type==POSITION_TYPE_SELL && open-tick.ask>=trail_start)
   {
      double candidate=OCO_NormalizePrice(tick.ask+MathMax(trail_distance,broker_gap));
      if(candidate<open && (old_sl<=0.0 || candidate<old_sl-point)) new_sl=candidate;
   }
   if(new_sl!=old_sl)
   {
      g_oco_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_oco_trade.PositionModify(ticket,new_sl,target);
   }
}

int OnInit()
{
   if(InpATRPeriod<2 || InpEntryOffsetPrice<=0.0 || InpStopDistancePrice<=0.0 ||
      InpTrailStartPrice<=0.0 || InpTrailDistancePrice<=0.0 || InpEntryOffsetATR<=0.0 ||
      InpStopDistanceATR<=0.0 || InpTrailStartATR<=0.0 || InpTrailDistanceATR<=0.0 ||
      InpMinimumStopPrice<=0.0 || InpMaximumStopPrice<InpMinimumStopPrice ||
      (!InpAllowLong && !InpAllowShort) || InpBaseLot<=0.0 || InpReferenceBalance<=0.0 ||
      InpMaximumConfiguredLot<InpMinimumConfiguredLot || InpMagic<=0) return INIT_PARAMETERS_INCORRECT;
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
   if(new_bar && InpReplacePendingEachNewBar) OCO_DeletePending();
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
      HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=InpMagic ||
      HistoryDealGetInteger(transaction.deal,DEAL_ENTRY)!=DEAL_ENTRY_IN) return;
   OCO_DeletePending();
}
