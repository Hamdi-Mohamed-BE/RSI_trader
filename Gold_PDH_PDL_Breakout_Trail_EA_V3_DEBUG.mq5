//+------------------------------------------------------------------+
//| Gold_PDH_PDL_Breakout_Trail_EA_V3_DEBUG.mq5                      |
//| Previous-day high/low breakout EA for MetaTrader 5                |
//|                                                                  |
//| Strategy from transcript:                                        |
//| - At the new trading day, place Buy Stop at previous day high     |
//| - Place Sell Stop at previous day low                             |
//| - 1:1 SL/TP by default                                            |
//| - Trail stop aggressively after activation                        |
//|                                                                  |
//| V3 changes:                                                       |
//| - Raw MqlTradeRequest + OrderCheck diagnostic logs                 |
//| - Does not silently skip; prints exact broker/tester rejection     |
//| - Optional market entry if the PDH/PDL was already broken before   |
//|   the EA could place the pending order                             |
//| - Safer defaults for XAUUSDm / 3-digit gold                        |
//+------------------------------------------------------------------+
#property strict
#property version   "3.00"
#property description "Gold previous-day high/low breakout EA with aggressive trailing and full diagnostics."

//----------------------------- ENUMS --------------------------------
enum ENUM_LOT_MODE_V3
{
   LOT_FIXED_V3        = 0,
   LOT_RISK_PERCENT_V3 = 1
};

enum ENUM_LEVEL_ALREADY_BROKEN_MODE
{
   LEVEL_SKIP_V3            = 0, // Strict: do nothing if the level is already broken
   LEVEL_NEAREST_PENDING_V3 = 1, // Put stop order at nearest valid distance from current price
   LEVEL_MARKET_ENTRY_V3    = 2  // Enter market immediately if PDH/PDL already broken
};

enum ENUM_SLTP_MODE_V3
{
   SLTP_PRICE_DISTANCE_V3 = 0, // XAU price distance, e.g. 25.00 = $25 move
   SLTP_POINTS_V3         = 1  // Broker points, e.g. XAUUSDm 25000 points = $25 if _Point=0.001
};

//----------------------------- INPUTS -------------------------------
input string                         InpEAName                       = "PDH/PDL Gold Breakout Trail V3";
input ulong                          InpMagicNumber                  = 26062403;

// Trade size
input ENUM_LOT_MODE_V3               InpLotMode                      = LOT_FIXED_V3;
input double                         InpFixedLots                    = 0.10;
input double                         InpRiskPercent                  = 2.0;

// Entry logic
input bool                           InpPlaceBuySide                 = true;
input bool                           InpPlaceSellSide                = true;
input int                            InpEntryOffsetPoints            = 20;       // XAUUSDm: 20 points = $0.02 if _Point=0.001
input ENUM_LEVEL_ALREADY_BROKEN_MODE InpIfLevelAlreadyBroken         = LEVEL_MARKET_ENTRY_V3;
input bool                           InpDeleteOldPendingOrdersNewDay = true;
input int                            InpMinSecondsBetweenRetries     = 5;

// SL/TP 1:1 default
input ENUM_SLTP_MODE_V3              InpSLTPMode                     = SLTP_PRICE_DISTANCE_V3;
input double                         InpSLTPPriceDistance            = 25.00;    // $25 move on gold
input int                            InpSLTPPoints                   = 25000;    // XAUUSDm 3-digit: 25000 = $25

// Filters
input int                            InpMaxSpreadPoints              = 0;        // 0 = disabled
input bool                           InpTradeMonday                  = true;
input bool                           InpTradeTuesday                 = true;
input bool                           InpTradeWednesday               = true;
input bool                           InpTradeThursday                = true;
input bool                           InpTradeFriday                  = true;

