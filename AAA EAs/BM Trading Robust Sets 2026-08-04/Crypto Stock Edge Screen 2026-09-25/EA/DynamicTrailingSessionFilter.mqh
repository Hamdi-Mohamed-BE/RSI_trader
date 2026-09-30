#ifndef DYNAMIC_TRAILING_SESSION_FILTER_MQH
#define DYNAMIC_TRAILING_SESSION_FILTER_MQH

enum ENUM_DTS_SESSION_MODE
  {
   DTS_SESSION_ALL=0,
   DTS_SESSION_ASIA=1,
   DTS_SESSION_LONDON=2,
   DTS_SESSION_NEW_YORK=3,
   DTS_SESSION_LONDON_NEW_YORK_OVERLAP=4
  };

input group "Research: dynamic trailing SL"
input bool                  InpUseDynamicTrailingSL=false;
input double                InpDynamicTriggerFraction=0.50;
input double                InpDynamicLockFraction=0.20;
input group "Research: UTC entry session"
input ENUM_DTS_SESSION_MODE InpResearchSession=DTS_SESSION_ALL;
input int                   InpResearchBrokerUtcOffsetMinutes=180;

struct DTS_TRACKED_POSITION
  {
   ulong    identifier;
   datetime opened;
   double   target_distance;
  };

DTS_TRACKED_POSITION g_dts_positions[];
datetime g_dts_last_m15_bar=0;

bool DTS_InputsValid()
  {
   return InpDynamicTriggerFraction>0.0 && InpDynamicTriggerFraction<=1.0 &&
          InpDynamicLockFraction>=0.0 && InpDynamicLockFraction<InpDynamicTriggerFraction &&
          InpResearchBrokerUtcOffsetMinutes>=-840 && InpResearchBrokerUtcOffsetMinutes<=840;
  }

bool DTS_MinuteInside(const int minute_of_day,const int start_minute,const int end_minute)
  {
   if(start_minute==end_minute) return true;
   if(start_minute<end_minute) return minute_of_day>=start_minute && minute_of_day<end_minute;
   return minute_of_day>=start_minute || minute_of_day<end_minute;
  }

bool DTS_EntrySessionAllowed()
  {
   if(InpResearchSession==DTS_SESSION_ALL) return true;
   datetime utc=TimeCurrent()-InpResearchBrokerUtcOffsetMinutes*60;
   MqlDateTime now; TimeToStruct(utc,now);
   int minute_of_day=now.hour*60+now.min;
   if(InpResearchSession==DTS_SESSION_ASIA)
      return DTS_MinuteInside(minute_of_day,0,8*60);
   if(InpResearchSession==DTS_SESSION_LONDON)
      return DTS_MinuteInside(minute_of_day,7*60,12*60);
   if(InpResearchSession==DTS_SESSION_NEW_YORK)
      return DTS_MinuteInside(minute_of_day,13*60,21*60);
   if(InpResearchSession==DTS_SESSION_LONDON_NEW_YORK_OVERLAP)
      return DTS_MinuteInside(minute_of_day,13*60,16*60);
   return true;
  }

int DTS_FindTracked(const ulong identifier)
  {
   for(int i=0;i<ArraySize(g_dts_positions);i++)
      if(g_dts_positions[i].identifier==identifier) return i;
   return -1;
  }

void DTS_ObservePositions(const long magic)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      if(DTS_FindTracked(identifier)>=0) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double target=PositionGetDouble(POSITION_TP);
      double stop=PositionGetDouble(POSITION_SL);
      double distance=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(target>entry) distance=target-entry;
         else if(stop>0.0 && stop<entry) distance=entry-stop;
        }
      else
        {
         if(target>0.0 && target<entry) distance=entry-target;
         else if(stop>entry) distance=stop-entry;
        }
      if(distance<=SymbolInfoDouble(_Symbol,SYMBOL_POINT)) continue;
      int size=ArraySize(g_dts_positions);
      ArrayResize(g_dts_positions,size+1);
      g_dts_positions[size].identifier=identifier;
      g_dts_positions[size].opened=(datetime)PositionGetInteger(POSITION_TIME);
      g_dts_positions[size].target_distance=distance;
     }
  }

bool DTS_ModifyStop(const ulong ticket,const double stop,const double target)
  {
   MqlTradeRequest request={};
   MqlTradeResult result={};
   request.action=TRADE_ACTION_SLTP;
   request.position=ticket;
   request.symbol=_Symbol;
   request.sl=NormalizeDouble(stop,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   request.tp=target;
   if(!OrderSend(request,result)) return false;
   return result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED || result.retcode==TRADE_RETCODE_NO_CHANGES;
  }

void DTS_ManageDynamicTrailing(const long magic)
  {
   if(!InpUseDynamicTrailingSL) return;
   DTS_ObservePositions(magic);
   datetime current_m15=iTime(_Symbol,PERIOD_M15,0);
   if(current_m15<=0) return;
   if(g_dts_last_m15_bar==0)
     {
      g_dts_last_m15_bar=current_m15;
      return;
     }
   if(current_m15==g_dts_last_m15_bar) return;
   g_dts_last_m15_bar=current_m15;
   double closed_price=iClose(_Symbol,PERIOD_M15,1);
   if(closed_price<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax(point,SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point);

   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      int tracked=DTS_FindTracked(identifier);
      if(tracked<0 || g_dts_positions[tracked].target_distance<=point) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double current_stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double distance=g_dts_positions[tracked].target_distance;
      double desired=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(closed_price<entry+InpDynamicTriggerFraction*distance) continue;
         desired=entry+InpDynamicLockFraction*distance;
         desired=MathMin(desired,tick.bid-broker_gap);
         if(desired<=entry || (current_stop>0.0 && desired<=current_stop+point)) continue;
        }
      else
        {
         if(closed_price>entry-InpDynamicTriggerFraction*distance) continue;
         desired=entry-InpDynamicLockFraction*distance;
         desired=MathMax(desired,tick.ask+broker_gap);
         if(desired>=entry || (current_stop>0.0 && desired>=current_stop-point)) continue;
        }
      if(!DTS_ModifyStop(ticket,desired,target))
         Print("Dynamic trailing SL modification failed for position ",ticket);
     }
  }

#endif
