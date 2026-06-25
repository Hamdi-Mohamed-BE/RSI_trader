//+------------------------------------------------------------------+
//| XAU Previous Day Edge Breakout EA v2 FIXED                       |
//| Strategy: previous-day high/low breakout orders for gold          |
//|                                                                  |
//| What changed in v2:                                               |
//| - Wider gold spread default, so it does not silently skip trades. |
//| - Price-distance inputs for gold instead of confusing raw points. |
//| - Pending orders PLUS market fallback when price is already past  |
//|   previous day high/low.                                          |
//| - Auto lot reduction if the requested lot is too large for margin.|
//| - Draws previous-day high/low and trigger levels on chart.         |
//| - More Journal debug messages explaining exactly why it skipped.  |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"
#property description "XAU previous-day high/low breakout EA with aggressive fast trailing and robust defaults."

#include <Trade/Trade.mqh>

CTrade trade;

enum ENUM_LOT_MODE
{
   LOT_FIXED        = 0,
   LOT_RISK_PERCENT = 1
};

enum ENUM_ENTRY_MODE
{
   ENTRY_PENDING_STOPS       = 0, // Only place Buy Stop / Sell Stop
   ENTRY_MARKET_ON_TOUCH     = 1, // No pending orders, enter market when edge is touched/broken
   ENTRY_PENDING_PLUS_MARKET = 2  // Best default: pending orders + market fallback
};

//======================== MAIN SETTINGS ============================
input string          InpTradeSymbol              = "";       // Empty = chart symbol
input bool            InpGoldOnly                 = true;     // Only allow XAU/GOLD symbols
input long            InpMagicNumber              = 27062402; // Magic number
input ENUM_ENTRY_MODE InpEntryMode                = ENTRY_PENDING_PLUS_MARKET;
input bool            InpTradeAllSessions         = true;     // TRUE = trade Asia/London/NY/all day
input int             InpStartHourServer          = 0;        // Used only if TradeAllSessions=false
input int             InpEndHourServer            = 23;       // Used only if TradeAllSessions=false
input double          InpMaxSpreadPrice           = 0.75;     // Gold spread filter in price, e.g. 0.75 = 75 cents
input bool            InpPrintDebug               = true;     // Print skip/fill reasons in Journal
input bool            InpDrawLevelsOnChart        = true;     // Draw PDH/PDL + trigger lines

//======================== BREAKOUT LEVEL SETTINGS ==================
input double          InpEntryOffsetPrice         = 0.10;     // Buy above PDH by this price; sell below PDL by this price
input bool            InpRebuildMissingOrders     = true;     // Re-place missing daily orders if no position
input bool            InpCancelOppositeOnFill     = true;     // OCO behavior
input bool            InpOnePositionAtATime       = true;     // Safer for high-lot trading
input bool            InpOneTradePerSidePerDay    = false;    // False = can re-enter after stop/close, within max trades/day
input int             InpMaxFilledTradesPerDay    = 6;        // Max entries/day for this EA/symbol
input bool            InpEnterIfAlreadyBeyondEdge = true;     // Market fallback if EA starts after edge already broke

//======================== LOT / RISK SETTINGS =======================
input ENUM_LOT_MODE   InpLotMode                  = LOT_FIXED;
input double          InpFixedLot                 = 0.10;     // Aggressive default for gold; raise only after testing
input double          InpRiskPercent              = 2.00;     // Used only if LotMode = LOT_RISK_PERCENT
input double          InpMaxLotCap                = 3.00;     // Hard cap
input bool            InpAutoReduceLotForMargin   = true;     // If lot too high, reduce until margin fits
input double          InpMarginSafetyMultiplier   = 1.05;     // Require free margin >= margin * this multiplier