// Aggressive trailing
input bool                           InpUseBreakEven                 = true;
input int                            InpBreakEvenStartPoints         = 150;      // XAUUSDm: 150 points = $0.15
input int                            InpBreakEvenLockPoints          = 30;       // lock tiny profit
input bool                           InpUseTrailingStop              = true;
input int                            InpTrailStartPoints             = 180;      // start early
input int                            InpTrailDistancePoints          = 120;      // tight trail; raised automatically to broker minimum
input int                            InpTrailStepPoints              = 20;

// Diagnostics
input bool                           InpVerboseLogs                  = true;
input bool                           InpChartComment                 = true;
input int                            InpTimerSeconds                 = 1;

//----------------------------- GLOBALS ------------------------------
datetime g_dayStart          = 0;
datetime g_lastPlacementTry  = 0;
string   g_status            = "Starting";
bool     g_buyHandledMemory  = false;
bool     g_sellHandledMemory = false;

//+------------------------------------------------------------------+
//| Basic helpers                                                     |
//+------------------------------------------------------------------+
void SetStatus(const string text)
{
   g_status = text;
   if(InpVerboseLogs)
      Print(InpEAName, " | ", text);
}

int VolumeDigits()
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      return 2;

   int digits = 0;
   while(step < 1.0 && digits < 8)
   {
      step *= 10.0;
      digits++;
   }
   return digits;
}

double NormalizeLots(double lots)
{
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0.0)   step = 0.01;
   if(minLot <= 0.0) minLot = step;
   if(maxLot <= 0.0) maxLot = lots;

   lots = MathMax(minLot, MathMin(maxLot, lots));
   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, VolumeDigits());

   if(lots < minLot)
      lots = minLot;

   return lots;
}

double NormalizePrice(double price)
{
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0.0)
      tickSize = _Point;

   return NormalizeDouble(MathRound(price / tickSize) * tickSize, _Digits);
}

int SpreadPoints()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return 999999;

   return (int)MathRound((tick.ask - tick.bid) / _Point);
}

double BrokerMinStopDistancePrice()
{
   long stopsLevel  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freezeLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   long minPoints   = (long)MathMax((double)stopsLevel, (double)freezeLevel);

   // Add safety buffer, because some brokers reject exactly-at-minimum stops.
   return ((double)minPoints + 5.0) * _Point;
}

double SLTPDistancePrice()
{
   double dist = InpSLTPPriceDistance;
   if(InpSLTPMode == SLTP_POINTS_V3)
      dist = (double)InpSLTPPoints * _Point;

   return MathMax(dist, BrokerMinStopDistancePrice() * 3.0);
}

bool TradingDayAllowed(datetime dayStart)
{
   MqlDateTime dt;
   TimeToStruct(dayStart, dt);

   if(dt.day_of_week == 1) return InpTradeMonday;
   if(dt.day_of_week == 2) return InpTradeTuesday;
   if(dt.day_of_week == 3) return InpTradeWednesday;
   if(dt.day_of_week == 4) return InpTradeThursday;
   if(dt.day_of_week == 5) return InpTradeFriday;

   return false;
}

bool GetTick(MqlTick &tick)
{
   ResetLastError();
   if(!SymbolInfoTick(_Symbol, tick))
   {
      SetStatus("No tick yet. Error=" + IntegerToString(GetLastError()));
      return false;
   }
   return true;
}

double CalculateLots(const double entry, const double sl)
{
   if(InpLotMode == LOT_FIXED_V3)
      return NormalizeLots(InpFixedLots);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0)
   {
      SetStatus("Cannot calculate risk lots because equity is 0. Set Strategy Tester Deposit > 0.");
      return 0.0;
   }

   double riskMoney = equity * InpRiskPercent / 100.0;
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);

   if(tickSize <= 0.0 || tickValue <= 0.0)
   {
      SetStatus("Tick size/value unavailable. Falling back to fixed lots.");
      return NormalizeLots(InpFixedLots);
   }

   double priceRisk = MathAbs(entry - sl);
   double ticksRisk = priceRisk / tickSize;
   double lossPerLot = ticksRisk * tickValue;

   if(lossPerLot <= 0.0)
      return NormalizeLots(InpFixedLots);

   return NormalizeLots(riskMoney / lossPerLot);
}

