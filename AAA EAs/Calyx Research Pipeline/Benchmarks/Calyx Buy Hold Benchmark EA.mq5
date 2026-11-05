// Buy-and-hold benchmark for the Calyx pipeline (owner 2026-11-05: every new EA idea is compared to just buying and holding).
// Buys once on the first tick at InpNotionalMultiple x starting equity, no stop and no target, and holds until the tester closes it
// at the end of the test. Broker spread, commission and swap are all included, so this is what holding the CFD really cost.
// Research only: it refuses to run outside the strategy tester.
#property strict
#property description "Calyx buy-and-hold benchmark. Strategy tester only."
#include <Trade/Trade.mqh>

input double InpNotionalMultiple=1.0;   // position notional as a multiple of starting equity
input long   InpMagic=99000001;

CTrade trade;
bool done=false;

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) { Print("Buy-hold benchmark runs in the strategy tester only."); return INIT_FAILED; }
   if(InpNotionalMultiple<=0) return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(InpMagic);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(done) return;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   string account=AccountInfoString(ACCOUNT_CURRENCY);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(ask<=0 || contract<=0 || step<=0) return;
   // Notional of one lot in account currency. Only forex pairs are sized in base-currency units; index and metal CFDs are contract x price,
   // even where the broker lists USD as their "base" currency. Other quote currencies are refused rather than guessed.
   long mode=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_CALC_MODE);
   bool forex=mode==SYMBOL_CALC_MODE_FOREX || mode==SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE;
   double lot_notional;
   if(forex && SymbolInfoString(_Symbol,SYMBOL_CURRENCY_BASE)==account) lot_notional=contract;
   else if(SymbolInfoString(_Symbol,SYMBOL_CURRENCY_PROFIT)==account) lot_notional=contract*ask;
   else { Print("BUYHOLD_REFUSED no direct conversion for ",_Symbol); done=true; return; }
   double lots=MathMax(vmin,MathMin(vmax,MathRound(equity*InpNotionalMultiple/lot_notional/step)*step));
   if(trade.Buy(NormalizeDouble(lots,8),_Symbol,0,0,0,"BUYHOLD"))
   {
      PrintFormat("BUYHOLD_SPEC symbol=%s lots=%.4f lot_notional=%.2f equity=%.2f ask=%.5f",_Symbol,lots,lot_notional,equity,ask);
      done=true;
   }
}
