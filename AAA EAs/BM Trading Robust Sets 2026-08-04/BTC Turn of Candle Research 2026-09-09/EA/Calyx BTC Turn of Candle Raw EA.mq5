#property strict
#property version   "1.00"
#property description "Raw reproduction of Shanaev, Vasenin and Stepanov (2023)."
#property description "Long BTC only during minutes 00, 15, 30 and 45; hold one M1 bar."

#include <Trade/Trade.mqh>

input bool   InpEnableTrading                    = true;
input double InpPaperCapitalAllocationPercent    = 100.0;
input int    InpHoldMinutes                      = 1;
input int    InpMaxDeviationBrokerPoints         = 100;
input long   InpMagic                            = 981009921;

CTrade trade;
datetime last_bar_time = 0;
datetime entry_bar_time = 0;

bool IsOurPosition()
{
   if(!PositionSelect(_Symbol))
      return false;
   return (long)PositionGetInteger(POSITION_MAGIC) == InpMagic;
}

double NormalizeVolumeDown(const double requested)
{
   const double minimum = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum <= 0.0 || maximum <= 0.0 || step <= 0.0)
      return 0.0;

   double value = MathMin(requested,maximum);
   value = MathFloor((value + 1e-12) / step) * step;
   if(value < minimum)
      return 0.0;
   return NormalizeDouble(value,8);
}

double PaperVolume()
{
   const double ask = SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   const double contract_size = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   const double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(ask <= 0.0 || contract_size <= 0.0 || balance <= 0.0)
      return 0.0;

   const double notional = balance * MathMax(0.0,InpPaperCapitalAllocationPercent) / 100.0;
   return NormalizeVolumeDown(notional / (ask * contract_size));
}

bool CloseExpiredPosition(const datetime current_bar)
{
   if(!IsOurPosition())
   {
      entry_bar_time = 0;
      return true;
   }

   if(entry_bar_time <= 0)
      entry_bar_time = (datetime)PositionGetInteger(POSITION_TIME);

   const int hold_seconds = MathMax(1,InpHoldMinutes) * 60;
   if(current_bar < entry_bar_time + hold_seconds)
      return false;

   if(!trade.PositionClose(_Symbol))
   {
      Print("Turn-of-candle exit failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   entry_bar_time = 0;
   return true;
}

void TryOpenTurnMinute(const datetime current_bar)
{
   if(!InpEnableTrading || IsOurPosition())
      return;

   MqlDateTime stamp;
   TimeToStruct(current_bar,stamp);
   if((stamp.min % 15) != 0)
      return;

   const double volume = PaperVolume();
   if(volume <= 0.0)
   {
      Print("Turn-of-candle entry skipped because fully invested paper volume is below broker minimum.");
      return;
   }

   if(!trade.Buy(volume,_Symbol,0.0,0.0,0.0,"raw turn-of-candle"))
   {
      Print("Turn-of-candle entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return;
   }
   entry_bar_time = current_bar;
}

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   const datetime current_bar = iTime(_Symbol,PERIOD_M1,0);
   if(current_bar <= 0 || current_bar == last_bar_time)
      return;
   last_bar_time = current_bar;

   if(!CloseExpiredPosition(current_bar))
      return;
   TryOpenTurnMinute(current_bar);
}