//======================== EXIT / FAST WIN SETTINGS ==================
input double          InpStopLossPrice            = 1.50;     // Gold SL in price, e.g. 1.50 dollars
input double          InpTakeProfitPrice          = 0.00;     // 0 = no fixed TP, let quick close/trailing manage
input bool            InpUseQuickProfitClose      = true;     // Close quickly in profit
input double          InpQuickProfitClosePrice    = 0.45;     // Close when profit reaches this price distance
input bool            InpUseBreakEven             = true;
input double          InpBreakEvenTriggerPrice    = 0.25;     // Move SL to BE quickly after this profit distance
input double          InpBreakEvenLockPrice       = 0.05;     // Lock this much price beyond entry
input bool            InpUseFastTrailing          = true;
input double          InpTrailStartPrice          = 0.30;     // Start trailing early
input double          InpTrailDistancePrice       = 0.20;     // Tight trailing distance
input double          InpTrailStepPrice           = 0.05;     // Modify SL after this improvement

//======================== PENDING ORDER SETTINGS ====================
input bool            InpUsePendingExpiration     = false;    // Some brokers reject expiration; GTC is safest
input int             InpPendingExpiryHours       = 20;
input int             InpDeviationPoints          = 50;       // Slippage/deviation for market orders and modifications

//======================== SAFETY SETTINGS ===========================
input bool            InpUseDailyLossStop         = true;
input double          InpDailyLossStopPercent     = 10.0;     // Disable trading for day if equity drops this %
input bool            InpCloseAllOnDailyStop      = true;

//======================== INTERNAL STATE ============================
string   g_symbol = "";
datetime g_currentD1Open = 0;
datetime g_dayStartTime = 0;
double   g_dayStartEquity = 0.0;
double   g_prevHigh = 0.0;
double   g_prevLow = 0.0;
double   g_buyTrigger = 0.0;
double   g_sellTrigger = 0.0;
bool     g_tradingDisabledToday = false;
bool     g_levelsReady = false;

//+------------------------------------------------------------------+
//| Logging / formatting                                              |
//+------------------------------------------------------------------+
void Log(const string msg)
{
   if(InpPrintDebug)
      Print("[XAU PD Edge v2] ", msg);
}

string Dbl(const double value)
{
   int digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
   return DoubleToString(value, digits);
}

//+------------------------------------------------------------------+
//| Symbol helpers                                                    |
//+------------------------------------------------------------------+
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

   if(minLot <= 0.0) minLot = 0.01;
   if(maxLot <= 0.0) maxLot = 100.0;
   if(step   <= 0.0) step   = 0.01;

   lots = MathMax(minLot, lots);
   lots = MathMin(maxLot, lots);
   lots = MathMin(InpMaxLotCap, lots);

   lots = MathFloor(lots / step + 1e-9) * step;
   lots = MathMax(minLot, lots);

   return NormalizeDouble(lots, VolumeDigitsFromStep(step));
}

double NormalizePriceForSymbol(const string sym, double price)
{
   double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);

   if(tickSize <= 0.0)
      tickSize = SymbolInfoDouble(sym, SYMBOL_POINT);
   if(tickSize <= 0.0)
      tickSize = 0.01;

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
   return (bid > 0.0 && ask > 0.0 && ask >= bid);
}

double MinTradeDistancePrice()
{
   double point = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   double tick  = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   int stopsLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_STOPS_LEVEL);

   if(point <= 0.0) point = 0.01;
   if(tick  <= 0.0) tick  = point;

   return MathMax(stopsLevel * point, tick * 2.0);
}

bool SpreadOK()
{
   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
   {
      Log("Skipped: no valid bid/ask tick yet.");
      return false;
   }

   double spread = ask - bid;
   if(spread > InpMaxSpreadPrice)
   {
      Log("Skipped: spread too high. spread=" + DoubleToString(spread, 3) +
          " max=" + DoubleToString(InpMaxSpreadPrice, 3));
      return false;
   }

   return true;
}

bool IsTradingTimeAllowed()
{
   if(InpTradeAllSessions)
      return true;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpStartHourServer <= InpEndHourServer)
      return (dt.hour >= InpStartHourServer && dt.hour <= InpEndHourServer);

   return (dt.hour >= InpStartHourServer || dt.hour <= InpEndHourServer);
}

