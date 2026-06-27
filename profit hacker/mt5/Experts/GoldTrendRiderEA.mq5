#property copyright "Open reimplementation from publicly described behavior"
#property version   "1.00"
#property strict
#property description "Gold M15 trend EA using SuperTrend, MACD, re-entry, and risk controls."

#include <Trade/Trade.mqh>

enum LotSizingMode
  {
   LOT_FIXED = 0,
   LOT_RISK_PERCENT = 1
  };

enum StopDistanceMode
  {
   STOP_FIXED_POINTS = 0,
   STOP_ATR_MULTIPLE = 1
  };

enum DrawdownCloseScope
  {
   DRAWDOWN_EA_POSITIONS = 0,
   DRAWDOWN_WHOLE_ACCOUNT = 1
  };

enum SignalSource
  {
   SOURCE_NONE = 0,
   SOURCE_SUPERTREND = 1,
   SOURCE_MACD = 2,
   SOURCE_COMBINED = 3
  };

input group "General"
input ulong           InpMagicNumber              = 26062026;
input ENUM_TIMEFRAMES InpTradingTimeframe         = PERIOD_M15;
input bool            InpShowDashboard            = true;
input int             InpMaxSpreadPoints          = 0;       // 0 disables the spread filter
input int             InpSlippagePoints           = 30;

input group "Signals"
input bool            InpEnableSuperTrend         = true;
input int             InpSuperTrendATRPeriod      = 10;
input double          InpSuperTrendMultiplier     = 3.0;
input int             InpSuperTrendLookback       = 350;
input bool            InpEnableMACD               = true;
input int             InpMACDFastEMA              = 12;
input int             InpMACDSlowEMA              = 26;
input int             InpMACDSignalPeriod         = 9;
input bool            InpEnableReEntry            = true;
input int             InpReEntryValidBars         = 4;

input group "Signal filters"
input int             InpATRPeriod                = 14;
input int             InpMinimumATRPoints         = 0;       // 0 disables the minimum
input int             InpMaximumATRPoints         = 0;       // 0 disables the maximum
input bool            InpUseEMAFilter             = true;
input int             InpEMAPeriod                = 100;
input bool            InpUseHigherTimeframeFilter = true;
input ENUM_TIMEFRAMES InpHigherTimeframe          = PERIOD_H1;
input int             InpHigherTimeframeEMA       = 200;
input bool            InpUseBollingerFilter       = true;
input int             InpBollingerPeriod          = 20;
input double          InpBollingerDeviation       = 2.0;

input group "Position sizing"
input LotSizingMode   InpLotSizingMode            = LOT_RISK_PERCENT;
input double          InpFixedLot                 = 0.01;
input double          InpRiskPercent              = 1.0;
input double          InpMaximumLot               = 1.0;

input group "Initial stop and target"
input StopDistanceMode InpStopDistanceMode        = STOP_ATR_MULTIPLE;
input int              InpStopLossPoints          = 1000;
input double           InpStopATRMultiplier       = 2.0;
input bool             InpUseRiskRewardTarget     = true;
input double           InpRewardRiskRatio         = 2.0;
input int              InpTakeProfitPoints        = 2000;

input group "Trade management"
input StopDistanceMode InpManagementDistanceMode  = STOP_ATR_MULTIPLE;
input bool            InpEnableBreakEven          = true;
input int             InpBreakEvenTriggerPoints   = 1000;
input double          InpBreakEvenTriggerATR      = 1.0;
input int             InpBreakEvenLockPoints      = 0;
input bool            InpEnableTrailingStop       = true;
input int             InpTrailingStartPoints      = 1500;
input int             InpTrailingDistancePoints   = 800;
input double          InpTrailingStartATR         = 1.5;
input double          InpTrailingDistanceATR      = 1.0;
input bool            InpCloseSuperTrendOpposite  = true;

