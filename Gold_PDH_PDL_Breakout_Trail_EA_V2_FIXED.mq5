//+------------------------------------------------------------------+
//| Gold_PDH_PDL_Breakout_Trail_EA_V2_FIXED.mq5                      |
//| Previous-day high/low breakout EA for MetaTrader 5                |
//| Places Buy Stop at previous D1 high and Sell Stop at previous     |
//| D1 low, then aggressively trails activated positions.             |
//| V2 fixes: spread filter disabled by default, GTC pending orders,   |
//| repeated same-day placement attempts, no duplicate order replace   |
//| after a pending order has triggered, and clearer journal logs.     |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"
#property description "Gold previous-day high/low breakout EA with aggressive trailing. V2 fixed for Exness/3-digit gold symbols."

#include <Trade/Trade.mqh>

CTrade trade;

//----------------------------- ENUMS --------------------------------
enum ENUM_LOT_MODE
{
   LOT_FIXED        = 0,
   LOT_RISK_PERCENT = 1
};

enum ENUM_SLTP_MODE
{
   SLTP_FIXED_PRICE  = 0,   // Gold-style price distance. Example: 25.00 = $25.00 XAUUSD move
   SLTP_FIXED_POINTS = 1,   // Broker points. Example on 3-digit XAUUSDm: 25000 points = $25.00
   SLTP_DAILY_ATR    = 2    // Daily ATR multiplied by ATR multiplier
};

enum ENUM_BROKEN_LEVEL_MODE
{
   BROKEN_SKIP_LEVEL              = 0, // Strict video mode: skip if PDH/PDL is already broken/invalid
   BROKEN_PLACE_NEAREST_VALID_STOP = 1  // Backtest/live-safe: move pending stop to nearest valid stop distance
};

//----------------------------- INPUTS -------------------------------
input string                 InpEAName                  = "PDH/PDL Gold Breakout Trail V2";
input ulong                  InpMagicNumber             = 26062402;

// Lots / risk
input ENUM_LOT_MODE          InpLotMode                 = LOT_FIXED;
input double                 InpFixedLots               = 0.10;
input double                 InpRiskPercent             = 2.00;

// SL/TP: transcript describes default 1:1, then aggressive trailing
input ENUM_SLTP_MODE         InpSLTPMode                = SLTP_FIXED_PRICE;
input double                 InpSLTPPriceDistance       = 25.00;   // Gold price units, e.g. 25.00 dollars
input int                    InpSLTPPoints              = 25000;   // 3-digit XAUUSDm: 25000 = $25.00
input int                    InpATRPeriod               = 14;
input double                 InpATRMultiplier           = 0.35;

// Entry orders
input bool                   InpPlaceBuyStop            = true;
input bool                   InpPlaceSellStop           = true;
input int                    InpEntryOffsetPoints       = 10;      // 3-digit gold: 10 points = $0.01
input ENUM_BROKEN_LEVEL_MODE InpBrokenLevelMode         = BROKEN_PLACE_NEAREST_VALID_STOP;
input bool                   InpDeleteOldPendingsNewDay = true;
input int                    InpPendingExpiryHours      = 0;       // 0 = GTC. Recommended for tester; old pendings deleted next D1

// Filters
input int                    InpMaxSpreadPoints         = 0;       // 0 = disabled. Exness XAUUSDm often has >120 points spread
input bool                   InpTradeMonday             = true;
input bool                   InpTradeTuesday            = true;
input bool                   InpTradeWednesday          = true;
input bool                   InpTradeThursday           = true;
input bool                   InpTradeFriday             = true;

// Aggressive management after entry
input bool                   InpUseBreakEven            = true;
input int                    InpBreakEvenStartPoints    = 100;     // 3-digit gold: 100 points = $0.10
input int                    InpBreakEvenLockPoints     = 20;      // 3-digit gold: 20 points = $0.02
input bool                   InpUseTrailingStop         = true;
input int                    InpTrailStartPoints        = 120;     // start trailing very early
input int                    InpTrailDistancePoints     = 80;      // tight trailing distance; auto-raised if broker stop level is bigger
input int                    InpTrailStepPoints         = 10;
input int                    InpTimerSeconds            = 1;

// Debug / safety
input bool                   InpShowChartComment        = true;
input bool                   InpVerboseLogs             = true;