bool CanTradeNow()
{
   long tradeMode = SymbolInfoInteger(g_symbol, SYMBOL_TRADE_MODE);
   if(tradeMode == SYMBOL_TRADE_MODE_DISABLED || tradeMode == SYMBOL_TRADE_MODE_CLOSEONLY)
   {
      Log("Skipped: symbol trade mode is disabled/close-only for " + g_symbol);
      return false;
   }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      Log("Skipped: terminal AutoTrading is disabled.");
      return false;
   }

   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Log("Skipped: EA trading permission is disabled in MT5.");
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Chart drawing                                                     |
//+------------------------------------------------------------------+
void DrawHLine(const string name, const double price, const color clr, const ENUM_LINE_STYLE style, const int width)
{
   if(!InpDrawLevelsOnChart)
      return;

   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);

   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

void DrawLevels()
{
   string prefix = "XAU_PD_EDGE_V2_" + g_symbol + "_";
   DrawHLine(prefix + "PDH", g_prevHigh, clrLime, STYLE_SOLID, 2);
   DrawHLine(prefix + "PDL", g_prevLow, clrTomato, STYLE_SOLID, 2);
   DrawHLine(prefix + "BUY_TRIGGER", g_buyTrigger, clrAqua, STYLE_DOT, 1);
   DrawHLine(prefix + "SELL_TRIGGER", g_sellTrigger, clrAqua, STYLE_DOT, 1);
}

//+------------------------------------------------------------------+
//| Position/order helpers                                            |
//+------------------------------------------------------------------+
bool IsOurPositionSelectedByIndex(const int index)
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

int CountTodayEntryDeals(const int sideFilter = -1)
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
      long type  = HistoryDealGetInteger(dealTicket, DEAL_TYPE);

      if(sym != g_symbol || magic != InpMagicNumber || entry != DEAL_ENTRY_IN)
         continue;

      if(sideFilter == 0 && type != DEAL_TYPE_BUY)
         continue;
      if(sideFilter == 1 && type != DEAL_TYPE_SELL)
         continue;

      count++;
   }

   return count;
}

bool BuyTakenToday()
{
   return (CountTodayEntryDeals(0) > 0);
}

