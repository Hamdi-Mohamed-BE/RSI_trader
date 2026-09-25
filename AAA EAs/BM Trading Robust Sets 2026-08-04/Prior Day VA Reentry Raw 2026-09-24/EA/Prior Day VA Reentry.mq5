#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
// Research-only raw EA (2026-09-24), the Market Profile "80% rule" as described by the user:
// - Mark the previous day's value area (previous UTC calendar day, M1 HLC3 x broker tick volume, 64 bins,
//   contiguous 70% value area from the POC). Same profile construction as the retained overnight VA EAs.
// - Setup: today's first price is outside that value area (above VAH or below VAL).
// - Trigger: a completed candle on InpSignalTimeframe closes back INSIDE the value area "with strong conviction":
//   close strictly inside [VAL, VAH], candle body >= InpMinBodyFraction of its range, and the body points back
//   into the value area (bearish when re-entering from above, bullish from below).
// - Trade toward the opposite edge: re-entry from above sells with target VAL; from below buys with target VAH.
// - Stop one tick beyond the trigger candle's high (short) / low (long). One trade per day.
// - Entries allowed until InpLastEntryHourUTC; any open trade is closed at InpFlatHourUTC:InpFlatMinuteUTC or one
//   minute before the broker session ends if earlier (gold has a daily break).
// - Optional "ranging market" filter: last completed D1 ADX(14) < InpMaxDailyADX (0 = off).
// - 1% equity risk on the stop distance; volume rounds UP to the broker step (minimum lot floor).
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M30;
input double InpMinBodyFraction=0.5;
input double InpMaxDailyADX=0;
input int InpLastEntryHourUTC=18;
input int InpFlatHourUTC=20;
input int InpFlatMinuteUTC=45;
input int InpBins=64;
input double InpValueAreaPercent=70;
input int InpMinimumProfileBars=300;
input double InpRiskPercent=1;
input int InpServerUTCOffsetHours=0;
input long InpExpectedLogin=0;
input string InpExpectedServer="";
input long InpMagic=89240931;
input string InpCase="raw";
CTrade trade;
int h_adx=INVALID_HANDLE;
int daykey=0,days=0,profiles=0,outside_open=0,triggers=0,entries=0,adx_filtered=0,geometry=0,rejected=0,time_exits=0;
bool ready=false,done=false;int open_side=0;
datetime bar_seen=0,flat_at=0,last_entry_at=0;
double vah=0,val=0,poc=0;
int audit_file=INVALID_HANDLE;

