#property copyright "HAMA Algo Systems"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Daily portfolio limits"
input bool   InpEnableDailyGuard=true;
input double InpDailyProfitLimitPct=2.0;
input double InpDailyLossLimitPct=2.0;
input bool   InpIncludeFloatingPnL=true;

input group "Lock actions"
input bool   InpCloseManagedPositions=true;
input bool   InpDeleteManagedPendingOrders=true;
input int    InpMaximumDeviationPoints=50;

input group "Active BAT scope"
input string InpManagedMagicCsv="7262250,86270827,86270828,86080707,86250828,86260823,86260829,460103,290729,1082601,220101,3082026,4080402,84081601,230103,310731,862023,860301";
input long   InpGuardMagic=99082701;

CTrade g_trade;
long g_managed_magics[];
int g_day_key=0;
datetime g_day_start=0;
double g_day_start_balance=0.0;
bool g_locked=false;
bool g_announced=false;

string StatePrefix()
{
   return "HAMA.BAT.DG."+IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
}

datetime ServerNow()
{
   datetime now=TimeTradeServer();
   if(now<=0) now=TimeCurrent();
   return now;
}

int DayKeyAndStart(const datetime now,datetime &start)
{
   MqlDateTime parts;
   TimeToStruct(now,parts);
   int key=parts.year*10000+parts.mon*100+parts.day;
   parts.hour=0;
   parts.min=0;
   parts.sec=0;
   start=StructToTime(parts);
   return key;
}

bool ManagedMagic(const long magic)
{
   for(int index=0;index<ArraySize(g_managed_magics);index++)
      if(g_managed_magics[index]==magic) return true;
   return false;
}

bool ParseManagedMagics()
{
   string values[];
   ushort separator=StringGetCharacter(",",0);
   int count=StringSplit(InpManagedMagicCsv,separator,values);
   if(count<=0) return false;
   ArrayResize(g_managed_magics,count);
   int accepted=0;
   for(int index=0;index<count;index++)
   {
      string token=values[index];
      StringTrimLeft(token);
      StringTrimRight(token);
      long magic=StringToInteger(token);
      if(magic<=0 || magic==InpGuardMagic) continue;
      bool duplicate=false;
      for(int prior=0;prior<accepted;prior++)
         if(g_managed_magics[prior]==magic) { duplicate=true; break; }
      if(!duplicate) g_managed_magics[accepted++]=magic;
   }
   ArrayResize(g_managed_magics,accepted);
   return accepted>0;
}

double ManagedClosedPnL(const datetime start,const datetime finish)
{
   if(!HistorySelect(start,finish)) return 0.0;
   double result=0.0;
   int total=HistoryDealsTotal();
   for(int index=0;index<total;index++)
   {
      ulong ticket=HistoryDealGetTicket(index);
      if(ticket==0 || !ManagedMagic(HistoryDealGetInteger(ticket,DEAL_MAGIC))) continue;
      result+=HistoryDealGetDouble(ticket,DEAL_PROFIT);
      result+=HistoryDealGetDouble(ticket,DEAL_COMMISSION);
      result+=HistoryDealGetDouble(ticket,DEAL_SWAP);
      result+=HistoryDealGetDouble(ticket,DEAL_FEE);
   }
   return result;
}

double ManagedFloatingPnL()
{
   double result=0.0;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !ManagedMagic(PositionGetInteger(POSITION_MAGIC))) continue;
      result+=PositionGetDouble(POSITION_PROFIT);
      result+=PositionGetDouble(POSITION_SWAP);
   }
   return result;
}

void SaveState()
{
   string prefix=StatePrefix();
   GlobalVariableSet(prefix+".DAY",(double)g_day_key);
   GlobalVariableSet(prefix+".BASE",g_day_start_balance);
   GlobalVariableSet(prefix+".LOCK",g_locked ? 1.0 : 0.0);
}