//----------------------------- GLOBALS ------------------------------
datetime g_currentD1Time = 0;
int      g_atrHandle     = INVALID_HANDLE;
string   g_lastStatus    = "Starting";

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
void Log(string msg)
{
   g_lastStatus = msg;
   if(InpVerboseLogs)
      Print(InpEAName, ": ", msg);
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

double NormalizeVolume(double lots)
{
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0.0)
      step = 0.01;
   if(min_lot <= 0.0)
      min_lot = step;
   if(max_lot <= 0.0)
      max_lot = lots;

   lots = MathMax(min_lot, MathMin(max_lot, lots));
   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, VolumeDigits());

   if(lots < min_lot)
      lots = min_lot;

   return lots;
}

double NormalizePrice(double price)
{
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_size <= 0.0)
      tick_size = _Point;

   return NormalizeDouble(MathRound(price / tick_size) * tick_size, _Digits);
}

int CurrentSpreadPoints()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return 999999;

   return (int)MathRound((tick.ask - tick.bid) / _Point);
}

double MinStopDistancePrice()
{
   long stops_level  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   long min_points   = (long)MathMax((double)stops_level, (double)freeze_level);

   return ((double)min_points + 1.0) * _Point;
}

bool IsAllowedTradingDay(datetime d1_time)
{
   MqlDateTime dt;
   TimeToStruct(d1_time, dt);

   if(dt.day_of_week == 1) return InpTradeMonday;
   if(dt.day_of_week == 2) return InpTradeTuesday;
   if(dt.day_of_week == 3) return InpTradeWednesday;
   if(dt.day_of_week == 4) return InpTradeThursday;
   if(dt.day_of_week == 5) return InpTradeFriday;

   return false;
}

double GetSLTPDistancePrice()
{
   double distance = InpSLTPPriceDistance;

   if(InpSLTPMode == SLTP_FIXED_POINTS)
      distance = (double)InpSLTPPoints * _Point;
   else if(InpSLTPMode == SLTP_DAILY_ATR)
   {
      double atr_buffer[];
      ArraySetAsSeries(atr_buffer, true);

      if(g_atrHandle != INVALID_HANDLE && CopyBuffer(g_atrHandle, 0, 1, 1, atr_buffer) == 1 && atr_buffer[0] > 0.0)
         distance = atr_buffer[0] * InpATRMultiplier;
      else
         distance = InpSLTPPriceDistance;
   }

   return MathMax(distance, MinStopDistancePrice());
}

double CalculateLots(double entry_price, double sl_price)
{
   if(InpLotMode == LOT_FIXED)
      return NormalizeVolume(InpFixedLots);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0)
   {
      Log("Account equity is 0. In Strategy Tester, set a real initial deposit such as 10000 USD.");
      return 0.0;
   }

   double risk_money = equity * InpRiskPercent / 100.0;
   double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);

   if(tick_size <= 0.0 || tick_value <= 0.0 || risk_money <= 0.0)
      return NormalizeVolume(InpFixedLots);

   double price_risk   = MathAbs(entry_price - sl_price);
   double ticks_risk   = price_risk / tick_size;
   double loss_per_lot = ticks_risk * tick_value;

   if(loss_per_lot <= 0.0)
      return NormalizeVolume(InpFixedLots);

   return NormalizeVolume(risk_money / loss_per_lot);
}

bool IsOurActivePendingType(ENUM_ORDER_TYPE order_type)
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;

      if(!OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE) == order_type)
         return true;
   }
   return false;
}

bool WasPendingTypePlacedToday(ENUM_ORDER_TYPE order_type, datetime day_start)
{
   if(IsOurActivePendingType(order_type))
      return true;

   datetime now_time = TimeCurrent();
   if(now_time <= 0)
      now_time = day_start + 86400;

   if(!HistorySelect(day_start, now_time + 86400))
      return false;

   for(int i = HistoryOrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = HistoryOrderGetTicket(i);
      if(ticket == 0)
         continue;

      if(HistoryOrderGetString(ticket, ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryOrderGetInteger(ticket, ORDER_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_ORDER_TYPE)HistoryOrderGetInteger(ticket, ORDER_TYPE) != order_type)
         continue;

      datetime setup_time = (datetime)HistoryOrderGetInteger(ticket, ORDER_TIME_SETUP);
      if(setup_time >= day_start)
         return true;
   }

   return false;
}

void DeleteThisEAPendingOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;

      if(!OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;

      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_SELL_STOP)
      {
         trade.SetExpertMagicNumber(InpMagicNumber);
         if(!trade.OrderDelete(ticket))
            Log("Failed to delete old pending order #" + (string)ticket + ". Retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription());
      }
   }
}

