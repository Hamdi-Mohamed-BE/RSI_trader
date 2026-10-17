#property strict
int RangeProbe(datetime start_time,int count){return 1;}
string RangeProbe(datetime start_time,datetime end_time){return "date-range";}
int RangeProbe(int start_pos,int count){return 2;}
void OnStart(){
 datetime event=(datetime)1791981000;
 int ambiguous_impulse=RangeProbe(event,event+59);
 int explicit_range=RangeProbe((datetime)event,(datetime)(event+59));
 int ambiguous_pre=RangeProbe(event-900,event-1);
 Print(ambiguous_impulse,explicit_range,ambiguous_pre);
}
