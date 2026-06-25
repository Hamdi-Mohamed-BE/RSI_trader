//+------------------------------------------------------------------+
//| XAU Previous Day Edge Breakout EA                                |
//| Strategy: previous-day high/low pending breakout orders for gold  |
//| Author: ChatGPT                                                  |
//| Notes: High-lot breakout trading is extremely risky. Backtest and |
//|        forward-test on demo before using live funds.              |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Places Buy Stop above previous day high and Sell Stop below previous day low."
#property description "Uses OCO, fast break-even, fast trailing stop, optional quick profit close."

#include <Trade/Trade.mqh>

CTrade trade;

enum ENUM_LOT_MODE
{
   LOT_FIXED       = 0,
   LOT_RISK_PERCENT = 1
};

//======================== MAIN SETTINGS ============================
input string        InpTradeSymbol              = "";       // Empty = chart symbol
input bool          InpGoldOnly                 = true;     // Only allow XAU/GOLD symbols
input long          InpMagicNumber              = 27062401; // Magic number
input bool          InpTradeAllSessions         = true;     // TRUE = trade Asia/London/NY/all day
input int           InpStartHourServer          = 0;        // Used only if TradeAllSessions=false
input int           InpEndHourServer            = 23;       // Used only if TradeAllSessions=false
input int           InpMaxSpreadPoints          = 80;       // Max spread in points

//======================== ORDER SETTINGS ============================
input ENUM_LOT_MODE InpLotMode                  = LOT_FIXED;
input double        InpFixedLot                 = 0.10;     // Aggressive users can raise this manually
input double        InpRiskPercent              = 1.00;     // Used if LotMode = LOT_RISK_PERCENT
input double        InpMaxLotCap                = 2.00;     // Hard cap so lot cannot exceed this input
input int           InpEntryOffsetPoints        = 50;       // BuyStop = prev high + offset, SellStop = prev low - offset
input int           InpStopLossPoints           = 300;      // Protective SL in points
input int           InpTakeProfitPoints         = 0;        // 0 = no fixed TP, let trailing manage
input bool          InpUsePendingExpiration     = false;    // Some brokers reject expiration; GTC is safer
input int           InpPendingExpiryHours       = 20;       // If expiration enabled
input bool          InpRebuildMissingOrders     = true;     // Re-place missing daily orders if no position
input bool          InpCancelOppositeOnFill     = true;     // OCO behavior
input int           InpMaxFilledTradesPerDay    = 2;        // Max entries/day for this EA/symbol

//======================== FAST WIN MANAGEMENT =======================
input bool          InpUseQuickProfitClose      = false;    // TRUE = close fast when profit reaches points
input int           InpQuickProfitClosePoints   = 120;      // Close position at this profit in points
input bool          InpUseBreakEven             = true;
input int           InpBreakEvenTriggerPoints   = 60;       // Move SL to BE quickly after this profit
input int           InpBreakEvenLockPoints      = 10;       // Lock this many points beyond entry
input bool          InpUseFastTrailing          = true;
input int           InpTrailStartPoints         = 80;       // Start trailing early
input int           InpTrailDistancePoints      = 45;       // Tight trailing distance
input int           InpTrailStepPoints          = 5;        // Modify SL each X points improvement

//======================== SAFETY SETTINGS ===========================
input bool          InpUseDailyLossStop         = true;
input double        InpDailyLossStopPercent     = 5.0;      // Disable trading for day if equity drops this %
input bool          InpCloseAllOnDailyStop      = true;
input bool          InpPrintDebug               = true;

//======================== INTERNAL STATE ============================
string   g_symbol = "";
datetime g_currentD1Open = 0;
datetime g_dayStartTime = 0;
double   g_dayStartEquity = 0.0;
double   g_prevHigh = 0.0;
double   g_prevLow = 0.0;
bool     g_tradingDisabledToday = false;

//+------------------------------------------------------------------+
//| Utility                                                          |
//+------------------------------------------------------------------+
void Log(string msg)
{
   if(InpPrintDebug)
      Print("[XAU Edge EA] ", msg);
}

bool ContainsGoldName(const string sym)
{
   string s = sym;
   StringToUpper(s);
   return (StringFind(s, "XAU") >= 0 || StringFind(s, "GOLD") >= 0);
}