input group "Account protection"
input double             InpMaximumDrawdownPercent = 20.0;   // Peak equity since EA start
input DrawdownCloseScope InpDrawdownCloseScope     = DRAWDOWN_EA_POSITIONS;
input int                InpTradingStartHour       = 0;      // Broker server time
input int                InpTradingEndHour         = 0;      // Same as start means 24 hours

CTrade trade;

int      atr_handle       = INVALID_HANDLE;
int      super_atr_handle = INVALID_HANDLE;
int      macd_handle      = INVALID_HANDLE;
int      ema_handle       = INVALID_HANDLE;
int      bands_handle     = INVALID_HANDLE;
int      htf_ema_handle   = INVALID_HANDLE;
datetime last_bar_time    = 0;
double   peak_equity      = 0.0;
bool     trading_halted   = false;

int          reentry_direction = 0;
int          reentry_bars_left = 0;
SignalSource reentry_source    = SOURCE_NONE;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpTradingTimeframe != PERIOD_M15)
      Print("GoldTrendRiderEA: the public strategy was described for M15; current input is ",
            EnumToString(InpTradingTimeframe), ".");

   if(InpSuperTrendATRPeriod < 1 || InpATRPeriod < 1 || InpEMAPeriod < 1 ||
      InpRiskPercent < 0.0 || InpMaximumLot <= 0.0 ||
      InpTradingStartHour < 0 || InpTradingStartHour > 23 ||
      InpTradingEndHour < 0 || InpTradingEndHour > 23)
     {
      Print("GoldTrendRiderEA: invalid input values.");
      return INIT_PARAMETERS_INCORRECT;
     }

   atr_handle = iATR(_Symbol, InpTradingTimeframe, InpATRPeriod);
   super_atr_handle = iATR(_Symbol, InpTradingTimeframe, InpSuperTrendATRPeriod);
   macd_handle = iMACD(_Symbol, InpTradingTimeframe, InpMACDFastEMA,
                       InpMACDSlowEMA, InpMACDSignalPeriod, PRICE_CLOSE);
   ema_handle = iMA(_Symbol, InpTradingTimeframe, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   bands_handle = iBands(_Symbol, InpTradingTimeframe, InpBollingerPeriod, 0,
                         InpBollingerDeviation, PRICE_CLOSE);
   htf_ema_handle = iMA(_Symbol, InpHigherTimeframe, InpHigherTimeframeEMA,
                        0, MODE_EMA, PRICE_CLOSE);

   if(atr_handle == INVALID_HANDLE || super_atr_handle == INVALID_HANDLE ||
      macd_handle == INVALID_HANDLE || ema_handle == INVALID_HANDLE ||
      bands_handle == INVALID_HANDLE || htf_ema_handle == INVALID_HANDLE)
     {
      Print("GoldTrendRiderEA: failed to create one or more indicator handles. Error ", GetLastError());
      return INIT_FAILED;
     }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);

   peak_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   last_bar_time = iTime(_Symbol, InpTradingTimeframe, 0);

   Print("GoldTrendRiderEA initialized on ", _Symbol, " ", EnumToString(InpTradingTimeframe),
         ". Test on a demo account before considering live use.");
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Expert shutdown                                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(atr_handle != INVALID_HANDLE)
      IndicatorRelease(atr_handle);
   if(super_atr_handle != INVALID_HANDLE)
      IndicatorRelease(super_atr_handle);
   if(macd_handle != INVALID_HANDLE)
      IndicatorRelease(macd_handle);
   if(ema_handle != INVALID_HANDLE)
      IndicatorRelease(ema_handle);
   if(bands_handle != INVALID_HANDLE)
      IndicatorRelease(bands_handle);
   if(htf_ema_handle != INVALID_HANDLE)
      IndicatorRelease(htf_ema_handle);

   Comment("");
  }