//+------------------------------------------------------------------+
//| Existing orders / positions                                       |
//+------------------------------------------------------------------+
bool ActivePendingExists(const ENUM_ORDER_TYPE orderType)
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE) == orderType)
         return true;
   }
   return false;
}

bool ActivePositionExistsForSide(const ENUM_POSITION_TYPE posType)
{
   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == posType)
         return true;
   }
   return false;
}

bool HistoryShowsHandledToday(const bool isBuySide)
{
   datetime nowTime = TimeCurrent();
   if(nowTime <= 0 || g_dayStart <= 0)
      return false;

   if(!HistorySelect(g_dayStart, nowTime + 86400))
      return false;

   // Orders placed today: prevents duplicate re-placement after trigger/delete.
   for(int i = HistoryOrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = HistoryOrderGetTicket(i);
      if(ticket == 0)
         continue;

      if(HistoryOrderGetString(ticket, ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryOrderGetInteger(ticket, ORDER_MAGIC) != InpMagicNumber)
         continue;

      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)HistoryOrderGetInteger(ticket, ORDER_TYPE);
      datetime setupTime = (datetime)HistoryOrderGetInteger(ticket, ORDER_TIME_SETUP);
      if(setupTime < g_dayStart)
         continue;

      if(isBuySide && (type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_BUY))
         return true;
      if(!isBuySide && (type == ORDER_TYPE_SELL_STOP || type == ORDER_TYPE_SELL))
         return true;
   }

   // Deals opened today: extra protection in case order history is broker-specific.
   for(int j = HistoryDealsTotal() - 1; j >= 0; --j)
   {
      ulong dealTicket = HistoryDealGetTicket(j);
      if(dealTicket == 0)
         continue;

      if(HistoryDealGetString(dealTicket, DEAL_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryDealGetInteger(dealTicket, DEAL_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dealTicket, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;

      ENUM_DEAL_TYPE dealType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(dealTicket, DEAL_TYPE);
      datetime dealTime = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      if(dealTime < g_dayStart)
         continue;

      if(isBuySide && dealType == DEAL_TYPE_BUY)
         return true;
      if(!isBuySide && dealType == DEAL_TYPE_SELL)
         return true;
   }

   return false;
}

bool BuySideHandledToday()
{
   if(g_buyHandledMemory)
      return true;
   if(ActivePendingExists(ORDER_TYPE_BUY_STOP))
      return true;
   if(ActivePositionExistsForSide(POSITION_TYPE_BUY))
      return true;
   return HistoryShowsHandledToday(true);
}

bool SellSideHandledToday()
{
   if(g_sellHandledMemory)
      return true;
   if(ActivePendingExists(ORDER_TYPE_SELL_STOP))
      return true;
   if(ActivePositionExistsForSide(POSITION_TYPE_SELL))
      return true;
   return HistoryShowsHandledToday(false);
}

void DeleteOldPendings()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;

      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type != ORDER_TYPE_BUY_STOP && type != ORDER_TYPE_SELL_STOP)
         continue;

      MqlTradeRequest req;
      MqlTradeResult  res;
      ZeroMemory(req);
      ZeroMemory(res);

      req.action = TRADE_ACTION_REMOVE;
      req.order  = ticket;
      req.symbol = _Symbol;
      req.magic  = InpMagicNumber;

      ResetLastError();
      if(!OrderSend(req, res))
         SetStatus("Delete pending failed #" + (string)ticket + " error=" + (string)GetLastError() + " retcode=" + (string)res.retcode + " " + res.comment);
      else if(res.retcode != TRADE_RETCODE_DONE)
         SetStatus("Delete pending rejected #" + (string)ticket + " retcode=" + (string)res.retcode + " " + res.comment);
   }
}

