#ifndef ONLINE_RESEARCH_COMMON_MQH
#define ONLINE_RESEARCH_COMMON_MQH

#include <Trade/Trade.mqh>

CTrade ResearchTrade;

double RT_Price(const string symbol,const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS));
}

double RT_Volume(const string symbol,const double raw)
{
   double minimum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double RT_LotsForRisk(const string symbol,const ENUM_ORDER_TYPE type,const double entry,
                      const double stop,const double risk_percent)
{
   if(risk_percent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   double one_lot_loss=MathAbs(one_lot_result);
   if(one_lot_loss<=0.0) return 0.0;
   return RT_Volume(symbol,AccountInfoDouble(ACCOUNT_EQUITY)*risk_percent/100.0/one_lot_loss);
}

bool RT_NewBar(const string symbol,const ENUM_TIMEFRAMES timeframe,datetime &last_bar)
{
   datetime current=iTime(symbol,timeframe,0);
   if(current<=0 || current==last_bar) return false;
   last_bar=current;
   return true;
}

double RT_Buffer(const int handle,const int buffer,const int shift)
{
   if(handle==INVALID_HANDLE) return EMPTY_VALUE;
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(handle,buffer,shift,1,values)!=1) return EMPTY_VALUE;
   return values[0];
}

bool RT_IsOurPosition(const string symbol,const long magic)
{
   return PositionGetString(POSITION_SYMBOL)==symbol && PositionGetInteger(POSITION_MAGIC)==magic;
}

int RT_PositionCount(const string symbol,const long magic)
{
   int count=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(PositionGetTicket(i)==0) continue;
      if(RT_IsOurPosition(symbol,magic)) count++;
   }
   return count;
}

double RT_TotalVolume(const string symbol,const long magic)
{
   double volume=0.0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(PositionGetTicket(i)==0) continue;
      if(RT_IsOurPosition(symbol,magic)) volume+=PositionGetDouble(POSITION_VOLUME);
   }
   return volume;
}

long RT_PositionDirection(const string symbol,const long magic)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(PositionGetTicket(i)==0) continue;
      if(RT_IsOurPosition(symbol,magic)) return PositionGetInteger(POSITION_TYPE);
   }
   return -1;
}

void RT_CloseAll(const string symbol,const long magic,const int deviation=50)
{
   ResearchTrade.SetExpertMagicNumber((ulong)magic);
   ResearchTrade.SetDeviationInPoints(deviation);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !RT_IsOurPosition(symbol,magic)) continue;
      if(!ResearchTrade.PositionClose(ticket,(ulong)deviation))
         Print("Close failed for ",ticket,": ",ResearchTrade.ResultRetcodeDescription());
   }
}

bool RT_CloseVolume(const string symbol,const long magic,double requested,const int deviation=50)
{
   double remaining=requested;
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   ResearchTrade.SetExpertMagicNumber((ulong)magic);
   ResearchTrade.SetDeviationInPoints(deviation);
   for(int i=PositionsTotal()-1;i>=0 && remaining>=step-1e-10;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !RT_IsOurPosition(symbol,magic)) continue;
      double have=PositionGetDouble(POSITION_VOLUME);
      double close_lots=RT_Volume(symbol,MathMin(have,remaining));
      if(close_lots<=0.0) continue;
      bool ok=(close_lots>=have-step/2.0 ? ResearchTrade.PositionClose(ticket,(ulong)deviation)
                                        : ResearchTrade.PositionClosePartial(ticket,close_lots,(ulong)deviation));
      if(!ok) Print("Partial close failed for ",ticket,": ",ResearchTrade.ResultRetcodeDescription());
      else remaining-=close_lots;
   }
   return remaining<step-1e-10;
}

void RT_ModifyAllStops(const string symbol,const long magic,const double stop)
{
   ResearchTrade.SetExpertMagicNumber((ulong)magic);
   double normalized=RT_Price(symbol,stop);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !RT_IsOurPosition(symbol,magic)) continue;
      double current=PositionGetDouble(POSITION_SL);
      long type=PositionGetInteger(POSITION_TYPE);
      bool improves=(type==POSITION_TYPE_BUY ? normalized>current : (current<=0.0 || normalized<current));
      if(improves && !ResearchTrade.PositionModify(ticket,normalized,PositionGetDouble(POSITION_TP)))
         Print("Stop update failed for ",ticket,": ",ResearchTrade.ResultRetcodeDescription());
   }
}

double RT_Highest(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_shift,const int count)
{
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyHigh(symbol,timeframe,start_shift,count,values)!=count) return EMPTY_VALUE;
   return values[ArrayMaximum(values,0,count)];
}

double RT_Lowest(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_shift,const int count)
{
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyLow(symbol,timeframe,start_shift,count,values)!=count) return EMPTY_VALUE;
   return values[ArrayMinimum(values,0,count)];
}

#endif