int VolumeDigitsFromStep(double step)
{
   int digits = 0;
   while(step > 0.0 && step < 1.0 && digits < 8)
   {
      step *= 10.0;
      digits++;
   }
   return digits;
}

double NormalizeVolumeForSymbol(const string sym, double lots)
{
   double minLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);

   if(step <= 0.0)
      step = 0.01;

   lots = MathMax(minLot, lots);
   lots = MathMin(maxLot, lots);
   lots = MathMin(InpMaxLotCap, lots);

   lots = MathFloor(lots / step) * step;
   lots = MathMax(minLot, lots);

   return NormalizeDouble(lots, VolumeDigitsFromStep(step));
}

double NormalizePriceForSymbol(const string sym, double price)
{
   double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);

   if(tickSize <= 0.0)
      tickSize = SymbolInfoDouble(sym, SYMBOL_POINT);

   price = MathRound(price / tickSize) * tickSize;
   return NormalizeDouble(price, digits);
}

bool GetBidAsk(const string sym, double &bid, double &ask)
{
   MqlTick tick;
   if(!SymbolInfoTick(sym, tick))
      return false;

   bid = tick.bid;
   ask = tick.ask;
   return (bid > 0.0 && ask > 0.0);
}

bool SpreadOK()
{
   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return false;

   double point = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   if(point <= 0.0)
      return false;

   double spreadPoints = (ask - bid) / point;
   return (spreadPoints <= InpMaxSpreadPoints);
}

bool IsTradingTimeAllowed()
{
   if(InpTradeAllSessions)
      return true;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpStartHourServer <= InpEndHourServer)
      return (dt.hour >= InpStartHourServer && dt.hour <= InpEndHourServer);

   // Overnight window, for example 22 -> 3
   return (dt.hour >= InpStartHourServer || dt.hour <= InpEndHourServer);
}

//+------------------------------------------------------------------+
//| Position/order counting                                           |
//+------------------------------------------------------------------+
bool IsOurPositionSelectedByIndex(int index)
{
   ulong ticket = PositionGetTicket(index);
   if(ticket == 0)
      return false;
   if(!PositionSelectByTicket(ticket))
      return false;

   string sym = PositionGetString(POSITION_SYMBOL);
   long magic = PositionGetInteger(POSITION_MAGIC);
   return (sym == g_symbol && magic == InpMagicNumber);
}

int CountOurOpenPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(IsOurPositionSelectedByIndex(i))
         count++;
   }
   return count;
}

int CountOurPendingOrders(const int filterType = -1)
{
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if(!OrderSelect(ticket))
         continue;

      string sym = OrderGetString(ORDER_SYMBOL);
      long magic = OrderGetInteger(ORDER_MAGIC);
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);

      if(sym != g_symbol || magic != InpMagicNumber)
         continue;

      if(type != ORDER_TYPE_BUY_STOP && type != ORDER_TYPE_SELL_STOP)
         continue;

      if(filterType >= 0 && (int)type != filterType)
         continue;

      count++;
   }
   return count;
}

int CountTodayEntryDeals()
{
   if(g_dayStartTime <= 0)
      return 0;

   int count = 0;
   if(!HistorySelect(g_dayStartTime, TimeCurrent()))
      return 0;

   int deals = HistoryDealsTotal();
   for(int i = deals - 1; i >= 0; i--)
   {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0)
         continue;

      string sym = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
      long magic = HistoryDealGetInteger(dealTicket, DEAL_MAGIC);
      long entry = HistoryDealGetInteger(dealTicket, DEAL_ENTRY);

      if(sym == g_symbol && magic == InpMagicNumber && entry == DEAL_ENTRY_IN)
         count++;
   }

   return count;
}