//+------------------------------------------------------------------+
//| Order sending with detailed check                                 |
//+------------------------------------------------------------------+
bool CheckAndSend(MqlTradeRequest &req, const string label)
{
   MqlTradeCheckResult check;
   MqlTradeResult      res;
   ZeroMemory(check);
   ZeroMemory(res);

   ResetLastError();
   bool checkOk = OrderCheck(req, check);
   if(!checkOk || (check.retcode != TRADE_RETCODE_DONE && check.retcode != TRADE_RETCODE_PLACED))
   {
      SetStatus(label + " OrderCheck failed/rejected. checkOk=" + (checkOk ? "true" : "false") +
                " retcode=" + (string)check.retcode +
                " comment=" + check.comment +
                " margin=" + DoubleToString(check.margin, 2) +
                " free=" + DoubleToString(check.margin_free, 2) +
                " LastError=" + (string)GetLastError());
      return false;
   }

   ResetLastError();
   bool sendOk = OrderSend(req, res);
   if(!sendOk || (res.retcode != TRADE_RETCODE_DONE &&
                  res.retcode != TRADE_RETCODE_PLACED &&
                  res.retcode != TRADE_RETCODE_DONE_PARTIAL))
   {
      SetStatus(label + " OrderSend failed/rejected. sendOk=" + (sendOk ? "true" : "false") +
                " retcode=" + (string)res.retcode +
                " comment=" + res.comment +
                " price=" + DoubleToString(req.price, _Digits) +
                " sl=" + DoubleToString(req.sl, _Digits) +
                " tp=" + DoubleToString(req.tp, _Digits) +
                " lots=" + DoubleToString(req.volume, VolumeDigits()) +
                " LastError=" + (string)GetLastError());
      return false;
   }

   SetStatus(label + " SENT OK. ticket/order=" + (string)res.order +
             " deal=" + (string)res.deal +
             " lots=" + DoubleToString(req.volume, VolumeDigits()) +
             " price=" + DoubleToString(req.price, _Digits) +
             " sl=" + DoubleToString(req.sl, _Digits) +
             " tp=" + DoubleToString(req.tp, _Digits));
   return true;
}

bool SendPendingStop(const bool isBuy, const double entry, const double sl, const double tp, const double lots)
{
   MqlTradeRequest req;
   ZeroMemory(req);

   req.action       = TRADE_ACTION_PENDING;
   req.magic        = InpMagicNumber;
   req.symbol       = _Symbol;
   req.volume       = lots;
   req.type         = isBuy ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
   req.price        = NormalizePrice(entry);
   req.sl           = NormalizePrice(sl);
   req.tp           = NormalizePrice(tp);
   req.deviation    = 50;
   req.type_time    = ORDER_TIME_GTC;
   req.type_filling = ORDER_FILLING_RETURN;
   req.comment      = isBuy ? "PDH BuyStop V3" : "PDL SellStop V3";

   return CheckAndSend(req, isBuy ? "BUY STOP" : "SELL STOP");
}

