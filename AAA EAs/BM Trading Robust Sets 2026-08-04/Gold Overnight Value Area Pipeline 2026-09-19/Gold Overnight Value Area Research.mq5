#property strict
#property version "1.10"
#include <Trade/Trade.mqh>
// Research-only. No active EA/includes/SETs are modified.
input int InpEntryEndMinute=960; // New York minutes after midnight
input int InpExitMinute=960;
input int InpStopMode=0; // 0=opposite value area, 1=POC
input double InpMinimumR=0;
input double InpTargetR=0; // 0=overnight extreme
input double InpBreakEvenR=0;
input double InpTrailDistanceR=0; // activate at 1R, closed-M5 trailing
double pipeline_initial_risk=0;
datetime pipeline_trail_bar=0;
input int InpDirectionMode=0; // 0=value area, 1=POC
input int InpBins=64;
input double InpValueAreaPercent=70;
input int InpMinimumProfileBars=120;
input double InpRiskPercent=1;
input int InpServerUTCOffsetHours=0;
input long InpExpectedLogin=0;
input string InpExpectedServer="";
input long InpMagic=89191901;
input string InpCase="raw";
CTrade trade;
int daykey=0,days=0,profiles=0,missing=0,signals=0,entries=0,geometry=0,rejected=0,closes=0;
bool consumed=false,ready=false,attempted=false;
datetime bar_seen=0,cutoff=0;
double hi=0,lo=0,poc=0,vah=0,val=0,min_equity=DBL_MAX,peak_equity=0,max_dd=0;
int audit_file=INVALID_HANDLE;

