#property strict
#property version "1.10"
#include <Trade/Trade.mqh>
// Research-only (2026-09-23). Based on Overnight Profile Raw Comparison 2026-09-19/Overnight Profile Raw.mq5.
// No active EA/includes/SETs are modified.
//
// Rules requested by the user 2026-09-23:
// - Profile: Asia open (00:00 UTC) to 09:30 New York, 64 bins, M1 HLC3 x broker tick volume, 70% value area.
// - Entry mode 0: only the 09:30-09:35 NY M5 candle; close above VAH buys, below VAL sells, inside = no trade.
//   Entry mode 1: first M5 close outside the value area from 09:30 NY until 16:00 NY (or broker session end).
// - Initial stop: opposite end of the signal candle, one tick beyond. No take-profit.
// - Trailing: after every later closed M5 candle, move the stop to that candle's low (long) / high (short)
//   minus/plus one tick, only when tighter. No time exit: the trade lives until the stop is hit.
// - One position; a new day's signal is skipped while a position is still open. Weekdays only for entries.
// v1.10 exit variants (defaults reproduce v1.00 exactly):
// - InpTrailStartR: trailing starts only after the best price since entry reached this many R (0 = immediately).
// - InpTrailTimeframe: candle timeframe used for trailing (M5 default).
// - InpTargetMode: 0 = no take-profit; 1 = take-profit at the overnight profile high (long) / low (short).
input int InpEntryMode=0;            // 0=first 09:30 candle only, 1=first M5 close outside until cutoff
input double InpTrailStartR=0;       // 0 = trail from the first closed candle after entry
input ENUM_TIMEFRAMES InpTrailTimeframe=PERIOD_M5;
input int InpTargetMode=0;            // 0 = none, 1 = overnight high/low
input int InpBins=64;
input double InpValueAreaPercent=70;
input int InpMinimumProfileBars=120;
input double InpRiskPercent=1;
input int InpServerUTCOffsetHours=0;
input long InpExpectedLogin=0;
input string InpExpectedServer="";
input long InpMagic=89230901;
input string InpCase="raw";
CTrade trade;
int daykey=0,days=0,profiles=0,missing=0,signals=0,entries=0,geometry=0,rejected=0,skipped_open=0;
int trail_moves=0,trail_market_exits=0,trail_rejects=0,inside_first=0;
bool consumed=false,ready=false,attempted=false;
datetime bar_seen=0,trail_bar_seen=0,cutoff=0,signal_bar=0;
double hi=0,lo=0,poc=0,vah=0,val=0,min_equity=DBL_MAX,peak_equity=0,max_dd=0;
double g_entry=0,g_risk=0,g_best=0;
int target_invalid=0,target_exits_seen=0;
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
 // Session boundaries are 09:30/16:00, never the ambiguous DST hour.
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
void Audit(string kind,datetime when,int side=0,double entry=0,double stop=0,double lots=0,double risk=0) {
 if(audit_file==INVALID_HANDLE)return;
 FileWrite(audit_file,kind,(long)when,daykey,side,hi,lo,poc,vah,val,entry,stop,lots,risk,(long)cutoff);
 FileFlush(audit_file);
}
datetime Cutoff(datetime today) {
 datetime desired=FromNY(today+16*3600),base=Midnight(desired);
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
 // Asia open = 00:00 UTC of the New York calendar date (NY 09:30 is always 13:30/14:30 UTC the same date).
 datetime start=today+InpServerUTCOffsetHours*3600,finish=FromNY(today+9*3600+30*60);
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
void Trail(datetime now) {
 ulong id;if(!OwnPosition(id))return;
 if(!PositionSelectByTicket(id))return;
 bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
 MqlTick live;if(SymbolInfoTick(_Symbol,live))g_best=(buy?MathMax(g_best,live.bid):(g_best>0?MathMin(g_best,live.ask):live.ask));
 int tf=PeriodSeconds(InpTrailTimeframe);
 datetime current=iTime(_Symbol,InpTrailTimeframe,0);if(current==trail_bar_seen)return;trail_bar_seen=current;
 MqlRates r[];if(CopyRates(_Symbol,InpTrailTimeframe,1,1,r)!=1)return;
 if(r[0].time+tf<=signal_bar+300 || r[0].time+tf>now)return;   // only candles that closed after the signal candle
 if(InpTrailStartR>0 && g_risk>0 && (buy ? g_best<g_entry+InpTrailStartR*g_risk : g_best>g_entry-InpTrailStartR*g_risk))return;
 double sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double candidate=Price(buy?r[0].low-step:r[0].high+step);
 if(buy ? candidate<=sl : (sl>0 && candidate>=sl))return;     // only tighter
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double min_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 bool breached=buy ? candidate>=tick.bid-min_distance : candidate<=tick.ask+min_distance;
 if(breached) {
  // Price is already through the new trailing level: exit at market instead of leaving the older stop.
  if(trade.PositionClose(id)){trail_market_exits++;Audit("trail_market_exit",now,buy?1:-1,0,candidate);}
  else trail_rejects++;
  return;
 }
 if(trade.PositionModify(id,candidate,tp)){trail_moves++;}
 else {trail_rejects++;Print("ONVT_TRAIL_REJECT|",trade.ResultRetcode(),"|",trade.ResultRetcodeDescription());}
}
void OnTick() {
 datetime now=TimeCurrent(),ny=ToNY(now),today=Midnight(ny);
 double equity=AccountInfoDouble(ACCOUNT_EQUITY);min_equity=MathMin(min_equity,equity);peak_equity=MathMax(peak_equity,equity);
 if(peak_equity>0)max_dd=MathMax(max_dd,100*(peak_equity-equity)/peak_equity);
 if(Key(ny)!=daykey) {
  daykey=Key(ny);consumed=false;ready=false;attempted=false;bar_seen=0;cutoff=Cutoff(today);
  MqlDateTime d;TimeToStruct(ny,d);if(d.day_of_week>=1 && d.day_of_week<=5)days++;
 }
 Trail(now);
 MqlDateTime d;TimeToStruct(ny,d);if(d.day_of_week==0 || d.day_of_week==6)return;
 datetime open=FromNY(today+9*3600+30*60);
 datetime last_entry=(InpEntryMode==0 ? open+600 : cutoff);
 if(now<open+300 || now>=last_entry || consumed)return;
 if(!attempted){attempted=true;ready=BuildProfile(today);if(ready)profiles++;else missing++;}
 if(!ready)return;
 datetime current=iTime(_Symbol,PERIOD_M5,0);if(current==bar_seen)return;bar_seen=current;
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1)return;
 if(r[0].time<open || r[0].time+300>now)return;
 if(InpEntryMode==0 && r[0].time!=open){consumed=true;return;}   // the 09:30 candle was not seen in time
 int side=0;
 if(r[0].close>vah)side=1;else if(r[0].close<val)side=-1;
 if(side==0){if(InpEntryMode==0){consumed=true;inside_first++;Audit("first_candle_inside",now);}return;}
 consumed=true;signals++;
 ulong id;if(OwnPosition(id)){skipped_open++;Audit("skipped_position_open",now,side);return;}
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)){rejected++;return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double entry=side>0?tick.ask:tick.bid,stop=Price(side>0?r[0].low-step:r[0].high+step);
 double min_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 // Broker validates buys against Bid, sells against Ask.
 bool valid=side>0 ? stop<tick.bid-min_distance : stop>tick.ask+min_distance;
 if(!valid){geometry++;Audit("invalid_geometry",now,side,entry,stop);return;}
 double target=0;
 if(InpTargetMode==1) {
  target=Price(side>0?hi:lo);
  // Target already behind the executable price: consume the signal, like the retained raw overnight EA.
  if(side>0 ? target<=entry+min_distance : target>=entry-min_distance){geometry++;target_invalid++;Audit("target_behind_entry",now,side,entry,stop);return;}
 }
 ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double unit=0;if(!OrderCalcProfit(type,_Symbol,1,entry,stop,unit) || unit>=0){rejected++;return;}
 double desired=equity*InpRiskPercent/100,lotstep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=MathCeil(desired/MathAbs(unit)/lotstep-1e-10)*lotstep;
 lots=NormalizeDouble(MathMin(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),lots)),8);
 double margin=0;if(!OrderCalcMargin(type,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){
  rejected++;Audit("margin_rejected",now,side,entry,stop,lots,MathAbs(unit)*lots);return;}
 string comment=StringFormat("ONVT m%d",InpEntryMode);
 bool sent=side>0?trade.Buy(lots,_Symbol,0,stop,target,comment):trade.Sell(lots,_Symbol,0,stop,target,comment);
 if(sent && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL)) {
  entries++;signal_bar=r[0].time;trail_bar_seen=iTime(_Symbol,InpTrailTimeframe,0);
  ulong opened;if(OwnPosition(opened) && PositionSelectByTicket(opened)){g_entry=PositionGetDouble(POSITION_PRICE_OPEN);g_risk=MathAbs(g_entry-stop);g_best=g_entry;}
  Audit("entry",now,side,entry,stop,lots,MathAbs(unit)*lots);
 }else {rejected++;Audit("order_rejected",now,side,entry,stop,lots,MathAbs(unit)*lots);Print("ONVT_REJECT|",trade.ResultRetcode(),"|",trade.ResultRetcodeDescription());}
}
int OnInit() {
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpExpectedLogin<=0 || AccountInfoInteger(ACCOUNT_LOGIN)!=InpExpectedLogin || AccountInfoString(ACCOUNT_SERVER)!=InpExpectedServer)return INIT_FAILED;
 if(InpEntryMode<0 || InpEntryMode>1 || InpBins<2 || InpRiskPercent<=0 || InpTrailStartR<0 || InpTargetMode<0 || InpTargetMode>1)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(50);
 audit_file=FileOpen(InpCase+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(audit_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit_file,"kind","server_epoch","ny_day","side","high","low","poc","vah","val","requested_entry","stop","lots","planned_cash_risk","cutoff_epoch");
 peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);min_equity=peak_equity;
 Print("ONVT_SPEC|",_Symbol,"|contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),"|tick=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),"|vol_min=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),"|server=",AccountInfoString(ACCOUNT_SERVER));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) {
 if(audit_file!=INVALID_HANDLE)FileClose(audit_file);
 PrintFormat("ONVT_SUMMARY|%s|days=%d|profiles=%d|missing=%d|first_inside=%d|signals=%d|entries=%d|skipped_open=%d|invalid_geometry=%d|rejected=%d|trail_moves=%d|trail_market_exits=%d|trail_rejects=%d|target_behind_entry=%d|min_equity=%.2f|max_equity_dd=%.6f|balance=%.2f",
  InpCase,days,profiles,missing,inside_first,signals,entries,skipped_open,geometry,rejected,trail_moves,trail_market_exits,trail_rejects,target_invalid,min_equity,max_dd,AccountInfoDouble(ACCOUNT_BALANCE));
}
