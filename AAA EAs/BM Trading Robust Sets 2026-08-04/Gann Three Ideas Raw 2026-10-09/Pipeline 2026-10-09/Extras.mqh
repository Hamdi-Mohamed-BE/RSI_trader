// Explicit research switches. Defaults preserve frozen raw logic.
int cEntry=0,cStop=0,cManagement=0,cExit=0,cSession=0,cDirection=0,cFilter=0,cCap=1,cFlat=1,cDOW=0,cWidth=1,cFast=12,cSlow=26;
double cFraction=.125,cBuffer=.1,cStopScale=1.5,cTrigger=1,cTrail=1;
int adx_handle=INVALID_HANDLE,atr_long_handle=INVALID_HANDLE,htf_handle=INVALID_HANDLE;
int trades_today=0;
double initial_risk=0,peak_price=0;
bool partial_done=false,executing_cue=false;
int cue_side=0;
MqlRates cue_bars[];
datetime cue_expires=0,cue_known=0,cue_pivot=0;
double cue_atr=0,cue_stop=0,cue_target=0,cue_feature=0,cue_age=0,cue_trigger=0;

datetime Sunday(int year,int month,int occurrence)
{
 MqlDateTime d={0};d.year=year;d.mon=month;d.day=1;
 datetime start=StructToTime(d);TimeToStruct(start,d);
 d.day=1+(7-d.day_of_week)%7+(occurrence-1)*7;d.hour=7;
 if(month==11)d.hour=6;
 return StructToTime(d);
}
bool SessionAllowed(datetime t)
{
 datetime utc=t-InpServerUTCOffsetHours*3600;MqlDateTime p;TimeToStruct(utc,p);
 if((cDOW==1 || cDOW==3) && p.day_of_week==1)return false;
 if((cDOW==2 || cDOW==3) && p.day_of_week==5)return false;
 int m=p.hour*60+p.min;
 if(cSession==0)return true;
 if(cSession==1)return m>=0 && m<480;
 if(cSession==2)return m>=420 && m<960;
 bool dst=utc>=Sunday(p.year,3,2) && utc<Sunday(p.year,11,1);
 TimeToStruct(utc+(dst?-4:-5)*3600,p);m=p.hour*60+p.min;
 if(cSession==3)return m>=570 && m<960;
 if(cSession==4)return m>=600 && m<720;
 return m>=570 && m<630;
}
bool FilterAllowed(int side,double atr,double entry)
{
 if(cDirection!=0 && side!=cDirection)return false;
 if(!SessionAllowed(TimeCurrent()))return false;
 double a[],b[],d[];
 if(cFilter>=1 && cFilter<=3)
 {
  if(CopyBuffer(adx_handle,0,1,1,a)!=1 || CopyBuffer(adx_handle,1,1,1,b)!=1 || CopyBuffer(adx_handle,2,1,1,d)!=1)return false;
  if((cFilter==1 || cFilter==3) && a[0]<C[InpCase][15])return false;
  if((cFilter==2 || cFilter==3) && (side>0?b[0]<=d[0]:d[0]<=b[0]))return false;
 }
 if(cFilter==4)
 {
  ArraySetAsSeries(a,true);if(CopyBuffer(htf_handle,0,1,2,a)!=2)return false;
  double close=iClose(_Symbol,PERIOD_H4,1);
  if(side>0?(close<=a[0] || a[0]<=a[1]):(close>=a[0] || a[0]>=a[1]))return false;
 }
 if(cFilter==5){if(CopyBuffer(atr_long_handle,0,1,1,a)!=1 || a[0]<=0 || atr/a[0]<.8 || atr/a[0]>2)return false;}
 if(cFilter==6)
 {
  MqlTick q;if(!SymbolInfoTick(_Symbol,q) || q.ask-q.bid>.1*atr)return false;
 }
 return true;
}
bool ApplyOptions(int side,MqlRates &bars[],double atr,double entry,double &stop,double &target,
 datetime known,datetime pivot,double feature,double age)
{
 if(!FilterAllowed(side,atr,entry))return false;
 if(cStop==1)stop=entry-side*cStopScale*atr;
 if(cStop==2)stop=(side>0?bars[1].low:bars[1].high)-side*cBuffer*atr;
 if(cStop==3)stop=entry-side*.002*entry;
 if(cStop==4)stop=entry-side*(_Symbol=="XAUUSD"?10:(_Symbol=="USTEC"?50:500));
 if(cStop==5)
 {
  if((side>0 && last_low_time<=0) || (side<0 && last_high_time<=0))return false;
  stop=(side>0?last_low:last_high)-side*cBuffer*atr;
 }
 double distance=side*(entry-stop);if(distance<=0)return false;
 // Fixed-R TP is computed in Place AFTER stop rounding, exactly like raw.
 if(cExit==1)target=0;
 if(cExit==2 || cExit==3)target=0;
 if(cEntry>0 && !executing_cue)
 {
  cue_side=side;ArrayResize(cue_bars,3);for(int i=0;i<3;i++)cue_bars[i]=bars[i];
  cue_expires=bars[0].time+2*PeriodSeconds(InpSignalTF);cue_atr=atr;cue_stop=stop;cue_target=target;
  cue_known=known;cue_pivot=pivot;cue_feature=feature;cue_age=age;
  cue_trigger=cEntry==2?entry-side*.25*atr:(side>0?bars[1].high:bars[1].low);
  return false;
 }
 return true;
}
void ExecuteCue()
{
 if(cue_side==0)return;
 if(TimeCurrent()>=cue_expires || trades_today>=cCap){cue_side=0;return;}
 ulong ticket;if(OurPosition(ticket)){cue_side=0;return;}
 if(!SessionAllowed(TimeCurrent()))return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double quote=cue_side>0?tick.ask:tick.bid;bool ready=false;
 if(cEntry==1)
 {
  if(iTime(_Symbol,InpSignalTF,0)<=cue_bars[0].time)return;
  MqlRates b[];ArraySetAsSeries(b,true);if(CopyRates(_Symbol,InpSignalTF,0,2,b)!=2)return;
  ready=cue_side>0?b[1].close>b[1].open:b[1].close<b[1].open;
  if(!ready){cue_side=0;return;}
 }
 else if(cEntry==2)ready=cue_side>0?quote<=cue_trigger:quote>=cue_trigger;
 else ready=cue_side>0?quote>cue_trigger:quote<cue_trigger;
 if(!ready)return;
 int side=cue_side;cue_side=0;executing_cue=true;
 Place(side,cue_bars,cue_atr,cue_stop,cue_target,cue_known,cue_pivot,cue_feature,cue_age);
 executing_cue=false;
}
void ManagePosition()
{
 if(cManagement==0)return;
 ulong ticket;if(!OurPosition(ticket) || initial_risk<=0)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 double entry=PositionGetDouble(POSITION_PRICE_OPEN),quote=side>0?q.bid:q.ask;
 if(peak_price==0)peak_price=quote;
 peak_price=side>0?MathMax(peak_price,quote):MathMin(peak_price,quote);
 double gain=side*(quote-entry);if(gain<cTrigger*initial_risk)return;
 double values[];if(CopyBuffer(atr_handle,0,1,1,values)!=1)return;
 double stop=PositionGetDouble(POSITION_SL),target=PositionGetDouble(POSITION_TP),next=stop;
 if(cManagement==1)next=entry;
 if(cManagement==2 || cManagement==7)next=peak_price-side*cTrail*values[0];
 if(cManagement==3)next=peak_price-side*.001*peak_price;
 if(cManagement==4){if(CopyBuffer(fast_handle,0,1,1,values)!=1)return;next=values[0];}
 if(cManagement==5)
 {
  MqlRates b[];ArraySetAsSeries(b,true);if(CopyRates(_Symbol,InpSignalTF,1,3,b)!=3)return;
  next=side>0?MathMin(b[0].low,MathMin(b[1].low,b[2].low)):MathMax(b[0].high,MathMax(b[1].high,b[2].high));
 }
 if(cManagement==6)next=entry+side*.5*side*(peak_price-entry);
 if(cManagement==7 && !partial_done)
 {
  double volume=PositionGetDouble(POSITION_VOLUME),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double half=MathFloor(volume*.5/step)*step;
  if(half>=minimum && volume-half>=minimum && trade.PositionClosePartial(ticket,half) && trade.ResultRetcode()==TRADE_RETCODE_DONE)partial_done=true;
 }
 next=Price(next);double guard=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 bool improve=side>0?(next>stop && next<q.bid-guard):(next<stop && next>q.ask+guard);
 if(improve)trade.PositionModify(ticket,next,target);
}