//+------------------------------------------------------------------+
//| Cancel orders / close positions                                   |
//+------------------------------------------------------------------+
void CancelOurPendingOrders(const int filterType = -1)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if(!OrderSelect(ticket))
         continue;

      string sym = OrderGetString(ORDER_SYMBOL);
      long magic = OrderGetInteger(ORDER_MAGIC);
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);

      if(sym != g_symbol || magic != InpMagicNumber)
         continue;

      if(type != ORDER_TYPE_BUY_STOP && type != ORDER_TYPE_SELL_STOP)
         continue;

      if(filterType >= 0 && (int)type != filterType)
         continue;

      if(!trade.OrderDelete(ticket))
         Log("Failed to delete pending order #" + (string)ticket + " retcode=" + (string)trade.ResultRetcode());
   }
}

void CloseOurPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;

      string sym = PositionGetString(POSITION_SYMBOL);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(sym != g_symbol || magic != InpMagicNumber)
         continue;

      if(!trade.PositionClose(ticket))
         Log("Failed to close position #" + (string)ticket + " retcode=" + (string)trade.ResultRetcode());
   }
}

//+------------------------------------------------------------------+
//| Previous day levels                                               |
//+------------------------------------------------------------------+
bool RefreshPreviousDayLevels()
{
   datetime d1Open = iTime(g_symbol, PERIOD_D1, 0);
   if(d1Open <= 0)
      return false;

   if(d1Open == g_currentD1Open && g_prevHigh > 0.0 && g_prevLow > 0.0)
      return true;

   double prevHigh = iHigh(g_symbol, PERIOD_D1, 1);
   double prevLow  = iLow(g_symbol, PERIOD_D1, 1);

   if(prevHigh <= 0.0 || prevLow <= 0.0 || prevHigh <= prevLow)
   {
      Log("Invalid previous D1 high/low. Need more D1 history.");
      return false;
   }

   // New broker day: cancel old pending orders and reset daily safety state
   bool isNewDay = (d1Open != g_currentD1Open);
   g_currentD1Open = d1Open;
   g_dayStartTime = d1Open;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_prevHigh = NormalizePriceForSymbol(g_symbol, prevHigh);
   g_prevLow = NormalizePriceForSymbol(g_symbol, prevLow);
   g_tradingDisabledToday = false;

   if(isNewDay)
   {
      CancelOurPendingOrders();
      Log("New D1 levels. PrevHigh=" + DoubleToString(g_prevHigh, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)) +
          " PrevLow=" + DoubleToString(g_prevLow, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)));
   }

   return true;
}

//+------------------------------------------------------------------+
//| Lot calculation                                                   |
//+------------------------------------------------------------------+
double CalculateLotSize()
{
   if(InpLotMode == LOT_FIXED)
      return NormalizeVolumeForSymbol(g_symbol, InpFixedLot);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * InpRiskPercent / 100.0;

   double tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   double point     = SymbolInfoDouble(g_symbol, SYMBOL_POINT);

   if(tickValue <= 0.0 || tickSize <= 0.0 || point <= 0.0 || InpStopLossPoints <= 0)
      return NormalizeVolumeForSymbol(g_symbol, InpFixedLot);

   double slPriceDistance = InpStopLossPoints * point;
   double ticks = slPriceDistance / tickSize;
   double lossPerLot = ticks * tickValue;

   if(lossPerLot <= 0.0)
      return NormalizeVolumeForSymbol(g_symbol, InpFixedLot);

   double lots = riskMoney / lossPerLot;
   return NormalizeVolumeForSymbol(g_symbol, lots);
}

bool HasEnoughMargin(ENUM_ORDER_TYPE orderType, double lots, double price)
{
   double margin = 0.0;
   if(!OrderCalcMargin(orderType, g_symbol, lots, price, margin))
      return true; // Let broker decide if calc not available

   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   return (freeMargin > margin * 1.20);
}

