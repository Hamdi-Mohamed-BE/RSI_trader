//+------------------------------------------------------------------+
//| Gold_PDH_PDL_Breakout_Trail_EA.mq5                               |
//| Previous-day high/low breakout EA for MetaTrader 5                |
//| Logic: places Buy Stop at previous D1 high and Sell Stop at       |
//| previous D1 low, then aggressively trails activated positions.    |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Previous-day high/low breakout EA with aggressive trailing stop management."

#include <Trade/Trade.mqh>

CTrade trade;

//-------------------------- INPUTS ----------------------------------
enum ENUM_LOT_MODE
{
   LOT_FIXED       = 0,
   LOT_RISK_PERCENT = 1
};

enum ENUM_SLTP_MODE
{
   SLTP_FIXED_PRICE  = 0,   // Gold-style price distance, e.g. 25.00 = $25 move on XAUUSD
   SLTP_FIXED_POINTS = 1,   // Raw broker points
   SLTP_DAILY_ATR    = 2    // Daily ATR multiplied by ATR multiplier
};

input string          InpEAName                 = "PDH/PDL Gold Breakout Trail";
input ulong           InpMagicNumber            = 24062401;
input ENUM_LOT_MODE   InpLotMode                = LOT_RISK_PERCENT;
input double          InpFixedLots              = 0.10;
input double          InpRiskPercent            = 2.00;

input ENUM_SLTP_MODE  InpSLTPMode               = SLTP_FIXED_PRICE;
input double          InpSLTPPriceDistance      = 25.00;     // $25 SL and $25 TP by default on gold
input int             InpSLTPPoints             = 2500;      // Used only if SLTP_FIXED_POINTS
input int             InpATRPeriod              = 14;        // Used only if SLTP_DAILY_ATR
input double          InpATRMultiplier          = 0.35;      // Used only if SLTP_DAILY_ATR

input int             InpEntryOffsetPoints      = 10;        // BuyStop = PDH + offset, SellStop = PDL - offset
input int             InpMaxSpreadPoints        = 120;       // Skip placing orders if spread is wider
input int             InpDeviationPoints        = 30;
input bool            InpPlaceBuyStop           = true;
input bool            InpPlaceSellStop          = true;
input bool            InpCancelOldPendingsOnNewDay = true;
input bool            InpSkipIfLevelAlreadyBroken  = true;
input int             InpPendingExpiryHours     = 23;        // 0 = GTC, otherwise expires same day

// Aggressive management after entry
input bool            InpUseBreakEven           = true;
input int             InpBreakEvenStartPoints   = 100;       // Move SL to BE after this profit
input int             InpBreakEvenLockPoints    = 20;        // Lock this many points beyond entry
input bool            InpUseTrailingStop        = true;
input int             InpTrailStartPoints       = 120;       // Start trailing very early
input int             InpTrailDistancePoints    = 80;        // Tight/aggressive distance
input int             InpTrailStepPoints        = 10;        // Modify only if SL improves by step
input int             InpTimerSeconds           = 1;         // 1-second management on VPS

// Trading-day filter, based on broker server daily candles
input bool            InpTradeMonday            = true;
input bool            InpTradeTuesday           = true;
input bool            InpTradeWednesday         = true;
input bool            InpTradeThursday          = true;
input bool            InpTradeFriday            = true;

//-------------------------- GLOBALS ---------------------------------
datetime g_lastD1BarTime = 0;
int      g_atrHandle     = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Normalize price to symbol tick size                               |
//+------------------------------------------------------------------+
double NormalizePrice(const double price)
{
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_size <= 0.0)
      tick_size = _Point;

   return NormalizeDouble(MathRound(price / tick_size) * tick_size, _Digits);
}

//+------------------------------------------------------------------+
//| Volume digits from volume step                                    |
//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
//| Normalize lots to broker min/max/step                             |
//+------------------------------------------------------------------+
double NormalizeVolume(double lots)
{
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0.0)
      step = 0.01;

   lots = MathMax(min_lot, MathMin(max_lot, lots));
   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, VolumeDigits());

   if(lots < min_lot)
      lots = min_lot;

   return lots;
}