//+------------------------------------------------------------------+
//| Tick processing                                                  |
//+------------------------------------------------------------------+
void OnTick()
  {
   CheckDrawdownProtection();
   ManageOpenPositions();

   datetime current_bar = iTime(_Symbol, InpTradingTimeframe, 0);
   if(current_bar > 0 && current_bar != last_bar_time)
     {
      last_bar_time = current_bar;
      EvaluateClosedBar();
     }

   UpdateDashboard();
  }

//+------------------------------------------------------------------+
//| Evaluate signals once, at the open of each new bar               |
//+------------------------------------------------------------------+
void EvaluateClosedBar()
  {
   int super_now = 0;
   int super_previous = 0;
   if(!GetSuperTrendDirections(super_now, super_previous))
     {
      Print("GoldTrendRiderEA: waiting for enough SuperTrend history.");
      return;
     }

   double macd_now = 0.0;
   double signal_now = 0.0;
   double macd_previous = 0.0;
   double signal_previous = 0.0;
   bool macd_ready = GetIndicatorValue(macd_handle, 0, 1, macd_now) &&
                     GetIndicatorValue(macd_handle, 1, 1, signal_now) &&
                     GetIndicatorValue(macd_handle, 0, 2, macd_previous) &&
                     GetIndicatorValue(macd_handle, 1, 2, signal_previous);

   if(InpCloseSuperTrendOpposite)
      CloseSuperTrendPositionsOnFlip(super_now, super_previous);

   int super_signal = 0;
   if(InpEnableSuperTrend)
     {
      if(super_now > 0 && super_previous < 0)
         super_signal = 1;
      else if(super_now < 0 && super_previous > 0)
         super_signal = -1;
     }

   int macd_signal = 0;
   if(InpEnableMACD && macd_ready)
     {
      if(macd_now > signal_now && macd_previous <= signal_previous)
         macd_signal = 1;
      else if(macd_now < signal_now && macd_previous >= signal_previous)
         macd_signal = -1;
     }

   int raw_direction = 0;
   SignalSource raw_source = SOURCE_NONE;
   if(super_signal != 0 && macd_signal != 0)
     {
      if(super_signal != macd_signal)
        {
         Print("GoldTrendRiderEA: conflicting SuperTrend and MACD signals; no entry.");
         ClearReEntry();
         return;
        }
      raw_direction = super_signal;
      raw_source = SOURCE_COMBINED;
     }
   else if(super_signal != 0)
     {
      raw_direction = super_signal;
      raw_source = SOURCE_SUPERTREND;
     }
   else if(macd_signal != 0)
     {
      raw_direction = macd_signal;
      raw_source = SOURCE_MACD;
     }

   if(HasManagedPosition())
     {
      if(raw_direction != 0)
         Print("GoldTrendRiderEA: signal ignored because this EA already manages a position on ", _Symbol, ".");
      return;
     }

   if(raw_direction != 0)
     {
      string rejection_reason = "";
      if(CanOpenDirection(raw_direction, rejection_reason))
        {
         if(OpenPosition(raw_direction, raw_source, false))
            ClearReEntry();
        }
      else
        {
         Print("GoldTrendRiderEA: ", DirectionText(raw_direction), " signal blocked by ", rejection_reason, ".");
         StoreReEntry(raw_direction, raw_source);
        }
      return;
     }

   TryReEntry(super_now, macd_ready, macd_now, signal_now);
  }