//+------------------------------------------------------------------+
//| Day preparation                                                   |
//+------------------------------------------------------------------+
void PrepareNewDailySession()
{
   datetime d1_time = iTime(_Symbol, PERIOD_D1, 0);
   if(d1_time <= 0)
      return;

   if(d1_time == g_currentD1Time)
      return;

   g_currentD1Time = d1_time;

   if(InpDeleteOldPendingsNewDay)
      DeleteThisEAPendingOrders();

   double prev_high = iHigh(_Symbol, PERIOD_D1, 1);
   double prev_low  = iLow(_Symbol, PERIOD_D1, 1);

   Log("New D1 session. Previous high=" + DoubleToString(prev_high, _Digits) +
       " previous low=" + DoubleToString(prev_low, _Digits) +
       " spread=" + (string)CurrentSpreadPoints() + " points.");
}

//+------------------------------------------------------------------+
//| Place one pending order                                           |
//+------------------------------------------------------------------+
bool PlaceOnePending(ENUM_ORDER_TYPE order_type, double base_level, datetime day_start)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
   {
      Log("No tick available yet. Waiting.");
      return false;
   }

   if(InpMaxSpreadPoints > 0 && CurrentSpreadPoints() > InpMaxSpreadPoints)
   {
      Log("Spread filter blocked placement. Spread=" + (string)CurrentSpreadPoints() +
          " max=" + (string)InpMaxSpreadPoints + ". Set InpMaxSpreadPoints=0 to disable.");
      return false;
   }

   double offset   = (double)InpEntryOffsetPoints * _Point;
   double min_stop = MinStopDistancePrice();
   double dist     = GetSLTPDistancePrice();

   double entry = 0.0;
   double sl    = 0.0;
   double tp    = 0.0;
   string comment = "";

   if(order_type == ORDER_TYPE_BUY_STOP)
   {
      entry = NormalizePrice(base_level + offset);

      if(entry <= tick.ask + min_stop)
      {
         if(InpBrokenLevelMode == BROKEN_SKIP_LEVEL)
         {
            Log("BuyStop skipped: PDH is already broken or too close. PDH entry=" + DoubleToString(entry, _Digits) +
                " ask=" + DoubleToString(tick.ask, _Digits));
            return false;
         }
         entry = NormalizePrice(tick.ask + min_stop);
      }

      sl = NormalizePrice(entry - dist);
      tp = NormalizePrice(entry + dist);
      comment = InpEAName + " BUY PDH";
   }
   else if(order_type == ORDER_TYPE_SELL_STOP)
   {
      entry = NormalizePrice(base_level - offset);

      if(entry >= tick.bid - min_stop)
      {
         if(InpBrokenLevelMode == BROKEN_SKIP_LEVEL)
         {
            Log("SellStop skipped: PDL is already broken or too close. PDL entry=" + DoubleToString(entry, _Digits) +
                " bid=" + DoubleToString(tick.bid, _Digits));
            return false;
         }
         entry = NormalizePrice(tick.bid - min_stop);
      }

      sl = NormalizePrice(entry + dist);
      tp = NormalizePrice(entry - dist);
      comment = InpEAName + " SELL PDL";
   }
   else
      return false;

   double lots = CalculateLots(entry, sl);
   if(lots <= 0.0)
   {
      Log("Lot calculation returned 0. Check tester deposit, risk mode, and symbol tick value.");
      return false;
   }

   ENUM_ORDER_TYPE_TIME type_time = ORDER_TIME_GTC;
   datetime expiration = 0;
   if(InpPendingExpiryHours > 0)
   {
      type_time = ORDER_TIME_SPECIFIED;
      expiration = day_start + InpPendingExpiryHours * 3600;
      if(expiration <= TimeCurrent())
         expiration = TimeCurrent() + 3600;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(30);
   trade.SetTypeFillingBySymbol(_Symbol);

   ResetLastError();
   bool ok = false;
   if(order_type == ORDER_TYPE_BUY_STOP)
      ok = trade.BuyStop(lots, entry, _Symbol, sl, tp, type_time, expiration, comment);
   else
      ok = trade.SellStop(lots, entry, _Symbol, sl, tp, type_time, expiration, comment);

   if(ok)
   {
      Log((order_type == ORDER_TYPE_BUY_STOP ? "BuyStop" : "SellStop") +
          " placed. Lots=" + DoubleToString(lots, VolumeDigits()) +
          " entry=" + DoubleToString(entry, _Digits) +
          " SL=" + DoubleToString(sl, _Digits) +
          " TP=" + DoubleToString(tp, _Digits));
      return true;
   }

   Log((order_type == ORDER_TYPE_BUY_STOP ? "BuyStop" : "SellStop") +
       " failed. Retcode=" + (string)trade.ResultRetcode() + " " + trade.ResultRetcodeDescription() +
       " LastError=" + (string)GetLastError() +
       " lots=" + DoubleToString(lots, VolumeDigits()) +
       " entry=" + DoubleToString(entry, _Digits) +
       " SL=" + DoubleToString(sl, _Digits) +
       " TP=" + DoubleToString(tp, _Digits));

   return false;
}