//+------------------------------------------------------------------+
//| Current spread in broker points                                   |
//+------------------------------------------------------------------+
int CurrentSpreadPoints()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return 999999;

   return (int)MathRound((tick.ask - tick.bid) / _Point);
}

//+------------------------------------------------------------------+
//| Minimum safe stop/freeze distance in price units                  |
//+------------------------------------------------------------------+
double MinStopDistancePrice()
{
   long stops_level  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   long min_points   = MathMax(stops_level, freeze_level);

   return (double)min_points * _Point;
}

//+------------------------------------------------------------------+
//| Check if daily candle day is allowed                              |
//+------------------------------------------------------------------+
bool IsAllowedTradingDay(datetime d1_time)
{
   MqlDateTime dt;
   TimeToStruct(d1_time, dt);

   // day_of_week: 0 Sunday, 1 Monday, ..., 6 Saturday
   if(dt.day_of_week == 1) return InpTradeMonday;
   if(dt.day_of_week == 2) return InpTradeTuesday;
   if(dt.day_of_week == 3) return InpTradeWednesday;
   if(dt.day_of_week == 4) return InpTradeThursday;
   if(dt.day_of_week == 5) return InpTradeFriday;

   return false;
}

//+------------------------------------------------------------------+
//| Read SL/TP distance in price units                                |
//+------------------------------------------------------------------+
double GetSLTPDistancePrice()
{
   double distance = InpSLTPPriceDistance;

   if(InpSLTPMode == SLTP_FIXED_POINTS)
      distance = (double)InpSLTPPoints * _Point;

   if(InpSLTPMode == SLTP_DAILY_ATR)
   {
      double atr_buffer[];
      ArraySetAsSeries(atr_buffer, true);

      if(g_atrHandle != INVALID_HANDLE && CopyBuffer(g_atrHandle, 0, 1, 1, atr_buffer) == 1 && atr_buffer[0] > 0.0)
         distance = atr_buffer[0] * InpATRMultiplier;
      else
         distance = InpSLTPPriceDistance;
   }

   double min_distance = MinStopDistancePrice() + _Point;
   return MathMax(distance, min_distance);
}

//+------------------------------------------------------------------+
//| Calculate lot size                                                 |
//+------------------------------------------------------------------+
double CalculateLots(const double entry_price, const double sl_price)
{
   if(InpLotMode == LOT_FIXED)
      return NormalizeVolume(InpFixedLots);

   double equity      = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money  = equity * InpRiskPercent / 100.0;
   double tick_size   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);

   if(tick_size <= 0.0 || tick_value <= 0.0 || risk_money <= 0.0)
      return NormalizeVolume(InpFixedLots);

   double price_risk  = MathAbs(entry_price - sl_price);
   double ticks_risk  = price_risk / tick_size;
   double loss_per_lot = ticks_risk * tick_value;

   if(loss_per_lot <= 0.0)
      return NormalizeVolume(InpFixedLots);

   double lots = risk_money / loss_per_lot;
   return NormalizeVolume(lots);
}

//+------------------------------------------------------------------+
//| Does this EA already have a pending order of this type?            |
//+------------------------------------------------------------------+
bool HasPendingOrder(const ENUM_ORDER_TYPE order_type)
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

//+------------------------------------------------------------------+
//| Delete all pending orders from this EA on this symbol              |
//+------------------------------------------------------------------+
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
         if(!trade.OrderDelete(ticket))
            Print("Failed to delete old pending order #", ticket, ". Error: ", GetLastError());
      }
   }
}