bool SendMarketOrder(const bool isBuy, const double sl, const double tp, const double lots)
{
   MqlTick tick;
   if(!GetTick(tick))
      return false;

   MqlTradeRequest req;
   ZeroMemory(req);

   req.action    = TRADE_ACTION_DEAL;
   req.magic     = InpMagicNumber;
   req.symbol    = _Symbol;
   req.volume    = lots;
   req.type      = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.price     = NormalizePrice(isBuy ? tick.ask : tick.bid);
   req.sl        = NormalizePrice(sl);
   req.tp        = NormalizePrice(tp);
   req.deviation = 100;
   req.comment   = isBuy ? "PDH BuyMarket V3" : "PDL SellMarket V3";

   // Use symbol supported filling for market orders.
   long filling = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      req.type_filling = ORDER_FILLING_FOK;
   else if((filling & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      req.type_filling = ORDER_FILLING_IOC;
   else
      req.type_filling = ORDER_FILLING_RETURN;

   return CheckAndSend(req, isBuy ? "BUY MARKET" : "SELL MARKET");
}

//+------------------------------------------------------------------+
//| Day/session/order logic                                           |
//+------------------------------------------------------------------+
void RefreshDay()
{
   datetime d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(d1 <= 0)
      return;

   if(d1 == g_dayStart)
      return;

   g_dayStart = d1;
   g_buyHandledMemory = false;
   g_sellHandledMemory = false;
   g_lastPlacementTry = 0;

   if(InpDeleteOldPendingOrdersNewDay)
      DeleteOldPendings();

   double ph = iHigh(_Symbol, PERIOD_D1, 1);
   double pl = iLow(_Symbol, PERIOD_D1, 1);

   SetStatus("New D1 day. Previous high=" + DoubleToString(ph, _Digits) +
             " previous low=" + DoubleToString(pl, _Digits) +
             " spread=" + (string)SpreadPoints() + " points");
}

void TryPlaceDailyOrders()
{
   if(g_dayStart <= 0)
      return;

   datetime nowTime = TimeCurrent();
   if(g_lastPlacementTry > 0 && (nowTime - g_lastPlacementTry) < InpMinSecondsBetweenRetries)
      return;
   g_lastPlacementTry = nowTime;

   if(Bars(_Symbol, PERIOD_D1) < 3)
   {
      SetStatus("Waiting: not enough D1 bars for previous-day high/low.");
      return;
   }

   if(AccountInfoDouble(ACCOUNT_BALANCE) <= 0.0)
   {
      SetStatus("NO TRADES POSSIBLE: account/tester balance is 0. Set Strategy Tester Deposit to 10000 USD or more.");
      return;
   }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      SetStatus("Trading is not allowed in terminal. Enable Algo Trading / tester trade permissions.");
      return;
   }

   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      SetStatus("Trading is not allowed for this EA. In Inputs/Common allow algo trading.");
      return;
   }

   if(!TradingDayAllowed(g_dayStart))
   {
      SetStatus("No orders today: weekday disabled by inputs.");
      return;
   }

   if(InpMaxSpreadPoints > 0 && SpreadPoints() > InpMaxSpreadPoints)
   {
      SetStatus("Spread blocked orders. spread=" + (string)SpreadPoints() + " max=" + (string)InpMaxSpreadPoints);
      return;
   }

   MqlTick tick;
   if(!GetTick(tick))
      return;

   double prevHigh = iHigh(_Symbol, PERIOD_D1, 1);
   double prevLow  = iLow(_Symbol, PERIOD_D1, 1);
   if(prevHigh <= 0.0 || prevLow <= 0.0 || prevHigh <= prevLow)
   {
      SetStatus("Invalid previous D1 data. high=" + DoubleToString(prevHigh, _Digits) + " low=" + DoubleToString(prevLow, _Digits));
      return;
   }

   double offset  = (double)InpEntryOffsetPoints * _Point;
   double minDist = BrokerMinStopDistancePrice();
   double rrDist  = SLTPDistancePrice();

   // BUY side: previous day high breakout
   if(InpPlaceBuySide && !BuySideHandledToday())
   {
      double entry = NormalizePrice(prevHigh + offset);
      bool levelAlreadyBrokenOrTooClose = (entry <= tick.ask + minDist);

      if(levelAlreadyBrokenOrTooClose && InpIfLevelAlreadyBroken == LEVEL_SKIP_V3)
      {
         SetStatus("BUY skipped: PDH already broken/too close. entry=" + DoubleToString(entry, _Digits) + " ask=" + DoubleToString(tick.ask, _Digits));
      }
      else if(levelAlreadyBrokenOrTooClose && InpIfLevelAlreadyBroken == LEVEL_MARKET_ENTRY_V3)
      {
         double openPrice = tick.ask;
         double sl = NormalizePrice(openPrice - rrDist);
         double tp = NormalizePrice(openPrice + rrDist);
         double lots = CalculateLots(openPrice, sl);
         if(lots > 0.0 && SendMarketOrder(true, sl, tp, lots))
            g_buyHandledMemory = true;
      }
      else
      {
         if(levelAlreadyBrokenOrTooClose)
            entry = NormalizePrice(tick.ask + minDist);

         double sl = NormalizePrice(entry - rrDist);
         double tp = NormalizePrice(entry + rrDist);
         double lots = CalculateLots(entry, sl);
         if(lots > 0.0 && SendPendingStop(true, entry, sl, tp, lots))
            g_buyHandledMemory = true;
      }
   }

   // SELL side: previous day low breakout
   if(InpPlaceSellSide && !SellSideHandledToday())
   {
      double entry = NormalizePrice(prevLow - offset);
      bool levelAlreadyBrokenOrTooClose = (entry >= tick.bid - minDist);

      if(levelAlreadyBrokenOrTooClose && InpIfLevelAlreadyBroken == LEVEL_SKIP_V3)
      {
         SetStatus("SELL skipped: PDL already broken/too close. entry=" + DoubleToString(entry, _Digits) + " bid=" + DoubleToString(tick.bid, _Digits));
      }
      else if(levelAlreadyBrokenOrTooClose && InpIfLevelAlreadyBroken == LEVEL_MARKET_ENTRY_V3)
      {
         double openPrice = tick.bid;
         double sl = NormalizePrice(openPrice + rrDist);
         double tp = NormalizePrice(openPrice - rrDist);
         double lots = CalculateLots(openPrice, sl);
         if(lots > 0.0 && SendMarketOrder(false, sl, tp, lots))
            g_sellHandledMemory = true;
      }
      else
      {
         if(levelAlreadyBrokenOrTooClose)
            entry = NormalizePrice(tick.bid - minDist);

         double sl = NormalizePrice(entry + rrDist);
         double tp = NormalizePrice(entry - rrDist);
         double lots = CalculateLots(entry, sl);
         if(lots > 0.0 && SendPendingStop(false, entry, sl, tp, lots))
            g_sellHandledMemory = true;
      }
   }
}

