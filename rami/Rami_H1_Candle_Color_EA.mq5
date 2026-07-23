//+------------------------------------------------------------------+
//| Rami_H1_Candle_Color_EA.mq5                                      |
//| Opens buys after a bullish H1 candle and sells after a bearish H1 |
//| candle. TP/SL are expressed in account currency.                 |
//+------------------------------------------------------------------+
#property strict

#include <Trade/Trade.mqh>

input ENUM_TIMEFRAMES InpSignalTimeframe = PERIOD_H1;
input double          InpLots = 0.01;
input double          InpTakeProfitMoney = 100.0;
input double          InpStopLossMoney = 1000.0;
input ulong           InpMagicNumber = 2026072301;
input int             InpDeviationPoints = 30;
input int             InpMaxWinningTradesPerDay = 1;
input bool            InpOnePositionPerSymbol = true;
input bool            InpCloseOppositeOnNewSignal = true;
input bool            InpAllowBuy = true;
input bool            InpAllowSell = true;

CTrade trade;
datetime last_bar_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);
   Print("Rami H1 Candle Color EA initialized on ", _Symbol,
         ". Signal timeframe=", EnumToString(InpSignalTimeframe),
         ", lots=", DoubleToString(InpLots, 2),
         ", TP money=", DoubleToString(InpTakeProfitMoney, 2),
         ", SL money=", DoubleToString(InpStopLossMoney, 2));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert tick                                                       |
//+------------------------------------------------------------------+
void OnTick()
{
   datetime current_bar_time = iTime(_Symbol, InpSignalTimeframe, 0);
   if(current_bar_time <= 0)
      return;

   if(current_bar_time == last_bar_time)
      return;

   last_bar_time = current_bar_time;
   ProcessClosedCandleSignal();
}

//+------------------------------------------------------------------+
//| Process the latest closed candle                                  |
//+------------------------------------------------------------------+
void ProcessClosedCandleSignal()
{
   double candle_open = iOpen(_Symbol, InpSignalTimeframe, 1);
   double candle_close = iClose(_Symbol, InpSignalTimeframe, 1);

   if(candle_open <= 0 || candle_close <= 0)
      return;

   if(candle_close > candle_open && InpAllowBuy)
      OpenSignalTrade(ORDER_TYPE_BUY);
   else if(candle_close < candle_open && InpAllowSell)
      OpenSignalTrade(ORDER_TYPE_SELL);
   else
      Print("No trade: closed candle was neutral or direction disabled.");
}