//+------------------------------------------------------------------+
//| Place daily breakout orders                                       |
//+------------------------------------------------------------------+
void PlaceDailyBreakoutOrders()
{
   if(Bars(_Symbol, PERIOD_D1) < 3)
   {
      Print("Not enough D1 bars to read previous day high/low.");
      return;
   }

   datetime current_d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(!IsAllowedTradingDay(current_d1))
   {
      Print("Trading day is disabled by filter.");
      return;
   }

   if(CurrentSpreadPoints() > InpMaxSpreadPoints)
   {
      Print("Spread too high. Spread points: ", CurrentSpreadPoints(), " / max: ", InpMaxSpreadPoints);
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
   {
      Print("Could not read current symbol tick.");
      return;
   }

   if(InpCancelOldPendingsOnNewDay)
      DeleteThisEAPendingOrders();

   double prev_high = iHigh(_Symbol, PERIOD_D1, 1);
   double prev_low  = iLow(_Symbol, PERIOD_D1, 1);

   if(prev_high <= 0.0 || prev_low <= 0.0 || prev_high <= prev_low)
   {
      Print("Invalid previous D1 high/low. High: ", prev_high, " Low: ", prev_low);
      return;
   }

   double dist = GetSLTPDistancePrice();
   double offset = (double)InpEntryOffsetPoints * _Point;
   double min_stop = MinStopDistancePrice() + _Point;

   ENUM_ORDER_TYPE_TIME time_type = ORDER_TIME_GTC;
   datetime expiration = 0;

   if(InpPendingExpiryHours > 0)
   {
      time_type = ORDER_TIME_SPECIFIED;
      expiration = current_d1 + (InpPendingExpiryHours * 3600);
      if(expiration <= TimeCurrent())
         expiration = TimeCurrent() + (InpPendingExpiryHours * 3600);
   }

   // Buy Stop at previous-day high
   if(InpPlaceBuyStop && !HasPendingOrder(ORDER_TYPE_BUY_STOP))
   {
      double entry = NormalizePrice(prev_high + offset);

      if(InpSkipIfLevelAlreadyBroken && entry <= tick.ask + min_stop)
      {
         Print("BuyStop skipped because previous high level is already broken or too close. Entry: ", entry, " Ask: ", tick.ask);
      }
      else
      {
         if(entry <= tick.ask + min_stop)
            entry = NormalizePrice(tick.ask + min_stop);

         double sl = NormalizePrice(entry - dist);
         double tp = NormalizePrice(entry + dist);
         double lots = CalculateLots(entry, sl);

         trade.SetExpertMagicNumber(InpMagicNumber);
         trade.SetDeviationInPoints(InpDeviationPoints);

         bool ok = trade.BuyStop(lots, entry, _Symbol, sl, tp, time_type, expiration, InpEAName + " BUY PDH");
         if(ok)
            Print("BuyStop placed at PDH. Lots: ", lots, " Entry: ", entry, " SL: ", sl, " TP: ", tp);
         else
            Print("BuyStop failed. Retcode: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription(), " Error: ", GetLastError());
      }
   }

   // Sell Stop at previous-day low
   if(InpPlaceSellStop && !HasPendingOrder(ORDER_TYPE_SELL_STOP))
   {
      double entry = NormalizePrice(prev_low - offset);

      if(InpSkipIfLevelAlreadyBroken && entry >= tick.bid - min_stop)
      {
         Print("SellStop skipped because previous low level is already broken or too close. Entry: ", entry, " Bid: ", tick.bid);
      }
      else
      {
         if(entry >= tick.bid - min_stop)
            entry = NormalizePrice(tick.bid - min_stop);

         double sl = NormalizePrice(entry + dist);
         double tp = NormalizePrice(entry - dist);
         double lots = CalculateLots(entry, sl);

         trade.SetExpertMagicNumber(InpMagicNumber);
         trade.SetDeviationInPoints(InpDeviationPoints);

         bool ok = trade.SellStop(lots, entry, _Symbol, sl, tp, time_type, expiration, InpEAName + " SELL PDL");
         if(ok)
            Print("SellStop placed at PDL. Lots: ", lots, " Entry: ", entry, " SL: ", sl, " TP: ", tp);
         else
            Print("SellStop failed. Retcode: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription(), " Error: ", GetLastError());
      }
   }
}

//+------------------------------------------------------------------+
//| Modify SL/TP by position ticket                                   |
//+------------------------------------------------------------------+
bool ModifyPositionStops(const ulong position_ticket, const double new_sl, const double current_tp)
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
      Print("SL modification failed for position #", position_ticket,
            ". Retcode: ", result.retcode,
            " Comment: ", result.comment,
            " Error: ", GetLastError());
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Aggressively trail active positions                               |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   if(!InpUseBreakEven && !InpUseTrailingStop)
      return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   double min_stop = MinStopDistancePrice() + _Point;
   double step     = (double)InpTrailStepPoints * _Point;

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
         double profit_points = (tick.bid - open_price) / _Point;

         if(InpUseBreakEven && profit_points >= InpBreakEvenStartPoints)
         {
            double be_sl = NormalizePrice(open_price + ((double)InpBreakEvenLockPoints * _Point));
            if((current_sl == 0.0 || be_sl > desired_sl) && be_sl <= tick.bid - min_stop)
               desired_sl = be_sl;
         }

         if(InpUseTrailingStop && profit_points >= InpTrailStartPoints)
         {
            double trail_sl = NormalizePrice(tick.bid - ((double)InpTrailDistancePoints * _Point));
            if((current_sl == 0.0 || trail_sl > desired_sl + step) && trail_sl <= tick.bid - min_stop)
               desired_sl = trail_sl;
         }

         desired_sl = NormalizePrice(desired_sl);
         if(desired_sl > 0.0 && (current_sl == 0.0 || desired_sl > current_sl + step))
            ModifyPositionStops(ticket, desired_sl, current_tp);
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double profit_points = (open_price - tick.ask) / _Point;

         if(InpUseBreakEven && profit_points >= InpBreakEvenStartPoints)
         {
            double be_sl = NormalizePrice(open_price - ((double)InpBreakEvenLockPoints * _Point));
            if((current_sl == 0.0 || be_sl < desired_sl) && be_sl >= tick.ask + min_stop)
               desired_sl = be_sl;
         }

         if(InpUseTrailingStop && profit_points >= InpTrailStartPoints)
         {
            double trail_sl = NormalizePrice(tick.ask + ((double)InpTrailDistancePoints * _Point));
            if((current_sl == 0.0 || trail_sl < desired_sl - step) && trail_sl >= tick.ask + min_stop)
               desired_sl = trail_sl;
         }

         desired_sl = NormalizePrice(desired_sl);
         if(desired_sl > 0.0 && (current_sl == 0.0 || desired_sl < current_sl - step))
            ModifyPositionStops(ticket, desired_sl, current_tp);
      }
   }
}

//+------------------------------------------------------------------+
//| New daily candle detection                                        |
//+------------------------------------------------------------------+
void CheckNewDailyBar()
{
   datetime current_d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(current_d1 <= 0)
      return;

   if(current_d1 != g_lastD1BarTime)
   {
      g_lastD1BarTime = current_d1;
      Print("New D1 candle detected. Refreshing previous-day breakout orders.");
      PlaceDailyBreakoutOrders();
   }
}

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpDeviationPoints);

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

   g_lastD1BarTime = 0;
   CheckNewDailyBar();

   Print(InpEAName, " initialized on ", _Symbol,
         ". Logic: BuyStop at previous D1 high, SellStop at previous D1 low, 1:1 SL/TP, aggressive trailing.");

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();

   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);
}

//+------------------------------------------------------------------+
//| Expert tick                                                       |
//+------------------------------------------------------------------+
void OnTick()
{
   CheckNewDailyBar();
   ManageOpenPositions();
}

//+------------------------------------------------------------------+
//| Timer: keeps trailing active even in slow markets/VPS             |
//+------------------------------------------------------------------+
void OnTimer()
{
   CheckNewDailyBar();
   ManageOpenPositions();
}
//+------------------------------------------------------------------+
