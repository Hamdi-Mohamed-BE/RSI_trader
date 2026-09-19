#property strict
#property version "1.00"
#property description "Research-only mark-to-market audit of saved tester fills. Never sends orders."
#property tester_file "calyx-nasdaq075-equity-input-20260919.csv"

struct AuditTrade
  {
   datetime entered,exited;
   int direction;
   double lots,price,entry_cash,exit_cash;
  };
AuditTrade g_trades[];
int g_index=0,g_day=0,g_output=INVALID_HANDLE;
bool g_active=false;
double g_balance=10000.0,g_day_balance=10000.0,g_day_min=10000.0;
double g_min_equity=10000.0,g_worst_day=0.0;
int g_daily_breaches=0,g_total_breaches=0;

void Observe(const double equity)
  {
   g_day_min=MathMin(g_day_min,equity);
   g_min_equity=MathMin(g_min_equity,equity);
  }

void FinishDay()
  {
   if(g_day==0) return;
   double loss=MathMax(0.0,g_day_balance-g_day_min);
   g_worst_day=MathMax(g_worst_day,loss);
   bool daily=(loss>500.000001),total=(g_day_min<9000.0-0.000001);
   if(daily) g_daily_breaches++;
   if(total) g_total_breaches++;
   FileWrite(g_output,g_day,DoubleToString(g_day_balance,2),DoubleToString(g_day_min,2),
             DoubleToString(loss,2),DoubleToString(g_balance,2),(int)daily,(int)total);
  }

int OnInit()
  {
   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   int audit_file=FileOpen("calyx-nasdaq075-equity-input-20260919.csv",FILE_READ|FILE_CSV|FILE_ANSI,';');
   if(audit_file==INVALID_HANDLE) return INIT_FAILED;
   while(!FileIsEnding(audit_file))
     {
      string first=FileReadString(audit_file);
      if(first=="") break;
      int n=ArraySize(g_trades);
      ArrayResize(g_trades,n+1);
      g_trades[n].entered=(datetime)StringToInteger(first);
      g_trades[n].exited=(datetime)FileReadNumber(audit_file);
      g_trades[n].direction=(int)FileReadNumber(audit_file);
      g_trades[n].lots=FileReadNumber(audit_file);
      g_trades[n].price=FileReadNumber(audit_file);
      g_trades[n].entry_cash=FileReadNumber(audit_file);
      g_trades[n].exit_cash=FileReadNumber(audit_file);
     }
   FileClose(audit_file);
   if(ArraySize(g_trades)!=45) return INIT_FAILED;
   g_output=FileOpen("calyx-nasdaq075-equity-days-20260919.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,';');
   if(g_output==INVALID_HANDLE) return INIT_FAILED;
   FileWrite(g_output,"prague_day","day_start_balance","minimum_equity","daily_loss_usd","day_end_balance","daily_breach","total_breach");
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   // Europe/Prague is UTC+2 throughout 19 July--18 September 2026.
   MqlDateTime date;
   TimeToStruct(TimeCurrent()+2*3600,date);
   int day=date.year*10000+date.mon*100+date.day;
   if(day!=g_day)
     {
      FinishDay();
      g_day=day;
      g_day_balance=g_balance;
      g_day_min=g_balance;
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   while(g_index<ArraySize(g_trades))
     {
      if(!g_active)
        {
         if(tick.time<g_trades[g_index].entered) break;
         g_balance+=g_trades[g_index].entry_cash;
         g_active=true;
        }
      double price=(g_trades[g_index].direction>0 ? tick.bid : tick.ask);
      double floating=g_trades[g_index].direction*(price-g_trades[g_index].price)*g_trades[g_index].lots;
      Observe(g_balance+NormalizeDouble(floating,2));
      if(tick.time<g_trades[g_index].exited) break;
      g_balance+=g_trades[g_index].exit_cash;
      Observe(g_balance);
      g_active=false;
      g_index++;
     }
   if(!g_active) Observe(g_balance);
  }

void OnDeinit(const int reason)
  {
   if(g_output!=INVALID_HANDLE)
     {
      FinishDay();
      FileClose(g_output);
     }
   PrintFormat("Calyx equity audit: closed=%d, active=%d, balance=%.2f, min_equity=%.2f, worst_daily_loss=%.2f, daily_breaches=%d, total_breaches=%d",
               g_index,(int)g_active,g_balance,g_min_equity,g_worst_day,g_daily_breaches,g_total_breaches);
  }