double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
int Key(datetime t){MqlDateTime d;TimeToStruct(t,d);return d.year*10000+d.mon*100+d.day;}
datetime Midnight(datetime t){MqlDateTime d;TimeToStruct(t,d);d.hour=0;d.min=0;d.sec=0;return StructToTime(d);}
bool OwnPosition(ulong &id){
 for(int i=PositionsTotal()-1;i>=0;i--){ulong p=PositionGetTicket(i);
  if(p && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){id=p;return true;}}
 return false;
}
void Audit(string kind,int side=0,double entry=0,double stop=0,double target=0,double lots=0){
 if(audit_file==INVALID_HANDLE)return;
 FileWrite(audit_file,kind,(long)TimeCurrent(),daykey,side,poc,vah,val,entry,stop,target,lots);FileFlush(audit_file);
}
datetime SessionEnd(datetime server_midnight){
 MqlDateTime d;TimeToStruct(server_midnight,d);datetime a,b;long last=0;
 for(uint i=0;i<20;i++){if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,a,b))break;
  long e=(long)b;if(e==0 && (long)a>0)e=86400;last=MathMax(last,e);}
 return last>0?server_midnight+(datetime)last:server_midnight+86400;
}
bool BuildPriorProfile(datetime utc_midnight){
 // Previous UTC calendar day, expressed in server time.
 datetime start=utc_midnight-86400+InpServerUTCOffsetHours*3600,finish=utc_midnight+InpServerUTCOffsetHours*3600;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_M1,start,finish-1,r);
 if(n<InpMinimumProfileBars)return false;
 double hi=-DBL_MAX,lo=DBL_MAX;
 for(int i=0;i<n;i++){hi=MathMax(hi,r[i].high);lo=MathMin(lo,r[i].low);}
 if(hi<=lo)return false;
 double bins[];ArrayResize(bins,InpBins);ArrayInitialize(bins,0);
 double width=(hi-lo)/InpBins,total=0;
 for(int i=0;i<n;i++){
  double typical=(r[i].high+r[i].low+r[i].close)/3;
  int b=(int)MathFloor((typical-lo)/width);b=MathMax(0,MathMin(InpBins-1,b));
  bins[b]+=(double)r[i].tick_volume;total+=(double)r[i].tick_volume;
 }
 if(total<=0)return false;
 int p=0;for(int i=1;i<InpBins;i++)if(bins[i]>bins[p])p=i;
 int left=p,right=p;double covered=bins[p];
 while(covered<total*InpValueAreaPercent/100 && (left>0 || right<InpBins-1)){
  double below=left>0?bins[left-1]:-1,above=right<InpBins-1?bins[right+1]:-1;
  if(above>=below && right<InpBins-1){right++;covered+=bins[right];}else{left--;covered+=bins[left];}
 }
 poc=Price(lo+(p+.5)*width);val=Price(lo+left*width);vah=Price(lo+(right+1)*width);
 return val<vah;
}
void ManageFlat(datetime now){
 ulong id;if(!OwnPosition(id))return;
 if(now>=flat_at && flat_at>0){if(trade.PositionClose(id))time_exits++;}
}
void OnTick(){
 datetime now=TimeCurrent();
 datetime utc=now-InpServerUTCOffsetHours*3600,utc_mid=Midnight(utc);
 if(Key(utc)!=daykey){
  daykey=Key(utc);ready=false;done=false;open_side=0;bar_seen=0;
  datetime server_mid=utc_mid+InpServerUTCOffsetHours*3600;
  datetime desired=server_mid+InpFlatHourUTC*3600+InpFlatMinuteUTC*60,end=SessionEnd(server_mid)-60;
  flat_at=MathMin(desired,end);last_entry_at=server_mid+InpLastEntryHourUTC*3600;
  MqlDateTime d;TimeToStruct(utc,d);
  if(d.day_of_week>=1 && d.day_of_week<=5){
   days++;
   ready=BuildPriorProfile(utc_mid);
   if(ready){
    profiles++;
    MqlTick t;if(SymbolInfoTick(_Symbol,t)){double mid=(t.bid+t.ask)/2;open_side=mid>vah?1:(mid<val?-1:0);}
    if(open_side!=0){outside_open++;Audit("outside_open",open_side);}
    else done=true;   // opened inside the value area: no setup today
   } else done=true;
  } else done=true;
 }
 ManageFlat(now);
 if(done || !ready || now>=last_entry_at || now>=flat_at)return;
 ulong id;if(OwnPosition(id))return;
 datetime current=iTime(_Symbol,InpSignalTimeframe,0);if(current==bar_seen)return;bar_seen=current;
 MqlRates b[];if(CopyRates(_Symbol,InpSignalTimeframe,1,1,b)!=1)return;
 if(b[0].time<utc_mid+InpServerUTCOffsetHours*3600)return;   // candle must belong to today
 double range=b[0].high-b[0].low;if(range<=0)return;
 double body=MathAbs(b[0].close-b[0].open);
 bool inside=b[0].close>val && b[0].close<vah;
 bool strong=body>=InpMinBodyFraction*range && (open_side>0 ? b[0].close<b[0].open : b[0].close>b[0].open);
 if(!inside || !strong)return;
 triggers++;done=true;
 if(InpMaxDailyADX>0){double a[];if(CopyBuffer(h_adx,0,1,1,a)!=1 || a[0]>=InpMaxDailyADX){adx_filtered++;Audit("adx_filtered",open_side);return;}}
 int side=-open_side;   // re-entry from above -> sell toward VAL; from below -> buy toward VAH
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)){rejected++;return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 double entry=side>0?tick.ask:tick.bid;
 double stop=Price(side>0?b[0].low-step:b[0].high+step),target=side>0?vah:val;
 double md=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 bool valid=side>0?(stop<tick.bid-md && target>entry+md):(stop>tick.ask+md && target<entry-md);
 if(!valid){geometry++;Audit("invalid_geometry",side,entry,stop,target);return;}
 ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double unit=0;if(!OrderCalcProfit(type,_Symbol,1,entry,stop,unit) || unit>=0){rejected++;return;}
 double eq=AccountInfoDouble(ACCOUNT_EQUITY),ls=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=MathCeil(eq*InpRiskPercent/100/MathAbs(unit)/ls-1e-10)*ls;
 lots=NormalizeDouble(MathMin(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),lots)),8);
 double margin=0;if(!OrderCalcMargin(type,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){rejected++;return;}
 bool sent=side>0?trade.Buy(lots,_Symbol,0,stop,target,"PDVA reentry"):trade.Sell(lots,_Symbol,0,stop,target,"PDVA reentry");
 if(sent && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL)){entries++;Audit("entry",side,entry,stop,target,lots);}
 else {rejected++;Audit("order_rejected",side,entry,stop,target,lots);Print("PDVA_REJECT|",trade.ResultRetcode(),"|",trade.ResultRetcodeDescription());}
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpExpectedLogin<=0 || AccountInfoInteger(ACCOUNT_LOGIN)!=InpExpectedLogin || AccountInfoString(ACCOUNT_SERVER)!=InpExpectedServer)return INIT_FAILED;
 if(InpMinBodyFraction<0 || InpMinBodyFraction>1 || InpBins<2 || InpRiskPercent<=0 || InpMaxDailyADX<0)return INIT_PARAMETERS_INCORRECT;
 if(InpMaxDailyADX>0){h_adx=iADX(_Symbol,PERIOD_D1,14);if(h_adx==INVALID_HANDLE)return INIT_FAILED;}
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(50);
 audit_file=FileOpen(InpCase+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(audit_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit_file,"kind","server_epoch","utc_day","side","poc","vah","val","entry","stop","target","lots");
 Print("PDVA_SPEC|",_Symbol,"|contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),"|tick=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),"|server=",AccountInfoString(ACCOUNT_SERVER));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){
 if(audit_file!=INVALID_HANDLE)FileClose(audit_file);
 PrintFormat("PDVA_SUMMARY|%s|days=%d|profiles=%d|outside_open=%d|triggers=%d|adx_filtered=%d|invalid_geometry=%d|entries=%d|rejected=%d|time_exits=%d|balance=%.2f",
  InpCase,days,profiles,outside_open,triggers,adx_filtered,geometry,entries,rejected,time_exits,AccountInfoDouble(ACCOUNT_BALANCE));
}