//+------------------------------------------------------------------+
//| Ensure today's 2 orders exist / existed                           |
//+------------------------------------------------------------------+
void EnsureDailyBreakoutOrders()
{
   if(g_currentD1Time <= 0)
      return;

   if(Bars(_Symbol, PERIOD_D1) < 3)
   {
      Log("Not enough D1 bars yet to read previous-day high/low.");
      return;
   }

   if(AccountInfoDouble(ACCOUNT_BALANCE) <= 0.0)
   {
      Log("Account balance is 0. In Strategy Tester set Deposit to something like 10000 USD. The screenshot shows Balance 0.00.");
      return;
   }

   if(!IsAllowedTradingDay(g_currentD1Time))
   {
      Log("Trading disabled for this weekday.");
      return;
   }

   double prev_high = iHigh(_Symbol, PERIOD_D1, 1);
   double prev_low  = iLow(_Symbol, PERIOD_D1, 1);

   if(prev_high <= 0.0 || prev_low <= 0.0 || prev_high <= prev_low)
   {
      Log("Invalid previous D1 high/low. High=" + DoubleToString(prev_high, _Digits) +
          " low=" + DoubleToString(prev_low, _Digits));
      return;
   }

   if(InpPlaceBuyStop && !WasPendingTypePlacedToday(ORDER_TYPE_BUY_STOP, g_currentD1Time))
      PlaceOnePending(ORDER_TYPE_BUY_STOP, prev_high, g_currentD1Time);

   if(InpPlaceSellStop && !WasPendingTypePlacedToday(ORDER_TYPE_SELL_STOP, g_currentD1Time))
      PlaceOnePending(ORDER_TYPE_SELL_STOP, prev_low, g_currentD1Time);
}

//+------------------------------------------------------------------+
//| Position modification / trailing                                  |
//+------------------------------------------------------------------+
bool ModifyPositionStops(ulong position_ticket, double new_sl, double current_tp)
{
   MqlTradeRequest request;
   MqlTradeResult  result;
   ZeroMemory(request);
   ZeroMemory(result);

   request.action   = TRADE_ACTION_SLTP;
   request.position = position_ticket;
   request.symbol   = _Symbol;
   request.magic    = InpMagicNumber;
   request.sl       = new_sl;
   request.tp       = current_tp;

   ResetLastError();
   bool ok = OrderSend(request, result);

   if(!ok || (result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED))
   {
      Log("SL modify failed for position #" + (string)position_ticket +
          ". Retcode=" + (string)result.retcode +
          " comment=" + result.comment +
          " error=" + (string)GetLastError());
      return false;
   }

   return true;
}