//+------------------------------------------------------------------+
//| Place daily edge pending orders                                   |
//+------------------------------------------------------------------+
void PlaceDailyEdgeOrders()
{
   if(g_tradingDisabledToday)
      return;
   if(!IsTradingTimeAllowed())
      return;
   if(!SpreadOK())
      return;
   if(CountOurOpenPositions() > 0)
      return;
   if(CountTodayEntryDeals() >= InpMaxFilledTradesPerDay)
      return;

   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return;

   double point = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   int stopsLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minStopDistance = MathMax(stopsLevel * point, point);

   double lots = CalculateLotSize();
   if(lots <= 0.0)
      return;

   double buyEntry  = NormalizePriceForSymbol(g_symbol, g_prevHigh + InpEntryOffsetPoints * point);
   double sellEntry = NormalizePriceForSymbol(g_symbol, g_prevLow  - InpEntryOffsetPoints * point);

   double buySL = 0.0, buyTP = 0.0, sellSL = 0.0, sellTP = 0.0;

   if(InpStopLossPoints > 0)
   {
      buySL  = NormalizePriceForSymbol(g_symbol, buyEntry  - InpStopLossPoints * point);
      sellSL = NormalizePriceForSymbol(g_symbol, sellEntry + InpStopLossPoints * point);
   }

   if(InpTakeProfitPoints > 0)
   {
      buyTP  = NormalizePriceForSymbol(g_symbol, buyEntry  + InpTakeProfitPoints * point);
      sellTP = NormalizePriceForSymbol(g_symbol, sellEntry - InpTakeProfitPoints * point);
   }

   ENUM_ORDER_TYPE_TIME timeType = ORDER_TIME_GTC;
   datetime expiration = 0;
   if(InpUsePendingExpiration)
   {
      timeType = ORDER_TIME_SPECIFIED;
      expiration = TimeCurrent() + InpPendingExpiryHours * 3600;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(20);

   // Buy Stop above previous day high
   if(CountOurPendingOrders(ORDER_TYPE_BUY_STOP) == 0)
   {
      if(buyEntry > ask + minStopDistance)
      {
         if(HasEnoughMargin(ORDER_TYPE_BUY_STOP, lots, buyEntry))
         {
            bool ok = trade.BuyStop(lots, buyEntry, g_symbol, buySL, buyTP, timeType, expiration, "PDH breakout buy stop");
            if(ok)
               Log("Placed BuyStop @ " + DoubleToString(buyEntry, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)) + " lots=" + DoubleToString(lots, 2));
            else
               Log("BuyStop failed. retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
         }
         else
            Log("Skipped BuyStop: not enough free margin for lot size.");
      }
      else
         Log("Skipped BuyStop: price already too close/above previous high edge.");
   }

   // Sell Stop below previous day low
   if(CountOurPendingOrders(ORDER_TYPE_SELL_STOP) == 0)
   {
      if(sellEntry < bid - minStopDistance)
      {
         if(HasEnoughMargin(ORDER_TYPE_SELL_STOP, lots, sellEntry))
         {
            bool ok = trade.SellStop(lots, sellEntry, g_symbol, sellSL, sellTP, timeType, expiration, "PDL breakout sell stop");
            if(ok)
               Log("Placed SellStop @ " + DoubleToString(sellEntry, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)) + " lots=" + DoubleToString(lots, 2));
            else
               Log("SellStop failed. retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
         }
         else
            Log("Skipped SellStop: not enough free margin for lot size.");
      }
      else
         Log("Skipped SellStop: price already too close/below previous low edge.");
   }
}

//+------------------------------------------------------------------+
//| Fast trade management                                             |
//+------------------------------------------------------------------+
void ModifySLIfBetter(ulong ticket, ENUM_POSITION_TYPE posType, double newSL, double currentSL, double currentTP)
{
   newSL = NormalizePriceForSymbol(g_symbol, newSL);

   bool better = false;
   if(posType == POSITION_TYPE_BUY)
      better = (currentSL <= 0.0 || newSL > currentSL);
   else if(posType == POSITION_TYPE_SELL)
      better = (currentSL <= 0.0 || newSL < currentSL);

   if(!better)
      return;

   if(!trade.PositionModify(ticket, newSL, currentTP))
      Log("PositionModify failed #" + (string)ticket + " retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
}

void ManageOpenPositions()
{
   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return;

   double point = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   if(point <= 0.0)
      return;

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(20);

   int ourPositions = CountOurOpenPositions();
   if(ourPositions > 0 && InpCancelOppositeOnFill)
      CancelOurPendingOrders();

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;

      string sym = PositionGetString(POSITION_SYMBOL);
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(sym != g_symbol || magic != InpMagicNumber)
         continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);

      double profitPoints = 0.0;
      if(type == POSITION_TYPE_BUY)
         profitPoints = (bid - openPrice) / point;
      else if(type == POSITION_TYPE_SELL)
         profitPoints = (openPrice - ask) / point;

      if(InpUseQuickProfitClose && profitPoints >= InpQuickProfitClosePoints)
      {
         if(trade.PositionClose(ticket))
            Log("Quick profit closed position #" + (string)ticket + " at +" + DoubleToString(profitPoints, 1) + " points");
         else
            Log("Quick profit close failed #" + (string)ticket + " retcode=" + (string)trade.ResultRetcode());
         continue;
      }

      // Fast break-even
      if(InpUseBreakEven && profitPoints >= InpBreakEvenTriggerPoints)
      {
         if(type == POSITION_TYPE_BUY)
         {
            double beSL = openPrice + InpBreakEvenLockPoints * point;
            if(sl <= 0.0 || sl < beSL)
               ModifySLIfBetter(ticket, type, beSL, sl, tp);
         }
         else if(type == POSITION_TYPE_SELL)
         {
            double beSL = openPrice - InpBreakEvenLockPoints * point;
            if(sl <= 0.0 || sl > beSL)
               ModifySLIfBetter(ticket, type, beSL, sl, tp);
         }
      }

      // Tight trailing stop
      if(InpUseFastTrailing && profitPoints >= InpTrailStartPoints)
      {
         if(type == POSITION_TYPE_BUY)
         {
            double trailSL = bid - InpTrailDistancePoints * point;
            if(trailSL > openPrice && (sl <= 0.0 || trailSL > sl + InpTrailStepPoints * point))
               ModifySLIfBetter(ticket, type, trailSL, sl, tp);
         }
         else if(type == POSITION_TYPE_SELL)
         {
            double trailSL = ask + InpTrailDistancePoints * point;
            if(trailSL < openPrice && (sl <= 0.0 || trailSL < sl - InpTrailStepPoints * point))
               ModifySLIfBetter(ticket, type, trailSL, sl, tp);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Daily equity protection                                           |
//+------------------------------------------------------------------+
void CheckDailyProtection()
{
   if(!InpUseDailyLossStop || g_tradingDisabledToday || g_dayStartEquity <= 0.0)
      return;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double limitEquity = g_dayStartEquity * (1.0 - InpDailyLossStopPercent / 100.0);

   if(equity <= limitEquity)
   {
      g_tradingDisabledToday = true;
      CancelOurPendingOrders();
      if(InpCloseAllOnDailyStop)
         CloseOurPositions();

      Log("DAILY LOSS STOP HIT. Trading disabled until next D1 candle. StartEquity=" +
          DoubleToString(g_dayStartEquity, 2) + " CurrentEquity=" + DoubleToString(equity, 2));
   }
}

//+------------------------------------------------------------------+
//| Expert events                                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   g_symbol = InpTradeSymbol;
   if(g_symbol == "")
      g_symbol = _Symbol;

   if(!SymbolSelect(g_symbol, true))
   {
      Print("Failed to select symbol: ", g_symbol);
      return INIT_FAILED;
   }

   if(InpGoldOnly && !ContainsGoldName(g_symbol))
   {
      Print("This EA is configured for gold only. Current symbol is: ", g_symbol,
            ". Disable InpGoldOnly if you really want another symbol.");
      return INIT_FAILED;
   }

   if(InpStopLossPoints <= 0)
   {
      Print("StopLossPoints must be greater than 0 for this high-risk breakout EA.");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(20);

   g_currentD1Open = 0;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_dayStartTime = iTime(g_symbol, PERIOD_D1, 0);

   if(!RefreshPreviousDayLevels())
   {
      Print("EA initialized, but previous D1 levels are not ready. Load more history and wait for ticks.");
   }

   Log("Initialized on " + g_symbol + ". Attach to XAUUSD/GOLD chart and backtest first.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   Log("Deinitialized. Reason=" + (string)reason);
}

void OnTick()
{
   if(!RefreshPreviousDayLevels())
      return;

   CheckDailyProtection();
   ManageOpenPositions();

   if(InpRebuildMissingOrders || CountOurPendingOrders() == 0)
      PlaceDailyEdgeOrders();
}
//+------------------------------------------------------------------+