//+------------------------------------------------------------------+
//| Position management                                               |
//+------------------------------------------------------------------+
bool ModifyPositionSLTP(const ulong positionTicket, const double sl, const double tp)
{
   MqlTradeRequest req;
   MqlTradeResult  res;
   ZeroMemory(req);
   ZeroMemory(res);

   req.action   = TRADE_ACTION_SLTP;
   req.position = positionTicket;
   req.symbol   = _Symbol;
   req.magic    = InpMagicNumber;
   req.sl       = NormalizePrice(sl);
   req.tp       = NormalizePrice(tp);

   ResetLastError();
   bool ok = OrderSend(req, res);
   if(!ok || res.retcode != TRADE_RETCODE_DONE)
   {
      SetStatus("Trail/BE SL modify failed. position=" + (string)positionTicket +
                " retcode=" + (string)res.retcode + " " + res.comment +
                " err=" + (string)GetLastError());
      return false;
   }

   return true;
}

void ManagePositions()
{
   if(!InpUseBreakEven && !InpUseTrailingStop)
      return;

   MqlTick tick;
   if(!GetTick(tick))
      return;

   double minDist    = BrokerMinStopDistancePrice();
   double beStart    = (double)InpBreakEvenStartPoints * _Point;
   double beLock     = (double)InpBreakEvenLockPoints * _Point;
   double trailStart = (double)InpTrailStartPoints * _Point;
   double trailDist  = MathMax((double)InpTrailDistancePoints * _Point, minDist);
   double trailStep  = MathMax((double)InpTrailStepPoints * _Point, _Point);

   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double oldSL     = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      double newSL     = oldSL;

      if(type == POSITION_TYPE_BUY)
      {
         double profitDist = tick.bid - openPrice;

         if(InpUseBreakEven && profitDist >= beStart)
         {
            double beSL = NormalizePrice(openPrice + beLock);
            if((newSL <= 0.0 || beSL > newSL) && beSL <= tick.bid - minDist)
               newSL = beSL;
         }

         if(InpUseTrailingStop && profitDist >= trailStart)
         {
            double trSL = NormalizePrice(tick.bid - trailDist);
            if((newSL <= 0.0 || trSL > newSL + trailStep) && trSL <= tick.bid - minDist)
               newSL = trSL;
         }

         if(newSL > 0.0 && (oldSL <= 0.0 || newSL > oldSL + trailStep))
            ModifyPositionSLTP(ticket, newSL, tp);
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double profitDist = openPrice - tick.ask;

         if(InpUseBreakEven && profitDist >= beStart)
         {
            double beSL = NormalizePrice(openPrice - beLock);
            if((newSL <= 0.0 || beSL < newSL) && beSL >= tick.ask + minDist)
               newSL = beSL;
         }

         if(InpUseTrailingStop && profitDist >= trailStart)
         {
            double trSL = NormalizePrice(tick.ask + trailDist);
            if((newSL <= 0.0 || trSL < newSL - trailStep) && trSL >= tick.ask + minDist)
               newSL = trSL;
         }

         if(newSL > 0.0 && (oldSL <= 0.0 || newSL < oldSL - trailStep))
            ModifyPositionSLTP(ticket, newSL, tp);
      }
   }
}