bool SellTakenToday()
{
   return (CountTodayEntryDeals(1) > 0);
}

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
         Log("Failed to delete pending order #" + (string)ticket +
             " retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
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
         Log("Failed to close position #" + (string)ticket +
             " retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Previous day levels                                               |
//+------------------------------------------------------------------+
bool RefreshPreviousDayLevels()
{
   if(iBars(g_symbol, PERIOD_D1) < 3)
   {
      Log("Skipped: not enough D1 history. Open D1 chart once or download more history.");
      return false;
   }

   datetime d1Open = iTime(g_symbol, PERIOD_D1, 0);
   if(d1Open <= 0)
      return false;

   if(d1Open == g_currentD1Open && g_levelsReady)
      return true;

   double prevHigh = iHigh(g_symbol, PERIOD_D1, 1);
   double prevLow  = iLow(g_symbol, PERIOD_D1, 1);

   if(prevHigh <= 0.0 || prevLow <= 0.0 || prevHigh <= prevLow)
   {
      Log("Skipped: invalid previous D1 high/low. prevHigh=" + DoubleToString(prevHigh, 5) +
          " prevLow=" + DoubleToString(prevLow, 5));
      return false;
   }

   bool isNewDay = (d1Open != g_currentD1Open);

   g_currentD1Open = d1Open;
   g_dayStartTime = d1Open;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_prevHigh = NormalizePriceForSymbol(g_symbol, prevHigh);
   g_prevLow  = NormalizePriceForSymbol(g_symbol, prevLow);
   g_buyTrigger  = NormalizePriceForSymbol(g_symbol, g_prevHigh + InpEntryOffsetPrice);
   g_sellTrigger = NormalizePriceForSymbol(g_symbol, g_prevLow  - InpEntryOffsetPrice);
   g_tradingDisabledToday = false;
   g_levelsReady = true;

   DrawLevels();

   if(isNewDay)
   {
      CancelOurPendingOrders();
      Log("New previous-day levels: PDH=" + Dbl(g_prevHigh) +
          " PDL=" + Dbl(g_prevLow) +
          " BuyTrigger=" + Dbl(g_buyTrigger) +
          " SellTrigger=" + Dbl(g_sellTrigger));
   }

   return true;
}

//+------------------------------------------------------------------+
//| Lot calculation                                                   |
//+------------------------------------------------------------------+
double CalculateRequestedLot()
{
   if(InpLotMode == LOT_FIXED)
      return NormalizeVolumeForSymbol(g_symbol, InpFixedLot);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * InpRiskPercent / 100.0;

   double tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickValue <= 0.0 || tickSize <= 0.0 || InpStopLossPrice <= 0.0)
      return NormalizeVolumeForSymbol(g_symbol, InpFixedLot);

   double ticks = InpStopLossPrice / tickSize;
   double lossPerLot = ticks * tickValue;

   if(lossPerLot <= 0.0)
      return NormalizeVolumeForSymbol(g_symbol, InpFixedLot);

   double lots = riskMoney / lossPerLot;
   return NormalizeVolumeForSymbol(g_symbol, lots);
}

double MarginSafeLot(const ENUM_ORDER_TYPE orderType, const double requestedLots, const double price)
{
   double lots = NormalizeVolumeForSymbol(g_symbol, requestedLots);
   double minLot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   double step   = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);

   if(minLot <= 0.0) minLot = 0.01;
   if(step   <= 0.0) step   = 0.01;

   double margin = 0.0;
   if(!OrderCalcMargin(orderType, g_symbol, lots, price, margin))
   {
      Log("OrderCalcMargin failed; sending requested lot and letting broker decide.");
      return lots;
   }

   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(freeMargin >= margin * InpMarginSafetyMultiplier)
      return lots;

   if(!InpAutoReduceLotForMargin)
   {
      Log("Skipped: not enough margin for lots=" + DoubleToString(lots, 2) +
          " required=" + DoubleToString(margin, 2) +
          " free=" + DoubleToString(freeMargin, 2));
      return 0.0;
   }

   int stepsFromMin = (int)MathFloor((lots - minLot) / step + 1e-9);
   for(int k = stepsFromMin; k >= 0; k--)
   {
      double testLots = NormalizeVolumeForSymbol(g_symbol, minLot + k * step);
      margin = 0.0;
      if(!OrderCalcMargin(orderType, g_symbol, testLots, price, margin))
         continue;

      if(freeMargin >= margin * InpMarginSafetyMultiplier)
      {
         if(testLots < lots)
            Log("Lot auto-reduced for margin: requested=" + DoubleToString(lots, 2) +
                " used=" + DoubleToString(testLots, 2));
         return testLots;
      }
   }

   Log("Skipped: even minimum lot does not fit margin. free=" + DoubleToString(freeMargin, 2));
   return 0.0;
}

//+------------------------------------------------------------------+
//| Stop/TP building                                                  |
//+------------------------------------------------------------------+
void BuildStops(const bool isBuy, const double entryPrice, double &sl, double &tp)
{
   double minDist = MinTradeDistancePrice();
   double slDist = MathMax(InpStopLossPrice, minDist * 1.20);
   double tpDist = InpTakeProfitPrice;

   if(isBuy)
   {
      sl = NormalizePriceForSymbol(g_symbol, entryPrice - slDist);
      tp = (tpDist > 0.0 ? NormalizePriceForSymbol(g_symbol, entryPrice + tpDist) : 0.0);
   }
   else
   {
      sl = NormalizePriceForSymbol(g_symbol, entryPrice + slDist);
      tp = (tpDist > 0.0 ? NormalizePriceForSymbol(g_symbol, entryPrice - tpDist) : 0.0);
   }
}

