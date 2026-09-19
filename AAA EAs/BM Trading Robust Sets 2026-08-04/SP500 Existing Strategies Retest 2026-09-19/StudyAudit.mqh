// Research-only observation. Never sends or modifies an order.
#property strict
input string InpStudyCase="sp500-study";
input long InpStudyLogin=0;
input string InpStudyServer="";
double study_peak=0,study_dd=0,study_min=0,study_margin=0;
double study_day_min=0,study_day_peak=0;
int study_file=INVALID_HANDLE;
datetime study_day=0;
bool StudyGuard()
{
   return (bool)MQLInfoInteger(MQL_TESTER) &&
          AccountInfoInteger(ACCOUNT_LOGIN)==InpStudyLogin &&
          AccountInfoString(ACCOUNT_SERVER)==InpStudyServer && _Symbol=="US500";
}
void StudyWriteDay()
{
   if(study_day==0 || study_file==INVALID_HANDLE) return;
   FileWrite(study_file,TimeToString(study_day,TIME_DATE),
             DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),
             DoubleToString(study_day_min,2),DoubleToString(study_day_peak,2));
}
int StudyInit()
{
   if(!StudyGuard()) return INIT_FAILED;
   study_peak=AccountInfoDouble(ACCOUNT_EQUITY);study_min=study_peak;
   study_file=FileOpen(InpStudyCase+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,';');
   if(study_file==INVALID_HANDLE) return INIT_FAILED;
   FileWrite(study_file,"utc_day","balance_at_observation","min_equity","max_equity");
   return INIT_SUCCEEDED;
}
void StudyObserve()
{
   if(study_file==INVALID_HANDLE) return;
   double e=AccountInfoDouble(ACCOUNT_EQUITY);
   study_peak=MathMax(study_peak,e);study_min=MathMin(study_min,e);
   if(study_peak>0)study_dd=MathMax(study_dd,100.0*(study_peak-e)/study_peak);
   study_margin=MathMax(study_margin,AccountInfoDouble(ACCOUNT_MARGIN));
   datetime day=(datetime)(((long)TimeCurrent()/86400)*86400);
   if(day!=study_day){StudyWriteDay();study_day=day;study_day_min=e;study_day_peak=e;}
   study_day_min=MathMin(study_day_min,e);study_day_peak=MathMax(study_day_peak,e);
}
void StudyFinish()
{
   StudyObserve();StudyWriteDay();
   if(study_file!=INVALID_HANDLE){FileClose(study_file);study_file=INVALID_HANDLE;}
   PrintFormat("SP500_AUDIT|%s|final=%.2f|min_equity=%.2f|equity_dd=%.8f|max_margin=%.2f",
               InpStudyCase,AccountInfoDouble(ACCOUNT_BALANCE),study_min,study_dd,study_margin);
}
