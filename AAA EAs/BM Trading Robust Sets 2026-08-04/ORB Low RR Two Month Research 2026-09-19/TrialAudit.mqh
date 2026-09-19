// Read-only instrumentation of the tester account; it never sends or changes orders.
#property strict
input string InpTrialAuditCase="orb-audit";
input double InpTrialTargetPercent=10.0;
int trial_day=0,trial_file=INVALID_HANDLE,trial_entry_day=0,trial_entry_days=0;
double trial_day_balance=10000.0,trial_day_min=10000.0,trial_min=10000.0;
double trial_previous_balance=10000.0;
double trial_day_max_margin=0.0,trial_worst_day_loss=0.0;
datetime trial_first_breach=0,trial_first_target=0;
string trial_breach_type="none";
ulong trial_last_position=0;

int TrialDay(const datetime when)
  {
   // All dates in this specific July--September 2026 study use Prague UTC+2.
   return (int)(((long)when+7200)/86400);
  }

void TrialWriteDay()
  {
   if(trial_day==0 || trial_file==INVALID_HANDLE) return;
   double loss=MathMax(0.0,trial_day_balance-trial_day_min);
   trial_worst_day_loss=MathMax(trial_worst_day_loss,loss);
   FileWrite(trial_file,TimeToString((datetime)(trial_day*86400),TIME_DATE),
             DoubleToString(trial_day_balance,2),DoubleToString(trial_day_min,2),
             DoubleToString(loss,2),DoubleToString(trial_previous_balance,2),
             DoubleToString(trial_day_max_margin,2));
  }

int TrialAuditInit()
  {
   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   trial_day_balance=AccountInfoDouble(ACCOUNT_BALANCE);
   trial_previous_balance=trial_day_balance;
   trial_day_min=trial_day_balance;
   trial_min=trial_day_balance;
   trial_file=FileOpen(InpTrialAuditCase+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,';');
   if(trial_file==INVALID_HANDLE) return INIT_FAILED;
   FileWrite(trial_file,"prague_day","start_balance","min_equity","daily_loss_usd","end_balance","max_margin_usd");
   return INIT_SUCCEEDED;
  }

void TrialAuditObserve()
  {
   if(trial_file==INVALID_HANDLE) return;
   datetime now=TimeCurrent();
   int day=TrialDay(now);
   double balance=AccountInfoDouble(ACCOUNT_BALANCE),equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(day!=trial_day)
     {
      TrialWriteDay();
      trial_day=day;
      trial_day_balance=trial_previous_balance;
      trial_day_min=equity;
      trial_day_max_margin=0.0;
     }
   trial_day_min=MathMin(trial_day_min,equity);
   trial_min=MathMin(trial_min,equity);
   trial_day_max_margin=MathMax(trial_day_max_margin,AccountInfoDouble(ACCOUNT_MARGIN));
   if(trial_first_breach==0 && (equity<trial_day_balance-500.000001 || equity<8999.999999))
     {
      trial_first_breach=now;
      trial_breach_type=(equity<8999.999999 ? "total_loss" : "daily_loss");
     }
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || ticket==trial_last_position) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic || PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      trial_last_position=ticket;
      int opened_day=TrialDay((datetime)PositionGetInteger(POSITION_TIME));
      if(opened_day!=trial_entry_day)
        {
         trial_entry_day=opened_day;
         trial_entry_days++;
        }
     }
   if(trial_first_target==0 && PositionsTotal()==0 && OrdersTotal()==0 && trial_entry_days>=4 &&
      balance>=10000.0*(1.0+InpTrialTargetPercent/100.0))
      trial_first_target=now;
   trial_previous_balance=balance;
  }

void TrialAuditFinish()
  {
   if(trial_file==INVALID_HANDLE) return;
   TrialWriteDay();
   FileClose(trial_file);
   trial_file=INVALID_HANDLE;
   PrintFormat("TRIAL_AUDIT|%s|final=%.2f|min_equity=%.2f|worst_daily_loss=%.2f|entry_days=%d|first_breach=%I64d|breach_type=%s|first_target=%I64d",
               InpTrialAuditCase,AccountInfoDouble(ACCOUNT_BALANCE),trial_min,trial_worst_day_loss,
               trial_entry_days,(long)trial_first_breach,trial_breach_type,(long)trial_first_target);
  }
