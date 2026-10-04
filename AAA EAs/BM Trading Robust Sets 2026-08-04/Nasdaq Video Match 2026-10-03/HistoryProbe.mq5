#property strict
#property description "Isolated tester-only Nasdaq history availability probe; no orders."
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return INIT_SUCCEEDED;}
void OnTick(){
 long first=0;SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_FIRSTDATE,first);
 PrintFormat("VIDEO_MATCH_HISTORY symbol=%s first_m1=%s first_tick=%s",_Symbol,TimeToString((datetime)first,TIME_DATE|TIME_MINUTES),TimeToString(TimeCurrent(),TIME_DATE|TIME_MINUTES));
 TesterStop();
}
