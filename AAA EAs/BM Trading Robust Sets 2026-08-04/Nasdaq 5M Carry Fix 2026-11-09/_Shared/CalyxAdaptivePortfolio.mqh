#ifndef CALYX_ADAPTIVE_PORTFOLIO_MQH
#define CALYX_ADAPTIVE_PORTFOLIO_MQH

// Native live implementation of the Recommended Adaptive portfolio governor.
// It changes entry risk only. Existing positions and their stops are never altered.
const double CALYX_DAILY_STOP_PERCENT=5.0;   // $500 on the website's $10,000 reference balance
const double CALYX_SOFT_DRAWDOWN_PERCENT=4.0;
const double CALYX_HARD_DRAWDOWN_PERCENT=7.0;
const int    CALYX_SOFT_LOSS_STREAK=3;
const int    CALYX_HARD_LOSS_STREAK=5;

double g_calyx_last_adaptive_multiplier=-1.0;
datetime g_calyx_last_adaptive_log=0;

double CalyxDealCashDelta(const ulong ticket)
{
   if(ticket==0) return 0.0;
   return HistoryDealGetDouble(ticket,DEAL_PROFIT)+
          HistoryDealGetDouble(ticket,DEAL_COMMISSION)+
          HistoryDealGetDouble(ticket,DEAL_SWAP)+
          HistoryDealGetDouble(ticket,DEAL_FEE);
}

datetime CalyxServerDayStart(const datetime now)
{
   MqlDateTime parts={};
   if(!TimeToStruct(now,parts)) return now;
   parts.hour=0;
   parts.min=0;
   parts.sec=0;
   return StructToTime(parts);
}

double CalyxDailyClosedTradingPL(const datetime now)
{
   if(now<=0 || !HistorySelect(CalyxServerDayStart(now),now)) return 0.0;
   double total=0.0;
   const int count=HistoryDealsTotal();
   for(int i=0;i<count;i++)
   {
      const ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0) continue;
      const ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(ticket,DEAL_TYPE);
      if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL) continue;
      total+=CalyxDealCashDelta(ticket);
   }
   return total;
}

string CalyxPeakKey()
{
   return "CALYX_ADAPTIVE_PEAK_V1_"+
          IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
}

string CalyxReferenceBalanceKey()
{
   return "CALYX_ADAPTIVE_REFERENCE_V1_"+
          IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
}

double CalyxReferenceBalance(const datetime now,const double current_balance)
{
   const string key=CalyxReferenceBalanceKey();
   if(GlobalVariableCheck(key) && GlobalVariableGet(key)>0.0) return GlobalVariableGet(key);

   double reference=current_balance;
   if(now>0 && HistorySelect(0,now))
   {
      const int count=HistoryDealsTotal();
      double all_delta=0.0;
      for(int i=0;i<count;i++) all_delta+=CalyxDealCashDelta(HistoryDealGetTicket(i));
      double running=current_balance-all_delta;
      if(running>0.0) reference=running;
      else
      {
         for(int i=0;i<count;i++)
         {
            running+=CalyxDealCashDelta(HistoryDealGetTicket(i));
            if(running>0.0)
            {
               reference=running;
               break;
            }
         }
      }
   }
   if(reference<=0.0) reference=current_balance;
   if(reference>0.0) GlobalVariableSet(key,reference);
   return reference;
}

double CalyxHistoricalClosedBalancePeak(const datetime now,const double current_balance)
{
   double peak=current_balance;
   if(now>0 && HistorySelect(0,now))
   {
      const int count=HistoryDealsTotal();
      double all_delta=0.0;
      for(int i=0;i<count;i++)
         all_delta+=CalyxDealCashDelta(HistoryDealGetTicket(i));

      double running=current_balance-all_delta;
      peak=MathMax(peak,running);
      for(int i=0;i<count;i++)
      {
         running+=CalyxDealCashDelta(HistoryDealGetTicket(i));
         peak=MathMax(peak,running);
      }
   }

   const string key=CalyxPeakKey();
   if(GlobalVariableCheck(key)) peak=MathMax(peak,GlobalVariableGet(key));
   if(!GlobalVariableCheck(key) || peak>GlobalVariableGet(key)) GlobalVariableSet(key,peak);
   return peak;
}

bool CalyxPositionIdentifierIsOpen(const long position_id)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(PositionGetTicket(i)==0) continue;
      if(PositionGetInteger(POSITION_IDENTIFIER)==position_id) return true;
   }
   return false;
}