//+------------------------------------------------------------------+
//| UI                                                                |
//+------------------------------------------------------------------+
void ShowComment()
{
   if(!InpChartComment)
      return;

   double ph = iHigh(_Symbol, PERIOD_D1, 1);
   double pl = iLow(_Symbol, PERIOD_D1, 1);
   long tradeMode = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE);

   Comment(
      InpEAName, "\n",
      "Symbol: ", _Symbol, "  Digits: ", _Digits, "  Point: ", DoubleToString(_Point, _Digits), "\n",
      "Balance: ", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
      "  Equity: ", DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
      "  FreeMargin: ", DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2), "\n",
      "D1 day: ", TimeToString(g_dayStart, TIME_DATE|TIME_MINUTES),
      "  PDH: ", DoubleToString(ph, _Digits), "  PDL: ", DoubleToString(pl, _Digits), "\n",
      "Spread: ", SpreadPoints(), " points  StopsLevel: ", (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
      "  FreezeLevel: ", (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL),
      "  TradeMode: ", (string)tradeMode, "\n",
      "Buy handled: ", (BuySideHandledToday() ? "yes" : "no"),
      "  Sell handled: ", (SellSideHandledToday() ? "yes" : "no"), "\n",
      "Status: ", g_status
   );
}

//+------------------------------------------------------------------+
//| MT5 events                                                        |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("---------------- ", InpEAName, " init ----------------");
   Print("Symbol=", _Symbol,
         " digits=", _Digits,
         " point=", DoubleToString(_Point, _Digits),
         " tick_size=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), _Digits),
         " tick_value=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE), 4),
         " minLot=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), 2),
         " maxLot=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), 2),
         " step=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), 2),
         " stopLevel=", (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
         " freezeLevel=", (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL),
         " fillingMode=", (int)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE),
         " tradeMode=", (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE));
   Print("Tester/account balance=", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
         " equity=", DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
         " freeMargin=", DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2));
   Print("For backtests, use Every tick or 1 minute OHLC. Do not use Open prices only for this stop-order breakout EA.");
   Print("------------------------------------------------------------");

   if(InpTimerSeconds > 0)
      EventSetTimer(InpTimerSeconds);

   RefreshDay();
   TryPlaceDailyOrders();
   ManagePositions();
   ShowComment();

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

void OnTick()
{
   RefreshDay();
   TryPlaceDailyOrders();
   ManagePositions();
   ShowComment();
}

void OnTimer()
{
   RefreshDay();
   TryPlaceDailyOrders();
   ManagePositions();
   ShowComment();
}
//+------------------------------------------------------------------+