//+------------------------------------------------------------------+
//| Re-evaluate a previously filtered signal                         |
//+------------------------------------------------------------------+
void TryReEntry(const int super_direction,
                const bool macd_ready,
                const double macd_value,
                const double macd_signal_value)
  {
   if(!InpEnableReEntry || reentry_direction == 0 || reentry_bars_left <= 0)
      return;

   bool still_valid = false;
   if(reentry_source == SOURCE_SUPERTREND)
      still_valid = (super_direction == reentry_direction);
   else if(reentry_source == SOURCE_MACD)
      still_valid = macd_ready &&
                    ((reentry_direction > 0 && macd_value > macd_signal_value) ||
                     (reentry_direction < 0 && macd_value < macd_signal_value));
   else
      still_valid = (super_direction == reentry_direction) ||
                    (macd_ready &&
                     ((reentry_direction > 0 && macd_value > macd_signal_value) ||
                      (reentry_direction < 0 && macd_value < macd_signal_value)));

   if(!still_valid)
     {
      Print("GoldTrendRiderEA: delayed signal is no longer valid.");
      ClearReEntry();
      return;
     }

   string rejection_reason = "";
   if(CanOpenDirection(reentry_direction, rejection_reason))
     {
      if(OpenPosition(reentry_direction, reentry_source, true))
         ClearReEntry();
      return;
     }

   reentry_bars_left--;
   Print("GoldTrendRiderEA: delayed ", DirectionText(reentry_direction),
         " still blocked by ", rejection_reason, "; ", reentry_bars_left, " bar(s) left.");
   if(reentry_bars_left <= 0)
      ClearReEntry();
  }

void StoreReEntry(const int direction, const SignalSource source)
  {
   if(!InpEnableReEntry || InpReEntryValidBars <= 0)
      return;

   reentry_direction = direction;
   reentry_source = source;
   reentry_bars_left = InpReEntryValidBars;
  }

void ClearReEntry()
  {
   reentry_direction = 0;
   reentry_source = SOURCE_NONE;
   reentry_bars_left = 0;
  }

//+------------------------------------------------------------------+
//| Signal filters                                                   |
//+------------------------------------------------------------------+
bool CanOpenDirection(const int direction, string &reason)
  {
   if(trading_halted)
     {
      reason = "drawdown halt";
      return false;
     }

   if(!IsTradingHour())
     {
      reason = "trading hours";
      return false;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
     {
      reason = "missing market quote";
      return false;
     }

   double spread_points = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spread_points > InpMaxSpreadPoints)
     {
      reason = "spread";
      return false;
     }

   double atr_value = 0.0;
   if(!GetIndicatorValue(atr_handle, 0, 1, atr_value))
     {
      reason = "ATR data";
      return false;
     }
   double atr_points = atr_value / _Point;
   if(InpMinimumATRPoints > 0 && atr_points < InpMinimumATRPoints)
     {
      reason = "low volatility";
      return false;
     }
   if(InpMaximumATRPoints > 0 && atr_points > InpMaximumATRPoints)
     {
      reason = "excess volatility";
      return false;
     }

   double close_price = iClose(_Symbol, InpTradingTimeframe, 1);
   if(close_price <= 0.0)
     {
      reason = "price history";
      return false;
     }

   if(InpUseEMAFilter)
     {
      double ema_value = 0.0;
      if(!GetIndicatorValue(ema_handle, 0, 1, ema_value))
        {
         reason = "EMA data";
         return false;
        }
      if((direction > 0 && close_price <= ema_value) ||
         (direction < 0 && close_price >= ema_value))
        {
         reason = "EMA trend";
         return false;
        }
     }

   if(InpUseHigherTimeframeFilter)
     {
      double htf_ema = 0.0;
      double htf_close = iClose(_Symbol, InpHigherTimeframe, 1);
      if(htf_close <= 0.0 || !GetIndicatorValue(htf_ema_handle, 0, 1, htf_ema))
        {
         reason = "higher-timeframe data";
         return false;
        }
      if((direction > 0 && htf_close <= htf_ema) ||
         (direction < 0 && htf_close >= htf_ema))
        {
         reason = "higher-timeframe trend";
         return false;
        }
     }

   if(InpUseBollingerFilter)
     {
      double upper_band = 0.0;
      double lower_band = 0.0;
      if(!GetIndicatorValue(bands_handle, 1, 1, upper_band) ||
         !GetIndicatorValue(bands_handle, 2, 1, lower_band))
        {
         reason = "Bollinger data";
         return false;
        }
      if((direction > 0 && close_price > upper_band) ||
         (direction < 0 && close_price < lower_band))
        {
         reason = "Bollinger price extreme";
         return false;
        }
     }

   reason = "";
   return true;
  }