bool CalyxPositionWasSeen(const long position_id,const long &seen[],const int seen_count)
{
   for(int i=0;i<seen_count;i++)
      if(seen[i]==position_id) return true;
   return false;
}

double CalyxClosedPositionNet(const long position_id)
{
   double total=0.0;
   const int count=HistoryDealsTotal();
   for(int i=0;i<count;i++)
   {
      const ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 || HistoryDealGetInteger(ticket,DEAL_POSITION_ID)!=position_id) continue;
      total+=CalyxDealCashDelta(ticket);
   }
   return total;
}

int CalyxConsecutiveLosses(const long magic,const datetime now)
{
   if(magic<=0 || now<=0 || !HistorySelect(0,now)) return 0;
   long seen[16];
   ArrayInitialize(seen,0);
   int seen_count=0;
   int losses=0;
   for(int i=HistoryDealsTotal()-1;i>=0 && seen_count<ArraySize(seen);i--)
   {
      const ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 || HistoryDealGetInteger(ticket,DEAL_MAGIC)!=magic) continue;
      const ENUM_DEAL_ENTRY entry_kind=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket,DEAL_ENTRY);
      if(entry_kind!=DEAL_ENTRY_OUT && entry_kind!=DEAL_ENTRY_INOUT && entry_kind!=DEAL_ENTRY_OUT_BY) continue;
      const long position_id=HistoryDealGetInteger(ticket,DEAL_POSITION_ID);
      if(position_id<=0 || CalyxPositionWasSeen(position_id,seen,seen_count) || CalyxPositionIdentifierIsOpen(position_id)) continue;
      seen[seen_count++]=position_id;
      const double net=CalyxClosedPositionNet(position_id);
      if(net<-0.005)
      {
         losses++;
         if(losses>=CALYX_HARD_LOSS_STREAK) break;
      }
      else if(net>0.005)
         break;
      else
         break;
   }
   return losses;
}

void CalyxLogAdaptiveDecision(const double multiplier,const double daily_pl,
                              const double drawdown_pct,const int loss_streak)
{
   const datetime now=TimeLocal();
   if(MathAbs(multiplier-g_calyx_last_adaptive_multiplier)<0.000001 &&
      g_calyx_last_adaptive_log>0 && now-g_calyx_last_adaptive_log<900) return;
   if(multiplier<=0.0)
      PrintFormat("Calyx Adaptive: new entry blocked by the daily closed-P/L stop (today %.2f).",daily_pl);
   else if(multiplier<0.999999)
      PrintFormat("Calyx Adaptive: entry risk multiplier %.4f (closed DD %.2f%%, EA loss streak %d).",
                  multiplier,drawdown_pct,loss_streak);
   g_calyx_last_adaptive_multiplier=multiplier;
   g_calyx_last_adaptive_log=now;
}

double CalyxAdaptiveRiskMultiplier(const bool enabled,const long magic)
{
   if(!enabled) return 1.0;
   datetime now=TimeCurrent();
   if(now<=0) now=TimeLocal();

   const double current_balance=AccountInfoDouble(ACCOUNT_BALANCE);
   const double daily_pl=CalyxDailyClosedTradingPL(now);
   const double reference_balance=CalyxReferenceBalance(now,current_balance);
   if(reference_balance>0.0 && daily_pl<=-(reference_balance*CALYX_DAILY_STOP_PERCENT/100.0))
   {
      CalyxLogAdaptiveDecision(0.0,daily_pl,0.0,0);
      return 0.0;
   }

   const double peak=CalyxHistoricalClosedBalancePeak(now,current_balance);
   const double drawdown_pct=(peak>0.0 ? 100.0*(peak-current_balance)/peak : 0.0);
   double multiplier=1.0;
   if(drawdown_pct>=CALYX_HARD_DRAWDOWN_PERCENT) multiplier*=0.25;
   else if(drawdown_pct>=CALYX_SOFT_DRAWDOWN_PERCENT) multiplier*=0.50;

   const int loss_streak=CalyxConsecutiveLosses(magic,now);
   if(loss_streak>=CALYX_HARD_LOSS_STREAK) multiplier*=0.25;
   else if(loss_streak>=CALYX_SOFT_LOSS_STREAK) multiplier*=0.50;

   CalyxLogAdaptiveDecision(multiplier,daily_pl,drawdown_pct,loss_streak);
   return multiplier;
}

#endif