void LoadOrResetDay(const datetime now)
{
   datetime start=0;
   int key=DayKeyAndStart(now,start);
   if(key==g_day_key) return;

   string prefix=StatePrefix();
   int stored_key=(GlobalVariableCheck(prefix+".DAY") ? (int)GlobalVariableGet(prefix+".DAY") : 0);
   if(stored_key==key && GlobalVariableCheck(prefix+".BASE"))
   {
      g_day_start_balance=GlobalVariableGet(prefix+".BASE");
      g_locked=GlobalVariableCheck(prefix+".LOCK") && GlobalVariableGet(prefix+".LOCK")>0.5;
   }
   else
   {
      double realized=ManagedClosedPnL(start,now);
      g_day_start_balance=MathMax(0.01,AccountInfoDouble(ACCOUNT_BALANCE)-realized);
      g_locked=false;
   }
   g_day_key=key;
   g_day_start=start;
   g_announced=false;
   SaveState();
}

void FlattenManagedExposure()
{
   g_trade.SetExpertMagicNumber((ulong)InpGuardMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);

   if(InpDeleteManagedPendingOrders)
   {
      for(int index=OrdersTotal()-1;index>=0;index--)
      {
         ulong ticket=OrderGetTicket(index);
         if(ticket==0 || !ManagedMagic(OrderGetInteger(ORDER_MAGIC))) continue;
         if(!g_trade.OrderDelete(ticket))
            Print("Daily Guard could not delete order ",ticket,": ",g_trade.ResultRetcodeDescription());
      }
   }

   if(InpCloseManagedPositions)
   {
      for(int index=PositionsTotal()-1;index>=0;index--)
      {
         ulong ticket=PositionGetTicket(index);
         if(ticket==0 || !ManagedMagic(PositionGetInteger(POSITION_MAGIC))) continue;
         if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
            Print("Daily Guard could not close position ",ticket,": ",g_trade.ResultRetcodeDescription());
      }
   }
}

void EvaluateGuard()
{
   datetime now=ServerNow();
   LoadOrResetDay(now);
   if(!InpEnableDailyGuard) return;

   double realized=ManagedClosedPnL(g_day_start,now);
   double floating=(InpIncludeFloatingPnL ? ManagedFloatingPnL() : 0.0);
   double day_pnl=realized+floating;
   double profit_limit=g_day_start_balance*InpDailyProfitLimitPct/100.0;
   double loss_limit=g_day_start_balance*InpDailyLossLimitPct/100.0;

   if(!g_locked)
   {
      bool profit_hit=InpDailyProfitLimitPct>0.0 && day_pnl>=profit_limit;
      bool loss_hit=InpDailyLossLimitPct>0.0 && day_pnl<=-loss_limit;
      if(profit_hit || loss_hit)
      {
         g_locked=true;
         SaveState();
         Print("PORTFOLIO DAILY LOCK: ",(profit_hit ? "profit" : "loss"),
               " threshold reached. Managed P/L=",DoubleToString(day_pnl,2),
               ", start balance=",DoubleToString(g_day_start_balance,2));
      }
   }

   if(g_locked)
   {
      FlattenManagedExposure();
      if(!g_announced)
      {
         Alert("HAMA BAT daily lock is active until the next broker day. Managed P/L: ",DoubleToString(day_pnl,2));
         g_announced=true;
      }
   }

   string state=(g_locked ? "LOCKED" : "ACTIVE");
   Comment("HAMA Portfolio Daily Guard — ",state,
           "\nBroker day: ",IntegerToString(g_day_key),
           "\nStart balance: ",DoubleToString(g_day_start_balance,2),
           "\nManaged realized: ",DoubleToString(realized,2),
           "\nManaged floating: ",DoubleToString(floating,2),
           "\nManaged day P/L: ",DoubleToString(day_pnl,2),
           "\nProfit lock: +",DoubleToString(profit_limit,2)," (",DoubleToString(InpDailyProfitLimitPct,2),"%)",
           "\nLoss lock: -",DoubleToString(loss_limit,2)," (",DoubleToString(InpDailyLossLimitPct,2),"%)");
}

int OnInit()
{
   if(InpDailyProfitLimitPct<0.0 || InpDailyLossLimitPct<0.0 || InpMaximumDeviationPoints<0)
      return INIT_PARAMETERS_INCORRECT;
   if(!ParseManagedMagics())
   {
      Print("Daily Guard has no valid managed magic numbers.");
      return INIT_PARAMETERS_INCORRECT;
   }
   g_trade.SetExpertMagicNumber((ulong)InpGuardMagic);
   EventSetMillisecondTimer(500);
   EvaluateGuard();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

void OnTimer()
{
   EvaluateGuard();
}

void OnTick()
{
   EvaluateGuard();
}