//+------------------------------------------------------------------+
//| Order creation                                                   |
//+------------------------------------------------------------------+
bool OpenPosition(const int direction, const SignalSource source, const bool is_reentry)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return false;

   double entry = (direction > 0) ? tick.ask : tick.bid;
   double atr_value = 0.0;
   if(!GetIndicatorValue(atr_handle, 0, 1, atr_value))
      return false;

   double stop_distance = 0.0;
   if(InpStopDistanceMode == STOP_ATR_MULTIPLE)
      stop_distance = atr_value * InpStopATRMultiplier;
   else
      stop_distance = InpStopLossPoints * _Point;

   double broker_minimum = MinimumStopDistance();
   stop_distance = MathMax(stop_distance, broker_minimum);
   if(stop_distance <= 0.0)
     {
      Print("GoldTrendRiderEA: stop distance must be greater than zero.");
      return false;
     }

   double target_distance = InpUseRiskRewardTarget
                            ? stop_distance * InpRewardRiskRatio
                            : InpTakeProfitPoints * _Point;
   target_distance = MathMax(target_distance, broker_minimum);

   double stop_loss = (direction > 0) ? entry - stop_distance : entry + stop_distance;
   double take_profit = (direction > 0) ? entry + target_distance : entry - target_distance;
   stop_loss = NormalizeDouble(stop_loss, _Digits);
   take_profit = NormalizeDouble(take_profit, _Digits);

   double volume = InpFixedLot;
   if(InpLotSizingMode == LOT_RISK_PERCENT)
      volume = CalculateRiskVolume(direction, entry, stop_loss);
   else
      volume = NormalizeVolume(volume);

   volume = FitVolumeToMargin(direction, volume, entry);
   if(volume <= 0.0)
     {
      Print("GoldTrendRiderEA: not enough free margin for the broker's minimum volume.");
      return false;
     }

   string order_comment = SignalComment(source, is_reentry);
   bool sent = false;
   if(direction > 0)
      sent = trade.Buy(volume, _Symbol, 0.0, stop_loss, take_profit, order_comment);
   else
      sent = trade.Sell(volume, _Symbol, 0.0, stop_loss, take_profit, order_comment);

   uint retcode = trade.ResultRetcode();
   if(!sent || (retcode != TRADE_RETCODE_DONE &&
                retcode != TRADE_RETCODE_DONE_PARTIAL &&
                retcode != TRADE_RETCODE_PLACED))
     {
      Print("GoldTrendRiderEA: order failed. Retcode ", retcode, " (", trade.ResultRetcodeDescription(), ").");
      return false;
     }

   Print("GoldTrendRiderEA: opened ", DirectionText(direction), " ",
         DoubleToString(volume, VolumeDigits()), " lot(s), SL ",
         DoubleToString(stop_loss, _Digits), ", TP ", DoubleToString(take_profit, _Digits),
         ", source ", order_comment, ".");
   return true;
  }

