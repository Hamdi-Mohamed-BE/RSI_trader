#property copyright "HAMA Algo Systems — Markov regime research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "DynamicTrailingSessionFilter.mqh"

input group "Markov regime"
input int InpWindow=40;
input double InpThreshold=0.05;
input double InpSignalGate=0.05;
input int InpMinimumTrainingLabels=252;
input int InpMaximumHistoryBars=3000;

input group "ATR execution"
input int InpATRPeriod=14;
input double InpInitialStopATR=4.0;
input double InpRewardRisk=3.0;
input bool InpCloseWhenRegimeInvalid=true;

input group "Risk and execution"
input bool InpEnableTrading=true;
input double InpRiskPercent=1.0;
input double InpMaximumNotionalLeverage=2.0;
input long InpMagic=86280828;
input int InpMaximumDeviationPoints=50;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_d1_bar=0;
double g_last_signal=0.0;
int g_last_state=1;

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw_lots)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || raw_lots<minimum) return 0.0;
   double lots=MathFloor(raw_lots/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return MathMin(lots,maximum);
}

bool ReadATR(const int shift,double &value)
{
   double buffer[];
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,shift,1,buffer)!=1)
      return false;
   value=buffer[0];
   return MathIsValidNumber(value) && value>0.0;
}

int RegimeState(const double current_close,const double earlier_close)
{
   if(earlier_close<=0.0) return 1;
   double rolling_return=current_close/earlier_close-1.0;
   if(rolling_return>InpThreshold) return 2;
   if(rolling_return<-InpThreshold) return 0;
   return 1;
}

bool CalculateSignal(double &signal,int &current_state)
{
   int available=Bars(_Symbol,PERIOD_D1)-1;
   int requested=MathMin(available,InpMaximumHistoryBars+InpWindow);
   if(requested<InpWindow+InpMinimumTrainingLabels+1) return false;

   double closes[];
   ArraySetAsSeries(closes,true);
   int copied=CopyClose(_Symbol,PERIOD_D1,1,requested,closes);
   if(copied<InpWindow+InpMinimumTrainingLabels+1) return false;

   int label_count=copied-InpWindow;
   int labels[];
   ArrayResize(labels,label_count);
   for(int chronological=0;chronological<label_count;chronological++)
   {
      int shift=label_count-1-chronological;
      labels[chronological]=RegimeState(closes[shift],closes[shift+InpWindow]);
   }

   // Match the no-lookahead Python research: when forecasting from the newest
   // state, do not count the transition that led into that newest state.
   double counts[3][3];
   ArrayInitialize(counts,0.0);
   for(int index=0;index<label_count-2;index++)
      counts[labels[index]][labels[index+1]]+=1.0;

   current_state=labels[label_count-1];
   double row_total=counts[current_state][0]+counts[current_state][1]+counts[current_state][2];
   if(row_total<=0.0) return false;
   double bear_probability=counts[current_state][0]/row_total;
   double bull_probability=counts[current_state][2]/row_total;
   signal=bull_probability-bear_probability;
   return MathIsValidNumber(signal);
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ticket=PositionGetTicket(index);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return true;
   }
   ticket=0;
   return false;
}

double LotsForRisk(const double entry,const double stop)
{
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_cash=equity*InpRiskPercent/100.0;
   double loss_one_lot=0.0;
   if(risk_cash<=0.0 || !OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1.0,entry,stop,loss_one_lot))
      return 0.0;
   loss_one_lot=MathAbs(loss_one_lot);
   if(loss_one_lot<=0.0) return 0.0;
   double risk_lots=risk_cash/loss_one_lot;

   double contract_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   double leverage_lots=risk_lots;
   if(InpMaximumNotionalLeverage>0.0 && contract_size>0.0 && entry>0.0)
      leverage_lots=equity*InpMaximumNotionalLeverage/(entry*contract_size);
   return NormalizeLots(MathMin(risk_lots,leverage_lots));
}

bool CloseOurPosition(const ulong ticket,const string reason)
{
   if(!InpEnableTrading) return false;
   if(g_trade.PositionClose(ticket,InpMaximumDeviationPoints)) return true;
   Print("Markov close failed (",reason,"): ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
   return false;
}

void TrailOurPosition(const ulong ticket,const double atr)
{
   if(!PositionSelectByTicket(ticket)) return;
   if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)!=POSITION_TYPE_BUY) return;
   double current_stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double reference_close=iClose(_Symbol,PERIOD_D1,1);
   double proposed=NormalizePrice(reference_close-InpInitialStopATR*atr);
   if(proposed<=current_stop) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   proposed=NormalizePrice(MathMin(proposed,tick.bid-broker_gap));
   if(proposed<=current_stop) return;
   if(InpEnableTrading && !g_trade.PositionModify(ticket,proposed,target))
      Print("Markov trail failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
}

bool OpenLong(const double atr)
{
   if(!DTS_EntrySessionAllowed()) return false;
   if(!InpEnableTrading) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   double stop_distance=MathMax(InpInitialStopATR*atr,broker_gap);
   double stop=NormalizePrice(tick.ask-stop_distance);
   double target=NormalizePrice(tick.ask+InpRewardRisk*stop_distance);
   double lots=LotsForRisk(tick.ask,stop);
   if(lots<=0.0)
   {
      Print("Markov entry skipped: broker minimum lot would exceed requested risk or leverage cap.");
      return false;
   }
   if(g_trade.Buy(lots,_Symbol,0.0,stop,target,"XAU Markov Regime")) return true;
   Print("Markov buy failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
   return false;
}

void EvaluateNewDailyBar()
{
   double signal=0.0;
   int state=1;
   double atr=0.0;
   if(!CalculateSignal(signal,state) || !ReadATR(1,atr))
   {
      Print("Markov evaluation skipped: insufficient D1 history or ATR data.");
      return;
   }
   g_last_signal=signal;
   g_last_state=state;

   ulong ticket=0;
   bool has_position=SelectOurPosition(ticket);
   if(has_position && InpCloseWhenRegimeInvalid && signal<=InpSignalGate)
   {
      CloseOurPosition(ticket,"regime invalid");
      has_position=SelectOurPosition(ticket);
   }
   if(has_position)
   {
      TrailOurPosition(ticket,atr);
      return;
   }
   if(signal>InpSignalGate) OpenLong(atr);
}

int OnInit()
{
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   if(InpWindow<2 || InpThreshold<=0.0 || InpSignalGate<0.0 ||
      InpMinimumTrainingLabels<20 || InpATRPeriod<2 || InpInitialStopATR<=0.0 ||
      InpRewardRisk<=0.0 || InpRiskPercent<=0.0)
      return INIT_PARAMETERS_INCORRECT;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_atr_handle=iATR(_Symbol,PERIOD_D1,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_last_d1_bar=(bool)MQLInfoInteger(MQL_TESTER) ? 0 : iTime(_Symbol,PERIOD_D1,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   Comment("");
}

void OnTick()
{
   DTS_ManageDynamicTrailing(InpMagic);
   datetime current_bar=iTime(_Symbol,PERIOD_D1,0);
   if(current_bar>0 && current_bar!=g_last_d1_bar)
   {
      g_last_d1_bar=current_bar;
      EvaluateNewDailyBar();
   }
   string state_name=(g_last_state==2 ? "Bull" : (g_last_state==0 ? "Bear" : "Sideways"));
   Comment("XAU Markov Regime\nState: ",state_name,"\nSignal: ",DoubleToString(g_last_signal,4),
           "\nGate: ",DoubleToString(InpSignalGate,4));
}