bool CanOpenNewTrade()
{
   if(!g_levelsReady)
      return false;

   if(g_tradingDisabledToday)
   {
      Log("Skipped: daily loss stop disabled trading today.");
      return false;
   }

   if(!CanTradeNow())
      return false;

   if(!IsTradingTimeAllowed())
   {
      Log("Skipped: outside configured session window.");
      return false;
   }

   if(!SpreadOK())
      return false;

   if(InpOnePositionAtATime && CountOurOpenPositions() > 0)
      return false;

   if(CountTodayEntryDeals() >= InpMaxFilledTradesPerDay)
   {
      Log("Skipped: max filled trades reached for today.");
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Market entries                                                    |
//+------------------------------------------------------------------+
bool OpenMarketBuy()
{
   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return false;

   double sl, tp;
   BuildStops(true, ask, sl, tp);

   double lots = MarginSafeLot(ORDER_TYPE_BUY, CalculateRequestedLot(), ask);
   if(lots <= 0.0)
      return false;

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);

   bool ok = trade.Buy(lots, g_symbol, ask, sl, tp, "PDH breakout BUY market");
   if(ok)
   {
      Log("BUY market opened @ " + Dbl(ask) + " lots=" + DoubleToString(lots, 2) +
          " SL=" + Dbl(sl) + " TP=" + (tp > 0 ? Dbl(tp) : "none"));
      if(InpCancelOppositeOnFill)
         CancelOurPendingOrders(ORDER_TYPE_SELL_STOP);
   }
   else
   {
      Log("BUY market failed. retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
   }

   return ok;
}

bool OpenMarketSell()
{
   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return false;

   double sl, tp;
   BuildStops(false, bid, sl, tp);

   double lots = MarginSafeLot(ORDER_TYPE_SELL, CalculateRequestedLot(), bid);
   if(lots <= 0.0)
      return false;

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);

   bool ok = trade.Sell(lots, g_symbol, bid, sl, tp, "PDL breakout SELL market");
   if(ok)
   {
      Log("SELL market opened @ " + Dbl(bid) + " lots=" + DoubleToString(lots, 2) +
          " SL=" + Dbl(sl) + " TP=" + (tp > 0 ? Dbl(tp) : "none"));
      if(InpCancelOppositeOnFill)
         CancelOurPendingOrders(ORDER_TYPE_BUY_STOP);
   }
   else
   {
      Log("SELL market failed. retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
   }

   return ok;
}

void CheckMarketFallbackEntries()
{
   if(InpEntryMode == ENTRY_PENDING_STOPS)
      return;

   if(!CanOpenNewTrade())
      return;

   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return;

   bool buyAlreadyTaken  = InpOneTradePerSidePerDay && BuyTakenToday();
   bool sellAlreadyTaken = InpOneTradePerSidePerDay && SellTakenToday();

   if(ask >= g_buyTrigger && !buyAlreadyTaken)
   {
      if(InpEnterIfAlreadyBeyondEdge || ask - g_buyTrigger <= MathMax(InpStopLossPrice, 0.01))
      {
         OpenMarketBuy();
         return;
      }
   }

   if(bid <= g_sellTrigger && !sellAlreadyTaken)
   {
      if(InpEnterIfAlreadyBeyondEdge || g_sellTrigger - bid <= MathMax(InpStopLossPrice, 0.01))
      {
         OpenMarketSell();
         return;
      }
   }
}

//+------------------------------------------------------------------+
//| Pending orders                                                    |
//+------------------------------------------------------------------+
void PlaceDailyEdgePendingOrders()
{
   if(InpEntryMode == ENTRY_MARKET_ON_TOUCH)
      return;

   if(!CanOpenNewTrade())
      return;

   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return;

   double minDist = MinTradeDistancePrice();
   double requestedLots = CalculateRequestedLot();
   ENUM_ORDER_TYPE_TIME timeType = ORDER_TIME_GTC;
   datetime expiration = 0;

   if(InpUsePendingExpiration)
   {
      timeType = ORDER_TIME_SPECIFIED;
      expiration = TimeCurrent() + InpPendingExpiryHours * 3600;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);

   // Buy Stop above previous day high
   if(CountOurPendingOrders(ORDER_TYPE_BUY_STOP) == 0)
   {
      bool buyTaken = InpOneTradePerSidePerDay && BuyTakenToday();
      if(!buyTaken)
      {
         double buyEntry = MathMax(g_buyTrigger, ask + minDist);
         buyEntry = NormalizePriceForSymbol(g_symbol, buyEntry);

         if(buyEntry > ask + minDist * 0.90)
         {
            double sl, tp;
            BuildStops(true, buyEntry, sl, tp);

            double lots = MarginSafeLot(ORDER_TYPE_BUY_STOP, requestedLots, buyEntry);
            if(lots > 0.0)
            {
               bool ok = trade.BuyStop(lots, buyEntry, g_symbol, sl, tp, timeType, expiration, "PDH breakout BUY STOP");
               if(ok)
                  Log("BuyStop placed @ " + Dbl(buyEntry) + " lots=" + DoubleToString(lots, 2) +
                      " SL=" + Dbl(sl) + " TP=" + (tp > 0 ? Dbl(tp) : "none"));
               else
                  Log("BuyStop failed. retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
            }
         }
         else
         {
            Log("BuyStop skipped: current ask is too close/above trigger. Market fallback can handle it.");
         }
      }
   }

   // Sell Stop below previous day low
   if(CountOurPendingOrders(ORDER_TYPE_SELL_STOP) == 0)
   {
      bool sellTaken = InpOneTradePerSidePerDay && SellTakenToday();
      if(!sellTaken)
      {
         double sellEntry = MathMin(g_sellTrigger, bid - minDist);
         sellEntry = NormalizePriceForSymbol(g_symbol, sellEntry);

         if(sellEntry < bid - minDist * 0.90)
         {
            double sl, tp;
            BuildStops(false, sellEntry, sl, tp);

            double lots = MarginSafeLot(ORDER_TYPE_SELL_STOP, requestedLots, sellEntry);
            if(lots > 0.0)
            {
               bool ok = trade.SellStop(lots, sellEntry, g_symbol, sl, tp, timeType, expiration, "PDL breakout SELL STOP");
               if(ok)
                  Log("SellStop placed @ " + Dbl(sellEntry) + " lots=" + DoubleToString(lots, 2) +
                      " SL=" + Dbl(sl) + " TP=" + (tp > 0 ? Dbl(tp) : "none"));
               else
                  Log("SellStop failed. retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
            }
         }
         else
         {
            Log("SellStop skipped: current bid is too close/below trigger. Market fallback can handle it.");
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Trade management                                                  |
//+------------------------------------------------------------------+
void ModifySLIfBetter(const ulong ticket, const ENUM_POSITION_TYPE posType, double newSL, const double currentSL, const double currentTP)
{
   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return;

   double minDist = MinTradeDistancePrice();

   if(posType == POSITION_TYPE_BUY)
   {
      double maxAllowedSL = NormalizePriceForSymbol(g_symbol, bid - minDist);
      if(newSL > maxAllowedSL)
         newSL = maxAllowedSL;
   }
   else if(posType == POSITION_TYPE_SELL)
   {
      double minAllowedSL = NormalizePriceForSymbol(g_symbol, ask + minDist);
      if(newSL < minAllowedSL)
         newSL = minAllowedSL;
   }

   newSL = NormalizePriceForSymbol(g_symbol, newSL);

   bool better = false;
   if(posType == POSITION_TYPE_BUY)
      better = (currentSL <= 0.0 || newSL > currentSL + MinTradeDistancePrice() * 0.05);
   else if(posType == POSITION_TYPE_SELL)
      better = (currentSL <= 0.0 || newSL < currentSL - MinTradeDistancePrice() * 0.05);

   if(!better)
      return;

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);

   if(!trade.PositionModify(ticket, newSL, currentTP))
      Log("PositionModify failed #" + (string)ticket +
          " retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
}

void ManageOpenPositions()
{
   double bid, ask;
   if(!GetBidAsk(g_symbol, bid, ask))
      return;

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

      double profitDist = 0.0;
      if(type == POSITION_TYPE_BUY)
         profitDist = bid - openPrice;
      else if(type == POSITION_TYPE_SELL)
         profitDist = openPrice - ask;

      trade.SetExpertMagicNumber(InpMagicNumber);
      trade.SetDeviationInPoints(InpDeviationPoints);

      if(InpUseQuickProfitClose && profitDist >= InpQuickProfitClosePrice)
      {
         if(trade.PositionClose(ticket))
            Log("Quick profit closed #" + (string)ticket + " profitDistance=" + DoubleToString(profitDist, 3));
         else
            Log("Quick profit close failed #" + (string)ticket +
                " retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
         continue;
      }

      // Fast break-even
      if(InpUseBreakEven && profitDist >= InpBreakEvenTriggerPrice)
      {
         if(type == POSITION_TYPE_BUY)
         {
            double beSL = openPrice + InpBreakEvenLockPrice;
            ModifySLIfBetter(ticket, type, beSL, sl, tp);
         }
         else if(type == POSITION_TYPE_SELL)
         {
            double beSL = openPrice - InpBreakEvenLockPrice;
            ModifySLIfBetter(ticket, type, beSL, sl, tp);
         }
      }

      // Tight trailing stop
      if(InpUseFastTrailing && profitDist >= InpTrailStartPrice)
      {
         if(type == POSITION_TYPE_BUY)
         {
            double trailSL = bid - InpTrailDistancePrice;
            if(trailSL > openPrice && (sl <= 0.0 || trailSL > sl + InpTrailStepPrice))
               ModifySLIfBetter(ticket, type, trailSL, sl, tp);
         }
         else if(type == POSITION_TYPE_SELL)
         {
            double trailSL = ask + InpTrailDistancePrice;
            if(trailSL < openPrice && (sl <= 0.0 || trailSL < sl - InpTrailStepPrice))
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
//| Status panel                                                      |
//+------------------------------------------------------------------+
void UpdateStatusComment()
{
   if(!InpPrintDebug)
      return;

   double bid = 0.0, ask = 0.0;
   GetBidAsk(g_symbol, bid, ask);

   string status = "XAU Previous-Day Edge Breakout EA v2 FIXED\n";
   status += "Symbol: " + g_symbol + " | EntryMode: " + (string)InpEntryMode + " | AllSessions: " + (InpTradeAllSessions ? "true" : "false") + "\n";
   status += "PDH: " + Dbl(g_prevHigh) + " | PDL: " + Dbl(g_prevLow) + "\n";
   status += "BuyTrigger: " + Dbl(g_buyTrigger) + " | SellTrigger: " + Dbl(g_sellTrigger) + "\n";
   status += "Bid: " + Dbl(bid) + " | Ask: " + Dbl(ask) + " | Spread: " + DoubleToString(ask - bid, 3) + "\n";
   status += "OpenPositions: " + (string)CountOurOpenPositions() + " | PendingOrders: " + (string)CountOurPendingOrders() + " | DealsToday: " + (string)CountTodayEntryDeals() + "\n";
   status += "If no trades: check Journal for exact skip reason.";

   Comment(status);
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
            ". Use XAUUSD/XAUUSDm/GOLD or set InpGoldOnly=false.");
      return INIT_FAILED;
   }

   if(InpStopLossPrice <= 0.0)
   {
      Print("InpStopLossPrice must be greater than 0 for this breakout EA.");
      return INIT_FAILED;
   }

   if(InpFixedLot <= 0.0 && InpLotMode == LOT_FIXED)
   {
      Print("InpFixedLot must be greater than 0.");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);

   g_currentD1Open = 0;
   g_levelsReady = false;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_dayStartTime = iTime(g_symbol, PERIOD_D1, 0);

   RefreshPreviousDayLevels();

   Log("Initialized on " + g_symbol +
       ". Defaults are optimized to actually place trades on gold: wider spread filter, pending+market fallback, fast BE/trailing.");

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   Comment("");
   Log("Deinitialized. Reason=" + (string)reason);
}

void OnTick()
{
   if(!RefreshPreviousDayLevels())
      return;

   CheckDailyProtection();
   ManageOpenPositions();

   // First, if price is already at/beyond edge, enter using market fallback.
   CheckMarketFallbackEntries();

   // Then keep pending orders parked at both previous-day edges when possible.
   if(InpRebuildMissingOrders || CountOurPendingOrders() == 0)
      PlaceDailyEdgePendingOrders();

   UpdateStatusComment();
}
//+------------------------------------------------------------------+