double CalculateRiskVolume(const int direction, const double entry, const double stop_loss)
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money = equity * InpRiskPercent / 100.0;
   double one_lot_loss = 0.0;
   ENUM_ORDER_TYPE order_type = (direction > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   if(risk_money <= 0.0 ||
      !OrderCalcProfit(order_type, _Symbol, 1.0, entry, stop_loss, one_lot_loss) ||
      MathAbs(one_lot_loss) <= 0.0)
     {
      Print("GoldTrendRiderEA: risk calculation unavailable; using broker minimum volume.");
      return NormalizeVolume(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
     }

   double raw_volume = risk_money / MathAbs(one_lot_loss);
   double broker_minimum = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   if(raw_volume < broker_minimum)
      Print("GoldTrendRiderEA: calculated risk volume is below broker minimum; minimum volume will be used.");

   return NormalizeVolume(raw_volume);
  }

double NormalizeVolume(const double requested_volume)
  {
   double minimum = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maximum = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double cap = MathMin(maximum, InpMaximumLot);

   if(step <= 0.0)
      step = minimum;
   if(cap < minimum)
      cap = minimum;

   double volume = MathMax(minimum, MathMin(requested_volume, cap));
   volume = MathFloor(volume / step + 1e-9) * step;
   volume = MathMax(minimum, MathMin(volume, cap));
   return NormalizeDouble(volume, VolumeDigits());
  }

double FitVolumeToMargin(const int direction, double volume, const double entry)
  {
   double minimum = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   ENUM_ORDER_TYPE order_type = (direction > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   while(volume >= minimum - 1e-9)
     {
      double required_margin = 0.0;
      if(!OrderCalcMargin(order_type, _Symbol, volume, entry, required_margin))
         return volume;
      if(required_margin <= free_margin * 0.95)
         return volume;
      if(volume <= minimum + step / 2.0)
         break;
      volume = NormalizeVolume(volume - step);
     }

   return 0.0;
  }

//+------------------------------------------------------------------+
//| Open-position management                                         |
//+------------------------------------------------------------------+
void ManageOpenPositions()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   double atr_value = 0.0;
   if(InpManagementDistanceMode == STOP_ATR_MULTIPLE &&
      !GetIndicatorValue(atr_handle, 0, 1, atr_value))
      return;

   double break_even_trigger = (InpManagementDistanceMode == STOP_ATR_MULTIPLE)
                               ? atr_value * InpBreakEvenTriggerATR
                               : InpBreakEvenTriggerPoints * _Point;
   double trailing_start = (InpManagementDistanceMode == STOP_ATR_MULTIPLE)
                           ? atr_value * InpTrailingStartATR
                           : InpTrailingStartPoints * _Point;
   double trailing_distance = (InpManagementDistanceMode == STOP_ATR_MULTIPLE)
                              ? atr_value * InpTrailingDistanceATR
                              : InpTrailingDistancePoints * _Point;

   double minimum_stop = MinimumStopDistance();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsSelectedManagedPosition())
         continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl = PositionGetDouble(POSITION_SL);
      double take_profit = PositionGetDouble(POSITION_TP);
      double market_price = (type == POSITION_TYPE_BUY) ? tick.bid : tick.ask;

      double desired_sl = current_sl;
      bool improve = false;

      if(InpEnableBreakEven)
        {
         double favorable_move = (type == POSITION_TYPE_BUY)
                                  ? market_price - open_price
                                  : open_price - market_price;
         if(favorable_move >= break_even_trigger)
           {
            double break_even_sl = (type == POSITION_TYPE_BUY)
                                   ? open_price + InpBreakEvenLockPoints * _Point
                                   : open_price - InpBreakEvenLockPoints * _Point;
            bool valid_distance = (type == POSITION_TYPE_BUY)
                                  ? break_even_sl <= tick.bid - minimum_stop
                                  : break_even_sl >= tick.ask + minimum_stop;
            bool better = (type == POSITION_TYPE_BUY)
                          ? (current_sl == 0.0 || break_even_sl > desired_sl + _Point / 2.0)
                          : (current_sl == 0.0 || break_even_sl < desired_sl - _Point / 2.0);
            if(valid_distance && better)
              {
               desired_sl = break_even_sl;
               improve = true;
              }
           }
        }

      if(InpEnableTrailingStop)
        {
         double favorable_move = (type == POSITION_TYPE_BUY)
                                  ? market_price - open_price
                                  : open_price - market_price;
         if(favorable_move >= trailing_start)
           {
            double trailing_sl = (type == POSITION_TYPE_BUY)
                                 ? tick.bid - trailing_distance
                                 : tick.ask + trailing_distance;
            bool valid_distance = (type == POSITION_TYPE_BUY)
                                  ? trailing_sl <= tick.bid - minimum_stop
                                  : trailing_sl >= tick.ask + minimum_stop;
            bool better = (type == POSITION_TYPE_BUY)
                          ? (desired_sl == 0.0 || trailing_sl > desired_sl + _Point / 2.0)
                          : (desired_sl == 0.0 || trailing_sl < desired_sl - _Point / 2.0);
            if(valid_distance && better)
              {
               desired_sl = trailing_sl;
               improve = true;
              }
           }
        }

      if(improve)
        {
         desired_sl = NormalizeDouble(desired_sl, _Digits);
         if(!trade.PositionModify(ticket, desired_sl, take_profit))
            Print("GoldTrendRiderEA: stop update failed for #", ticket, ": ", trade.ResultRetcodeDescription());
        }
     }
  }