void ManageOpenPositions()
{
   if(!InpUseBreakEven && !InpUseTrailingStop)
      return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   double min_stop     = MinStopDistancePrice();
   double be_start     = (double)InpBreakEvenStartPoints * _Point;
   double be_lock      = (double)InpBreakEvenLockPoints * _Point;
   double trail_start  = (double)InpTrailStartPoints * _Point;
   double trail_dist   = MathMax((double)InpTrailDistancePoints * _Point, min_stop);
   double trail_step   = MathMax((double)InpTrailStepPoints * _Point, _Point);

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
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl = PositionGetDouble(POSITION_SL);
      double current_tp = PositionGetDouble(POSITION_TP);
      double desired_sl = current_sl;

      if(type == POSITION_TYPE_BUY)
      {
         double profit_price = tick.bid - open_price;

         if(InpUseBreakEven && profit_price >= be_start)
         {
            double be_sl = NormalizePrice(open_price + be_lock);
            if((desired_sl == 0.0 || be_sl > desired_sl) && be_sl <= tick.bid - min_stop)
               desired_sl = be_sl;
         }

         if(InpUseTrailingStop && profit_price >= trail_start)
         {
            double trail_sl = NormalizePrice(tick.bid - trail_dist);
            if((desired_sl == 0.0 || trail_sl > desired_sl + trail_step) && trail_sl <= tick.bid - min_stop)
               desired_sl = trail_sl;
         }

         desired_sl = NormalizePrice(desired_sl);
         if(desired_sl > 0.0 && (current_sl == 0.0 || desired_sl > current_sl + trail_step))
            ModifyPositionStops(ticket, desired_sl, current_tp);
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double profit_price = open_price - tick.ask;

         if(InpUseBreakEven && profit_price >= be_start)
         {
            double be_sl = NormalizePrice(open_price - be_lock);
            if((desired_sl == 0.0 || be_sl < desired_sl) && be_sl >= tick.ask + min_stop)
               desired_sl = be_sl;
         }

         if(InpUseTrailingStop && profit_price >= trail_start)
         {
            double trail_sl = NormalizePrice(tick.ask + trail_dist);
            if((desired_sl == 0.0 || trail_sl < desired_sl - trail_step) && trail_sl >= tick.ask + min_stop)
               desired_sl = trail_sl;
         }

         desired_sl = NormalizePrice(desired_sl);
         if(desired_sl > 0.0 && (current_sl == 0.0 || desired_sl < current_sl - trail_step))
            ModifyPositionStops(ticket, desired_sl, current_tp);
      }
   }
}

//+------------------------------------------------------------------+
//| Chart status                                                      |
//+------------------------------------------------------------------+
void UpdateChartComment()
{
   if(!InpShowChartComment)
      return;

   double prev_high = iHigh(_Symbol, PERIOD_D1, 1);
   double prev_low  = iLow(_Symbol, PERIOD_D1, 1);

   Comment(
      InpEAName, "\n",
      "Symbol: ", _Symbol, "  Digits: ", _Digits, "  Point: ", DoubleToString(_Point, _Digits), "\n",
      "D1: ", TimeToString(g_currentD1Time, TIME_DATE|TIME_MINUTES), "\n",
      "PDH: ", DoubleToString(prev_high, _Digits), "  PDL: ", DoubleToString(prev_low, _Digits), "\n",
      "Spread: ", CurrentSpreadPoints(), " points  MaxSpread: ", InpMaxSpreadPoints, "\n",
      "Balance: ", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
      "  Equity: ", DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2), "\n",
      "Status: ", g_lastStatus
   );
}

//+------------------------------------------------------------------+
//| MT5 events                                                        |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(30);
   trade.SetTypeFillingBySymbol(_Symbol);

   if(InpSLTPMode == SLTP_DAILY_ATR)
   {
      g_atrHandle = iATR(_Symbol, PERIOD_D1, InpATRPeriod);
      if(g_atrHandle == INVALID_HANDLE)
      {
         Print("Failed to create ATR handle. Error: ", GetLastError());
         return INIT_FAILED;
      }
   }

   if(InpTimerSeconds > 0)
      EventSetTimer(InpTimerSeconds);

   Print("------------------------------------------------------------");
   Print(InpEAName, " initialized on ", _Symbol,
         ". Previous-day high/low breakout, 1:1 SL/TP, aggressive trailing.");
   Print("Symbol info: digits=", _Digits,
         " point=", DoubleToString(_Point, _Digits),
         " tick_size=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), _Digits),
         " min_lot=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN), 2),
         " max_lot=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), 2),
         " stops_level=", (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
         " spread_now=", CurrentSpreadPoints(), " points");
   Print("IMPORTANT: if Strategy Tester shows Balance 0.00, set a non-zero initial Deposit before testing.");
   Print("------------------------------------------------------------");

   g_currentD1Time = 0;
   PrepareNewDailySession();
   EnsureDailyBreakoutOrders();
   UpdateChartComment();

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");

   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);
}

void OnTick()
{
   PrepareNewDailySession();
   EnsureDailyBreakoutOrders();
   ManageOpenPositions();
   UpdateChartComment();
}

void OnTimer()
{
   PrepareNewDailySession();
   EnsureDailyBreakoutOrders();
   ManageOpenPositions();
   UpdateChartComment();
}
//+------------------------------------------------------------------+