int Sunday(int year,int month,int nth) {
 MqlDateTime t={0};t.year=year;t.mon=month;t.day=1;t.hour=12;
 datetime d=StructToTime(t);TimeToStruct(d,t);return 1+(7-t.day_of_week)%7+(nth-1)*7;
}
int NYOffset(datetime utc) {
 MqlDateTime t;TimeToStruct(utc,t);
 MqlDateTime a={0},b={0};a.year=t.year;a.mon=3;a.day=Sunday(t.year,3,2);a.hour=7;
 b.year=t.year;b.mon=11;b.day=Sunday(t.year,11,1);b.hour=6;
 return utc>=StructToTime(a) && utc<StructToTime(b) ? -4 : -5;
}
datetime ToNY(datetime server) {datetime u=server-InpServerUTCOffsetHours*3600;return u+NYOffset(u)*3600;}
datetime FromNY(datetime wall) {
 // Session boundaries are 18:00/09:30/16:00, never the ambiguous DST hour.
 datetime u=wall+5*3600;return wall-NYOffset(u)*3600+InpServerUTCOffsetHours*3600;
}
int Key(datetime wall) {MqlDateTime t;TimeToStruct(wall,t);return t.year*10000+t.mon*100+t.day;}
datetime Midnight(datetime t) {MqlDateTime d;TimeToStruct(t,d);d.hour=0;d.min=0;d.sec=0;return StructToTime(d);}
double Price(double p) {double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/tick)*tick,_Digits);}
bool OwnPosition(ulong &id) {
 for(int i=PositionsTotal()-1;i>=0;i--) {ulong p=PositionGetTicket(i);
  if(p && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){id=p;return true;}}
 return false;
}
void Audit(string kind,datetime when,int side=0,double entry=0,double stop=0,double target=0,double lots=0,double risk=0) {
 if(audit_file==INVALID_HANDLE)return;
 FileWrite(audit_file,kind,(long)when,daykey,side,hi,lo,poc,vah,val,entry,stop,target,lots,risk,(long)cutoff);
 FileFlush(audit_file);
}
datetime Cutoff(datetime today) {
 datetime desired=FromNY(today+InpExitMinute*60),base=Midnight(desired);
 MqlDateTime d;TimeToStruct(desired,d);datetime a,b;long last=0;
 for(uint i=0;i<20;i++) {
  if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,a,b))break;
  long end=(long)b; if(end==0 && (long)a>0)end=86400;
  last=MathMax(last,end);
 }
 if(last>0)desired=(datetime)MathMin((long)desired,(long)base+last-60);
 return desired;
}
bool BuildProfile(datetime today) {
 datetime start=FromNY(today-86400+18*3600),finish=FromNY(today+9*3600+30*60);
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_M1,start,finish-1,r);
 if(n<InpMinimumProfileBars){Audit("missing_profile",TimeCurrent());return false;}
 hi=-DBL_MAX;lo=DBL_MAX;
 for(int i=0;i<n;i++){if(r[i].time<start || r[i].time+60>finish)return false;hi=MathMax(hi,r[i].high);lo=MathMin(lo,r[i].low);}
 if(hi<=lo)return false;
 double bins[];ArrayResize(bins,InpBins);ArrayInitialize(bins,0);
 double width=(hi-lo)/InpBins,total=0;
 for(int i=0;i<n;i++) {
  double typical=(r[i].high+r[i].low+r[i].close)/3;
  int b=(int)MathFloor((typical-lo)/width);b=MathMax(0,MathMin(InpBins-1,b));
  bins[b]+=(double)r[i].tick_volume;total+=(double)r[i].tick_volume;
 }
 if(total<=0)return false;
 int p=0;for(int i=1;i<InpBins;i++)if(bins[i]>bins[p])p=i;
 int left=p,right=p;double covered=bins[p];
 while(covered<total*InpValueAreaPercent/100 && (left>0 || right<InpBins-1)) {
  double below=left>0?bins[left-1]:-1,above=right<InpBins-1?bins[right+1]:-1;
  if(above>=below && right<InpBins-1){right++;covered+=bins[right];}else{left--;covered+=bins[left];}
 }
 poc=Price(lo+(p+.5)*width);val=Price(lo+left*width);vah=Price(lo+(right+1)*width);
 Audit("profile",TimeCurrent());double eps=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 return lo-eps<=val && val<=poc && poc<=vah && vah<=hi+eps;
}
void Manage(datetime now) {
 ulong id;if(!OwnPosition(id))return;
 datetime entered=(datetime)PositionGetInteger(POSITION_TIME);
 if((InpBreakEvenR>0 || InpTrailDistanceR>0) && pipeline_initial_risk>0) {
  MqlTick tick;if(SymbolInfoTick(_Symbol,tick)) {
   int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
   double market=side>0?tick.bid:tick.ask,progress=side*(market-entry)/pipeline_initial_risk,candidate=sl;
   if(InpBreakEvenR>0 && progress>=InpBreakEvenR)candidate=side>0?MathMax(candidate,entry):MathMin(candidate,entry);
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(InpTrailDistanceR>0 && progress>=1 && current!=pipeline_trail_bar) {
    pipeline_trail_bar=current;MqlRates bar[];
    if(CopyRates(_Symbol,PERIOD_M5,1,1,bar)==1) {
     double level=bar[0].close-side*InpTrailDistanceR*pipeline_initial_risk;
     candidate=side>0?MathMax(candidate,level):MathMin(candidate,level);
    }
   }
   candidate=Price(candidate);
   double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(side*(candidate-sl)>0 && side*(market-candidate)>minimum)trade.PositionModify(id,candidate,tp);
  }
 }
 if(now>=cutoff || Key(ToNY(entered))!=Key(ToNY(now))) {
  if(trade.PositionClose(id)){closes++;Audit("timed_exit",now);}
 }
}
void OnTick() {
 datetime now=TimeCurrent(),ny=ToNY(now),today=Midnight(ny);
 double equity=AccountInfoDouble(ACCOUNT_EQUITY);min_equity=MathMin(min_equity,equity);peak_equity=MathMax(peak_equity,equity);
 if(peak_equity>0)max_dd=MathMax(max_dd,100*(peak_equity-equity)/peak_equity);
 if(Key(ny)!=daykey) {
  daykey=Key(ny);consumed=false;ready=false;attempted=false;bar_seen=0;cutoff=Cutoff(today);
  MqlDateTime d;TimeToStruct(ny,d);if(d.day_of_week>=1 && d.day_of_week<=5)days++;
 }
 Manage(now);
 MqlDateTime d;TimeToStruct(ny,d);if(d.day_of_week==0 || d.day_of_week==6)return;
 datetime open=FromNY(today+9*3600+30*60);
 if(now<open || now>=cutoff || now>=FromNY(today+InpEntryEndMinute*60))return;
 if(!attempted){attempted=true;ready=BuildProfile(today);if(ready)profiles++;else missing++;}
 if(!ready || consumed)return;
 ulong id;if(OwnPosition(id))return;
 datetime current=iTime(_Symbol,PERIOD_M5,0);if(current==bar_seen)return;bar_seen=current;
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1)return;
 if(r[0].time<open || r[0].time+300>now)return;
 int side=0;
 if(InpDirectionMode==0){if(r[0].close>vah)side=1;else if(r[0].close<val)side=-1;}
 else {if(r[0].close>poc)side=1;else if(r[0].close<poc)side=-1;}
 if(side==0)return;
 consumed=true;signals++;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)){rejected++;return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double anchor=InpStopMode==1?poc:(side>0?val:vah);
 double entry=side>0?tick.ask:tick.bid,stop=Price(anchor-side*step),target=Price(side>0?hi:lo);
 if(InpTargetR>0)target=Price(entry+side*InpTargetR*MathAbs(entry-stop));
 double min_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 // Broker validates buys against Bid, sells against Ask.
 bool valid=side>0 ? (stop<tick.bid-min_distance && target>entry+min_distance) : (stop>tick.ask+min_distance && target<entry-min_distance);
 if(!valid || side*(entry-stop)<=0 || MathAbs(target-entry)/MathAbs(entry-stop)<InpMinimumR){geometry++;Audit("invalid_geometry",now,side,entry,stop,target);return;}
 ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double unit=0;if(!OrderCalcProfit(type,_Symbol,1,entry,stop,unit) || unit>=0){rejected++;return;}
 double desired=equity*InpRiskPercent/100,lotstep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=MathCeil(desired/MathAbs(unit)/lotstep-1e-10)*lotstep;
 lots=NormalizeDouble(MathMin(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),lots)),8);
 double margin=0;if(!OrderCalcMargin(type,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){
  rejected++;Audit("margin_rejected",now,side,entry,stop,target,lots,MathAbs(unit)*lots);return;}
 bool sent=side>0?trade.Buy(lots,_Symbol,0,stop,target,"ONVP VA/POC"):trade.Sell(lots,_Symbol,0,stop,target,"ONVP VA/POC");
 if(sent && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL)) {
  pipeline_initial_risk=MathAbs(trade.ResultPrice()-stop);pipeline_trail_bar=0;
  entries++;Audit("entry",now,side,entry,stop,target,lots,MathAbs(unit)*lots);
 }else {rejected++;Audit("order_rejected",now,side,entry,stop,target,lots,MathAbs(unit)*lots);Print("ONVP_REJECT|",trade.ResultRetcode(),"|",trade.ResultRetcodeDescription());}
}
int OnInit() {
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpExpectedLogin<=0 || AccountInfoInteger(ACCOUNT_LOGIN)!=InpExpectedLogin || AccountInfoString(ACCOUNT_SERVER)!=InpExpectedServer)return INIT_FAILED;
 if(InpDirectionMode<0 || InpDirectionMode>1 || InpBins<2 || InpRiskPercent<=0 || InpEntryEndMinute<=575 || InpExitMinute<=575 || InpStopMode<0 || InpStopMode>1)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(50);
 audit_file=FileOpen(InpCase+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(audit_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit_file,"kind","server_epoch","ny_day","side","high","low","poc","vah","val","requested_entry","stop","target","lots","planned_cash_risk","cutoff_epoch");
 peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);min_equity=peak_equity;
 Print("ONVP_SPEC|",_Symbol,"|contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),"|tick=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),"|login=",AccountInfoInteger(ACCOUNT_LOGIN),"|server=",AccountInfoString(ACCOUNT_SERVER));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) {
 if(audit_file!=INVALID_HANDLE)FileClose(audit_file);
 PrintFormat("ONVP_SUMMARY|%s|days=%d|profiles=%d|missing=%d|signals=%d|entries=%d|invalid_geometry=%d|rejected=%d|timed_exits=%d|min_equity=%.2f|max_equity_dd=%.6f|balance=%.2f",InpCase,days,profiles,missing,signals,entries,geometry,rejected,closes,min_equity,max_dd,AccountInfoDouble(ACCOUNT_BALANCE));
}