void CloseSuperTrendPositionsOnFlip(const int current_direction, const int previous_direction)
  {
   if(current_direction == previous_direction)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsSelectedManagedPosition())
         continue;

      string comment = PositionGetString(POSITION_COMMENT);
      if(StringFind(comment, "ST") < 0)
         continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      bool opposite = (type == POSITION_TYPE_BUY && current_direction < 0) ||
                      (type == POSITION_TYPE_SELL && current_direction > 0);
      if(opposite)
        {
         if(trade.PositionClose(ticket))
            Print("GoldTrendRiderEA: closed SuperTrend position #", ticket, " on the opposite trend flip.");
         else
            Print("GoldTrendRiderEA: opposite-signal close failed for #", ticket, ": ",
                  trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
//| Drawdown protection                                              |
//+------------------------------------------------------------------+
void CheckDrawdownProtection()
  {
   if(InpMaximumDrawdownPercent <= 0.0 || trading_halted)
      return;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > peak_equity)
      peak_equity = equity;
   if(peak_equity <= 0.0)
      return;

   double drawdown = 100.0 * (peak_equity - equity) / peak_equity;
   if(drawdown < InpMaximumDrawdownPercent)
      return;

   trading_halted = true;
   ClearReEntry();
   Print("GoldTrendRiderEA: maximum drawdown reached (", DoubleToString(drawdown, 2),
         "%). Closing protected positions and halting new entries until EA restart.");
   CloseProtectedPositions();
  }

void CloseProtectedPositions()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;

      bool close_position = (InpDrawdownCloseScope == DRAWDOWN_WHOLE_ACCOUNT) ||
                            IsSelectedManagedPosition();
      if(close_position && !trade.PositionClose(ticket))
         Print("GoldTrendRiderEA: drawdown close failed for #", ticket, ": ",
               trade.ResultRetcodeDescription());
     }
  }