//+------------------------------------------------------------------+
//| Open trade for direction                                          |
//+------------------------------------------------------------------+
void OpenSignalTrade(ENUM_ORDER_TYPE order_type)
{
   if(DailyWinLimitReached())
      return;

   if(InpOnePositionPerSymbol && HasPosition(order_type))
   {
      Print("Skipped: already have same-direction position for ", _Symbol);
      return;
   }

   ENUM_ORDER_TYPE opposite = (order_type == ORDER_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
   if(InpCloseOppositeOnNewSignal)
      ClosePositions(opposite);
   else if(InpOnePositionPerSymbol && HasPosition(opposite))
   {
      Print("Skipped: opposite position exists and close-opposite is disabled.");
      return;
   }

   double lots = NormalizeLot(InpLots);
   if(lots <= 0)
   {
      Print("Invalid lot after normalization: ", DoubleToString(lots, 2));
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
   {
      Print("Failed to read tick for ", _Symbol);
      return;
   }

   double entry = (order_type == ORDER_TYPE_BUY ? tick.ask : tick.bid);
   double tp_distance = MoneyToPriceDistance(_Symbol, lots, InpTakeProfitMoney);
   double sl_distance = MoneyToPriceDistance(_Symbol, lots, InpStopLossMoney);

   if(tp_distance <= 0 || sl_distance <= 0)
   {
      Print("Failed to calculate money-based TP/SL distances.");
      return;
   }

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double sl = 0.0;
   double tp = 0.0;

   if(order_type == ORDER_TYPE_BUY)
   {
      sl = NormalizeDouble(entry - sl_distance, digits);
      tp = NormalizeDouble(entry + tp_distance, digits);
   }
   else
   {
      sl = NormalizeDouble(entry + sl_distance, digits);
      tp = NormalizeDouble(entry - tp_distance, digits);
   }

   if(!StopsAreValid(order_type, entry, sl, tp))
      return;

   string comment = "Rami H1 candle";
   bool ok = false;
   if(order_type == ORDER_TYPE_BUY)
      ok = trade.Buy(lots, _Symbol, 0.0, sl, tp, comment);
   else
      ok = trade.Sell(lots, _Symbol, 0.0, sl, tp, comment);

   if(ok)
   {
      Print("Opened ", EnumToString(order_type), " ", _Symbol,
            " lots=", DoubleToString(lots, 2),
            " entry~", DoubleToString(entry, digits),
            " SL=", DoubleToString(sl, digits),
            " TP=", DoubleToString(tp, digits));
   }
   else
   {
      Print("Order failed. Retcode=", trade.ResultRetcode(),
            " message=", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Daily win limit                                                   |
//+------------------------------------------------------------------+
bool DailyWinLimitReached()
{
   if(InpMaxWinningTradesPerDay <= 0)
      return false;

   int wins = CountTodayWinningDeals();
   if(wins >= InpMaxWinningTradesPerDay)
   {
      Print("Skipped: daily winning trade limit reached for ", _Symbol,
            ". wins=", wins,
            " max=", InpMaxWinningTradesPerDay);
      return true;
   }
   return false;
}

int CountTodayWinningDeals()
{
   datetime day_start = StartOfToday();
   datetime now = TimeCurrent();

   if(!HistorySelect(day_start, now))
      return 0;

   int wins = 0;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong deal_ticket = HistoryDealGetTicket(i);
      if(deal_ticket == 0)
         continue;

      string symbol = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
      if(symbol != _Symbol)
         continue;

      long magic = HistoryDealGetInteger(deal_ticket, DEAL_MAGIC);
      if((ulong)magic != InpMagicNumber)
         continue;

      long entry_type = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
      if(entry_type != DEAL_ENTRY_OUT && entry_type != DEAL_ENTRY_INOUT)
         continue;

      double net_profit =
         HistoryDealGetDouble(deal_ticket, DEAL_PROFIT) +
         HistoryDealGetDouble(deal_ticket, DEAL_SWAP) +
         HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);

      if(net_profit > 0.0)
         wins++;
   }

   return wins;
}

datetime StartOfToday()
{
   MqlDateTime parts;
   TimeToStruct(TimeCurrent(), parts);
   parts.hour = 0;
   parts.min = 0;
   parts.sec = 0;
   return StructToTime(parts);
}

//+------------------------------------------------------------------+
//| Convert account-currency target into price distance               |
//+------------------------------------------------------------------+
double MoneyToPriceDistance(string symbol, double lots, double money)
{
   if(money <= 0 || lots <= 0)
      return 0.0;

   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0 || tick_value <= 0)
      return 0.0;

   return (money / (tick_value * lots)) * tick_size;
}

//+------------------------------------------------------------------+
//| Normalize lot to broker min/max/step                              |
//+------------------------------------------------------------------+
double NormalizeLot(double lot)
{
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0)
      step = 0.01;

   lot = MathMax(min_lot, MathMin(max_lot, lot));
   lot = MathFloor(lot / step) * step;
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| Check broker stop-distance rules                                  |
//+------------------------------------------------------------------+
bool StopsAreValid(ENUM_ORDER_TYPE order_type, double entry, double sl, double tp)
{
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int stops_level = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double min_distance = stops_level * point;

   if(min_distance <= 0)
      return true;

   if(order_type == ORDER_TYPE_BUY)
   {
      if(entry - sl < min_distance || tp - entry < min_distance)
      {
         Print("Invalid BUY stops: broker minimum distance is ", DoubleToString(min_distance, _Digits));
         return false;
      }
   }
   else
   {
      if(sl - entry < min_distance || entry - tp < min_distance)
      {
         Print("Invalid SELL stops: broker minimum distance is ", DoubleToString(min_distance, _Digits));
         return false;
      }
   }

   return true;
}

//+------------------------------------------------------------------+
//| Position helpers                                                  |
//+------------------------------------------------------------------+
bool HasPosition(ENUM_ORDER_TYPE order_type)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      if(order_type == ORDER_TYPE_BUY && type == POSITION_TYPE_BUY)
         return true;
      if(order_type == ORDER_TYPE_SELL && type == POSITION_TYPE_SELL)
         return true;
   }
   return false;
}

void ClosePositions(ENUM_ORDER_TYPE order_type)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      bool should_close =
         (order_type == ORDER_TYPE_BUY && type == POSITION_TYPE_BUY) ||
         (order_type == ORDER_TYPE_SELL && type == POSITION_TYPE_SELL);

      if(should_close)
      {
         if(trade.PositionClose(ticket))
            Print("Closed opposite position ticket=", ticket);
         else
            Print("Failed closing opposite ticket=", ticket,
                  " retcode=", trade.ResultRetcode(),
                  " message=", trade.ResultRetcodeDescription());
      }
   }
}