//+------------------------------------------------------------------+
//| Internal non-repainting SuperTrend, read from closed bars         |
//+------------------------------------------------------------------+
bool GetSuperTrendDirections(int &current_direction, int &previous_direction)
  {
   int requested = MathMax(InpSuperTrendLookback, InpSuperTrendATRPeriod + 50);
   MqlRates rates[];
   double atr_values[];
   ArraySetAsSeries(rates, true);
   ArraySetAsSeries(atr_values, true);

   int rates_copied = CopyRates(_Symbol, InpTradingTimeframe, 0, requested, rates);
   int atr_copied = CopyBuffer(super_atr_handle, 0, 0, requested, atr_values);
   int count = MathMin(rates_copied, atr_copied);
   if(count < InpSuperTrendATRPeriod + 5 || count < 3)
      return false;

   double final_upper[];
   double final_lower[];
   int trend[];
   ArrayResize(final_upper, count);
   ArrayResize(final_lower, count);
   ArrayResize(trend, count);

   int oldest = count - 1;
   double midpoint = (rates[oldest].high + rates[oldest].low) / 2.0;
   final_upper[oldest] = midpoint + InpSuperTrendMultiplier * atr_values[oldest];
   final_lower[oldest] = midpoint - InpSuperTrendMultiplier * atr_values[oldest];
   trend[oldest] = (rates[oldest].close >= midpoint) ? 1 : -1;

   for(int i = oldest - 1; i >= 0; i--)
     {
      int previous = i + 1;
      midpoint = (rates[i].high + rates[i].low) / 2.0;
      double basic_upper = midpoint + InpSuperTrendMultiplier * atr_values[i];
      double basic_lower = midpoint - InpSuperTrendMultiplier * atr_values[i];

      final_upper[i] = (basic_upper < final_upper[previous] ||
                        rates[previous].close > final_upper[previous])
                       ? basic_upper : final_upper[previous];
      final_lower[i] = (basic_lower > final_lower[previous] ||
                        rates[previous].close < final_lower[previous])
                       ? basic_lower : final_lower[previous];

      if(trend[previous] < 0)
         trend[i] = (rates[i].close > final_upper[i]) ? 1 : -1;
      else
         trend[i] = (rates[i].close < final_lower[i]) ? -1 : 1;
     }

   current_direction = trend[1];
   previous_direction = trend[2];
   return true;
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
bool GetIndicatorValue(const int handle, const int buffer,
                       const int shift, double &value)
  {
   double values[1];
   if(CopyBuffer(handle, buffer, shift, 1, values) != 1 || values[0] == EMPTY_VALUE)
      return false;
   value = values[0];
   return true;
  }

bool IsTradingHour()
  {
   if(InpTradingStartHour == InpTradingEndHour)
      return true;

   MqlDateTime server_time;
   TimeToStruct(TimeTradeServer(), server_time);
   if(InpTradingStartHour < InpTradingEndHour)
      return server_time.hour >= InpTradingStartHour && server_time.hour < InpTradingEndHour;
   return server_time.hour >= InpTradingStartHour || server_time.hour < InpTradingEndHour;
  }

bool HasManagedPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) != 0 && IsSelectedManagedPosition())
         return true;
     }
   return false;
  }

bool IsSelectedManagedPosition()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol &&
          (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagicNumber;
  }

double MinimumStopDistance()
  {
   long stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   return (stops_level + 2) * _Point;
  }

int VolumeDigits()
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   for(int digits = 0; digits <= 8; digits++)
     {
      if(MathAbs(step - NormalizeDouble(step, digits)) < 1e-10)
         return digits;
     }
   return 8;
  }

string DirectionText(const int direction)
  {
   return (direction > 0) ? "BUY" : "SELL";
  }

string SignalComment(const SignalSource source, const bool is_reentry)
  {
   string label = "SIGNAL";
   if(source == SOURCE_SUPERTREND)
      label = "ST";
   else if(source == SOURCE_MACD)
      label = "MACD";
   else if(source == SOURCE_COMBINED)
      label = "ST+MACD";

   return is_reentry ? "GTR|RE-" + label : "GTR|" + label;
  }

void UpdateDashboard()
  {
   if(!InpShowDashboard)
     {
      Comment("");
      return;
     }

   MqlTick tick;
   double spread = 0.0;
   if(SymbolInfoTick(_Symbol, tick))
      spread = (tick.ask - tick.bid) / _Point;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double drawdown = (peak_equity > 0.0) ? 100.0 * (peak_equity - equity) / peak_equity : 0.0;
   string state = trading_halted ? "HALTED - drawdown guard" : "RUNNING";
   string delayed = (reentry_direction == 0)
                    ? "none"
                    : DirectionText(reentry_direction) + " (" + IntegerToString(reentry_bars_left) + " bars left)";

   Comment("Gold Trend Rider EA\n",
           "State: ", state, "\n",
           "Symbol / TF: ", _Symbol, " / ", EnumToString(InpTradingTimeframe), "\n",
           "Spread: ", DoubleToString(spread, 1), " points\n",
           "Peak-equity drawdown: ", DoubleToString(MathMax(drawdown, 0.0), 2), "%\n",
           "Delayed signal: ", delayed);
  }
