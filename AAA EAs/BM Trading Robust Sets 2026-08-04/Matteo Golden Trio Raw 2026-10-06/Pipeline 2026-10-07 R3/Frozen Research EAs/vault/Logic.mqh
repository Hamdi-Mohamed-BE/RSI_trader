
#property strict
input int InpCase=0;
input string InpTag="golden-search";
input bool InpVerbose=false;
input int InpControl=0;
int CFG_MODE=1;
ENUM_TIMEFRAMES CFG_TF=PERIOD_M30;
string CFG_TAG="";
#define STRATEGY_MODE CFG_MODE
#define STRATEGY_TF CFG_TF
#define STUDY_TAG CFG_TAG
#define STRATEGY_MAGIC 26100771
double cfg[];
int atr_handle=INVALID_HANDLE,atr_long_handle=INVALID_HANDLE,ema_handle=INVALID_HANDLE,trail_ema_handle=INVALID_HANDLE,htf_handle=INVALID_HANDLE;
datetime pending_expiry=0,entry_clock=0;
double original_risk=0,original_entry=0,last_lock=0;
ulong tracked_ticket=0;
bool partial_done=false,pending_reserved=false;
int failures=0,modifications=0,partial_count=0,requests=0,closed_carries=0,quote_file=INVALID_HANDLE;
int anchor_file=INVALID_HANDLE;
datetime last_anchor_epoch=0;
ENUM_TIMEFRAMES Timeframe(int x){switch(x){case 1:return PERIOD_M1;case 3:return PERIOD_M3;case 5:return PERIOD_M5;case 15:return PERIOD_M15;case 30:return PERIOD_M30;case 60:return PERIOD_H1;case 240:return PERIOD_H4;}return PERIOD_CURRENT;}
double Reading(int h,int buffer=0,int shift=1){double x[];return CopyBuffer(h,buffer,shift,1,x)==1?x[0]:0;}
#include <Trade/Trade.mqh>
input double InpRiskPct=1.0;
int InpDailyATRPeriod=14;
int InpATRMeanSessions=15;
double InpNoiseFraction=0.30;
int InpADXPeriod=14;
double InpADXMinimum=20.0;
double InpVaultStopPoints=75.0;
double InpVaultTargetPoints=40.0;
int InpPullbackMaxTrades=1;
int InpPullbackEntryStart=1000;
int InpPullbackEntryEnd=1430;
int InpPullbackStopBars=20;
int InpPullbackTargetBars=5;
double InpOvernightRR=3.0;
CTrade trade;
int df=INVALID_HANDLE,ef=INVALID_HANDLE,bf=INVALID_HANDLE,sf=INVALID_HANDLE;
int adx_handle=INVALID_HANDLE,day=0,count_today=0,bias=0,last_session_day=0;
datetime last_bar=0,last_minute=0;
double midnight_open=0,range_high=0,range_low=0,overnight_high=0,overnight_low=0;
double pv=0,vwap_volume=0,vwap=0,adx=0,adx_previous=0,noise_mean=0;
double prior_close=0,atr_state=0,tr_seed=0,atr_values[];
int tr_count=0;
bool range_ready=false,armed=false,touched=false,reclaimed=false;

int Sunday(int year,int month,int nth){
 MqlDateTime d={};d.year=year;d.mon=month;d.day=1;TimeToStruct(StructToTime(d),d);
 return 1+(7-d.day_of_week)%7+7*(nth-1);
}
int ChicagoOffset(datetime utc){
 MqlDateTime d;TimeToStruct(utc,d);MqlDateTime x={};
 x.year=d.year;x.mon=3;x.day=Sunday(d.year,3,2);x.hour=8;
 datetime start=StructToTime(x);x.mon=11;x.day=Sunday(d.year,11,1);x.hour=7;
 return utc>=start && utc<StructToTime(x)?-5:-6;
}
int Day(datetime utc){MqlDateTime d;TimeToStruct(utc+ChicagoOffset(utc)*3600,d);return d.year*10000+d.mon*100+d.day;}
int Clock(datetime utc){MqlDateTime d;TimeToStruct(utc+ChicagoOffset(utc)*3600,d);return d.hour*100+d.min;}
datetime MidnightUTC(datetime utc){
 int offset=ChicagoOffset(utc);MqlDateTime d;TimeToStruct(utc+offset*3600,d);d.hour=0;d.min=0;d.sec=0;
 // At a DST change midnight has the old offset, so resolve wall time twice.
 datetime guess=StructToTime(d)-offset*3600;return StructToTime(d)-ChicagoOffset(guess)*3600;
}
double Price(double p){
 double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 return NormalizeDouble(MathRound(p/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
bool Owned(){return PositionSelect(_Symbol) && PositionGetInteger(POSITION_MAGIC)==STRATEGY_MAGIC;}
void Session(int key,datetime epoch,double o,double hi,double lo,double c){
 if(key<=last_session_day || o<=0 || hi<lo)return;
 double tr=hi-lo;
 if(prior_close>0)tr=MathMax(tr,MathMax(MathAbs(hi-prior_close),MathAbs(lo-prior_close)));
 prior_close=c;last_session_day=key;tr_count++;
 if(tr_count<=InpDailyATRPeriod){tr_seed+=tr;if(tr_count==InpDailyATRPeriod)atr_state=tr_seed/InpDailyATRPeriod;}
 else atr_state=(atr_state*(InpDailyATRPeriod-1)+tr)/InpDailyATRPeriod;
 if(tr_count>=InpDailyATRPeriod){int n=ArraySize(atr_values);ArrayResize(atr_values,n+1);atr_values[n]=atr_state;}
 if(sf!=INVALID_HANDLE)FileWrite(sf,key,(long)epoch,o,hi,lo,c,tr,atr_state);
}
void UpdateSessions(datetime now,bool initial){
 datetime start=initial?now-240*86400:now-4*86400;
 MqlRates history[];int n=CopyRates(_Symbol,PERIOD_M30,start,now-1,history);
 int key=0,current_day=Day(now);datetime epoch=0;double o=0,hi=0,lo=0,c=0;
 for(int i=0;i<n;i++){
  int d=Day(history[i].time),clock=Clock(history[i].time);
  if(d>=current_day || d<=last_session_day || clock>=1600)continue;
  if(key!=d){if(key>0)Session(key,epoch,o,hi,lo,c);key=d;epoch=history[i].time;o=history[i].open;hi=history[i].high;lo=history[i].low;}
  else{hi=MathMax(hi,history[i].high);lo=MathMin(lo,history[i].low);}
  c=history[i].close;
 }
 if(key>0)Session(key,epoch,o,hi,lo,c);
 noise_mean=0;int size=ArraySize(atr_values);
 if(size>=InpATRMeanSessions){for(int i=size-InpATRMeanSessions;i<size;i++)noise_mean+=atr_values[i]/InpATRMeanSessions;}
 if(sf!=INVALID_HANDLE)FileFlush(sf);
}
void Reset(datetime now){
 bool initial=(day==0);UpdateSessions(now,initial);day=Day(now);count_today=0;bias=0;
 midnight_open=0;range_high=0;range_low=0;range_ready=false;armed=false;touched=false;reclaimed=false;
 pv=0;vwap_volume=0;vwap=0;
}
void Trace(string reason,MqlRates &bar,double entry=0,double lots=0,double budget=0,double unit_loss=0,double sl=0,double tp=0,double sizing=0){
 if(df==INVALID_HANDLE)return;
 if(df!=INVALID_HANDLE)FileWrite(df,(long)TimeCurrent(),(long)bar.time,reason,STRATEGY_MODE,range_high,range_low,overnight_high,overnight_low,
  midnight_open,noise_mean,midnight_open+InpNoiseFraction*noise_mean,bar.close,vwap,adx,adx_previous,bias,
  (int)armed,(int)touched,(int)reclaimed,count_today,entry,lots,budget,unit_loss,sl,tp,sizing,
  trade.ResultRetcode(),trade.ResultPrice(),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));
 FileFlush(df);
}
void Enter(bool buy,MqlRates &bar,double sl,double tp,MqlTick &tick){

 if(!Gate(buy,bar))return;
 double entry=buy?tick.ask:tick.bid;
 if((int)cfg[2]>=2){double offset=(int)cfg[2]==4?cfg[3]:Reading(atr_handle)*cfg[3];entry+=(buy?1:-1)*((int)cfg[2]==2 || (int)cfg[2]==4?-offset:offset);entry=Price(entry);}
 double distance=StopDistance(buy,bar,entry);if(distance<=0)return;
 sl=Price(entry+(buy?-distance:distance));tp=cfg[6]>0?Price(entry+(buy?1:-1)*distance*cfg[6]):0;

 double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 // A structurally valid broker TP can still be below Ask for a buy. The frozen
 // strategy must skip it: a profit target must lie beyond the executable entry.

 if((buy && (sl>=entry || (tp!=0 && tp<=entry))) || (!buy && (sl<=entry || (tp!=0 && tp>=entry))))return;
 if((int)cfg[2]<=1 && ((buy && (sl>=tick.bid || tick.bid-sl<minimum || (tp!=0 && tp-tick.bid<minimum))) ||
  (!buy && (sl<=tick.ask || sl-tick.ask<minimum || (tp!=0 && tick.ask-tp<minimum))))){Trace("broker_stop_skip",bar,entry,0,0,0,sl,tp);return;}
 if((int)cfg[2]>=2){double offset=MathAbs(entry-(buy?tick.ask:tick.bid));if(offset<minimum){Trace("pending_distance_skip",bar);return;}}
 double equity=AccountInfoDouble(ACCOUNT_EQUITY),budget=equity*InpRiskPct/100,profit=0;
 if(!OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1.0,entry,sl,profit) || profit>=0){Trace("sizing_failed",bar);return;}
 double unit_loss=-profit,step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=NormalizeDouble(MathFloor(budget/unit_loss/step+1e-9)*step,8);lots=MathMin(lots,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
 if(lots<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)){Trace("minimum_lot_skip",bar,entry,lots,budget,unit_loss,sl,tp,equity);return;}
 bool ok=Submit(buy,bar,tick,entry,sl,tp,lots);
 if(ok && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_PLACED)){if((int)cfg[2]>=2)pending_reserved=true;else count_today++;Trace("entry_sent",bar,entry,lots,budget,unit_loss,sl,tp,equity);armed=false;touched=false;reclaimed=false;}
 else{failures++;Trace("entry_failed",bar,entry,lots,budget,unit_loss,sl,tp,equity);}
}

int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpCase<0 || InpCase>=ArrayRange(Cases,0))return INIT_PARAMETERS_INCORRECT;
 ArrayResize(cfg,24);for(int i=0;i<24;i++)cfg[i]=Cases[InpCase][i];
 CFG_MODE=(int)cfg[0];CFG_TF=Timeframe((int)cfg[1]);CFG_TAG=InpTag+"-"+IntegerToString(InpCase);
 if(InpVerbose && CFG_TF==PERIOD_H4){anchor_file=FileOpen(CFG_TAG+"-anchor-bars.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');if(anchor_file==INVALID_HANDLE)return INIT_FAILED;FileWrite(anchor_file,"epoch","open","high","low","close","tick_volume");}
 if(InpVerbose){quote_file=FileOpen(CFG_TAG+"-quotes.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(quote_file==INVALID_HANDLE)return INIT_FAILED;FileWrite(quote_file,"ticket","position_id","epoch","entry","bid","ask","volume");}
 InpNoiseFraction=cfg[19];InpDailyATRPeriod=(int)cfg[20];InpATRMeanSessions=(int)cfg[21];InpADXMinimum=cfg[22];
 if((int)cfg[14]!=9)InpADXMinimum=-1;
 if(InpControl==4 || InpControl==6)InpADXMinimum=-1;
 atr_handle=iATR(_Symbol,STRATEGY_TF,14);atr_long_handle=iATR(_Symbol,STRATEGY_TF,50);ema_handle=iMA(_Symbol,STRATEGY_TF,50,0,MODE_EMA,PRICE_CLOSE);trail_ema_handle=iMA(_Symbol,STRATEGY_TF,12,0,MODE_EMA,PRICE_CLOSE);htf_handle=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);

 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpRiskPct<=0 || InpDailyATRPeriod<2 || InpATRMeanSessions<2 || InpADXPeriod<2)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber(STRATEGY_MAGIC);trade.SetTypeFillingBySymbol(_Symbol);
 adx_handle=iADXWilder(_Symbol,STRATEGY_TF,InpADXPeriod);if(adx_handle==INVALID_HANDLE)return INIT_FAILED;
 if(InpVerbose)df=FileOpen(STUDY_TAG+"-decisions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 if(InpVerbose)ef=FileOpen(STUDY_TAG+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 if(InpVerbose)bf=FileOpen(STUDY_TAG+"-bars.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 if(InpVerbose)sf=FileOpen(STUDY_TAG+"-sessions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 if(InpVerbose && (df==INVALID_HANDLE || ef==INVALID_HANDLE || bf==INVALID_HANDLE || sf==INVALID_HANDLE))return INIT_FAILED;
 if(df!=INVALID_HANDLE)FileWrite(df,"epoch","bar_epoch","reason","mode","range_high","range_low","overnight_high","overnight_low",
 "midnight_open","noise_mean","barrier","signal_close","vwap","adx","adx_previous","bias","armed","touched","reclaimed","count_today",
 "entry_quote","lots","risk_budget","unit_loss","sl","tp","sizing_equity","retcode","fill_price","volume_step","volume_min");
 if(ef!=INVALID_HANDLE)FileWrite(ef,"epoch","balance","equity");
 if(bf!=INVALID_HANDLE)FileWrite(bf,"epoch","open","high","low","close","tick_volume","vwap","adx","adx_previous","noise_mean","evaluation_epoch");
 if(sf!=INVALID_HANDLE)FileWrite(sf,"day","epoch","open","high","low","close","tr","atr");
 PrintFormat("GOLDEN_TRIO mode=%d symbol=%s server_assumed_UTC=true risk=%.2f%% CFD point_value=%.4f",
 STRATEGY_MODE,_Symbol,InpRiskPct,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE));
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();
 if(day==0)Reset(now);
 Manage();
 if(ef!=INVALID_HANDLE && now/60!=last_minute){last_minute=now/60;FileWrite(ef,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
 int clock=Clock(now),flat=(int)cfg[10];
 if(clock>=flat && Owned()){
  bool ok=trade.PositionClose(_Symbol);MqlRates dummy={};dummy.time=now;
  if(!ok)failures++;Trace(ok?"session_close":"session_close_failed",dummy);
 }
 datetime current_bar=iTime(_Symbol,STRATEGY_TF,0);
 if(current_bar==0 || current_bar==last_bar){if(Day(now)!=day)Reset(now);return;}
 last_bar=current_bar;MqlRates values[];if(CopyRates(_Symbol,STRATEGY_TF,1,1,values)!=1)return;
 MqlRates bar=values[0];
 // Audit yesterday's final candle before resetting the midnight anchor.
 if(Day(bar.time)!=day && STRATEGY_TF!=PERIOD_H4){Reset(now);return;}
 if(STRATEGY_TF==PERIOD_H4 && Day(now)!=day)Reset(now);
 if(STRATEGY_TF==PERIOD_H4)H4Anchor(now,current_bar);
 else{
  if(midnight_open==0)midnight_open=bar.open;
  pv+=(bar.high+bar.low+bar.close)/3*(double)bar.tick_volume;vwap_volume+=(double)bar.tick_volume;
  vwap=vwap_volume>0?pv/vwap_volume:0;
 }
 double av[];adx=0;adx_previous=0;
 if(CopyBuffer(adx_handle,0,1,2,av)==2){adx_previous=av[0];adx=av[1];}
 if(bf!=INVALID_HANDLE)FileWrite(bf,(long)bar.time,bar.open,bar.high,bar.low,bar.close,bar.tick_volume,vwap,adx,adx_previous,noise_mean,(long)now);
 if(Day(now)!=day){Reset(now);return;}
 int bclock=Clock(bar.time);
 if(STRATEGY_MODE==2 && bclock>=830 && bclock<900){
  if(range_high==0){range_high=bar.high;range_low=bar.low;}
  else{range_high=MathMax(range_high,bar.high);range_low=MathMin(range_low,bar.low);}
 }
 if(STRATEGY_MODE==2 && bclock>=900 && range_high>range_low && !range_ready){range_ready=true;Trace("range_locked",bar);}
 if(STRATEGY_MODE==3 && STRATEGY_TF==PERIOD_M15 && (int)cfg[23]==15 && bclock==830 && !range_ready){
  datetime start=MidnightUTC(now)-3600;
  // Previous 23:00 occurs at yesterday's historical Chicago offset.
  MqlDateTime d;TimeToStruct(MidnightUTC(now)+ChicagoOffset(MidnightUTC(now))*3600-86400,d);d.hour=23;
  datetime wall=StructToTime(d),guess=wall-ChicagoOffset(now)*3600;start=wall-ChicagoOffset(guess)*3600;
  MqlRates overnight[];int n=CopyRates(_Symbol,PERIOD_M15,start,bar.time-1,overnight);
  overnight_high=0;overnight_low=0;
  if(n>0){overnight_high=overnight[0].high;overnight_low=overnight[0].low;
   for(int i=1;i<n;i++){overnight_high=MathMax(overnight_high,overnight[i].high);overnight_low=MathMin(overnight_low,overnight[i].low);}}
  if(overnight_high>overnight_low){
   double third=(overnight_high-overnight_low)/3;
   bias=bar.open>=overnight_high-third?1:bar.open<=overnight_low+third?-1:0;
   range_high=bar.high;range_low=bar.low;range_ready=true;Trace("range_locked",bar);
  }return;
 }
 if(STRATEGY_TF!=PERIOD_M15 || (int)cfg[23]!=15)AlternateRange(now,bar);
 if(clock>=flat || clock<(int)cfg[11] || clock>=(int)cfg[12] || PositionSelect(_Symbol) || Pending())return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;

 if(STRATEGY_MODE==1){
  if(count_today>=(int)cfg[17] || noise_mean<=0 || vwap<=0)return;
  double barrier=(InpControl==2 || InpControl==5)?0:InpNoiseFraction*noise_mean;
  bool buy=bar.close>midnight_open+barrier && (InpControl==1 || InpControl==5 || bar.close>vwap);
  bool sell=bar.close<midnight_open-barrier && (InpControl==1 || InpControl==5 || bar.close<vwap);
  if(!buy && !sell){Trace("signal_block",bar);return;}
  Enter(buy,bar,tick.ask-InpVaultStopPoints,tick.ask+InpVaultTargetPoints,tick);
 }
 if(STRATEGY_MODE==2){
  if(!range_ready || count_today>=InpPullbackMaxTrades || clock<InpPullbackEntryStart || clock>=InpPullbackEntryEnd)return;
  if(bar.close>range_high)armed=true;
  if(armed && bar.low<=vwap)touched=true;
  if(touched && bar.close>vwap)reclaimed=true;
  if(!armed || !touched || !reclaimed || bar.close<=vwap)return;
  if(adx<=InpADXMinimum || adx>adx_previous){Trace("adx_block",bar);return;}
  MqlRates stops[],targets[];
  if(CopyRates(_Symbol,PERIOD_M1,1,InpPullbackStopBars,stops)!=InpPullbackStopBars ||
     CopyRates(_Symbol,PERIOD_M1,1,InpPullbackTargetBars,targets)!=InpPullbackTargetBars)return;
  double sl=stops[0].low,tp=targets[0].high;
  for(int i=1;i<InpPullbackStopBars;i++)sl=MathMin(sl,stops[i].low);
  for(int i=1;i<InpPullbackTargetBars;i++)tp=MathMax(tp,targets[i].high);
  Enter(true,bar,sl,tp,tick);
 }
 if(STRATEGY_MODE==3){
  if(!range_ready || (bias==0 && InpControl!=3 && InpControl!=6) || count_today>=(int)cfg[17] || bclock<845 || noise_mean<=0)return;
  bool buy=(bias==1 || InpControl==3 || InpControl==6) && bar.close>range_high,sell=(bias==-1 || InpControl==3 || InpControl==6) && bar.close<range_low;
  if(!buy && !sell)return;
  if(adx<=InpADXMinimum){Trace("adx_block",bar);return;}
  double dist=InpNoiseFraction*noise_mean;
  Enter(buy,bar,(buy?tick.ask:tick.bid)+(buy?-dist:dist),
   (buy?tick.ask:tick.bid)+(buy?InpOvernightRR*dist:-InpOvernightRR*dist),tick);
 }
}
void OnDeinit(const int reason){
 if(ef!=INVALID_HANDLE){FileWrite(ef,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileClose(ef);}
 if(df!=INVALID_HANDLE)FileClose(df);if(bf!=INVALID_HANDLE)FileClose(bf);if(sf!=INVALID_HANDLE)FileClose(sf);
 if(adx_handle!=INVALID_HANDLE)IndicatorRelease(adx_handle);
 if(anchor_file!=INVALID_HANDLE)FileClose(anchor_file);if(quote_file!=INVALID_HANDLE)FileClose(quote_file);if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);if(atr_long_handle!=INVALID_HANDLE)IndicatorRelease(atr_long_handle);if(ema_handle!=INVALID_HANDLE)IndicatorRelease(ema_handle);if(trail_ema_handle!=INVALID_HANDLE)IndicatorRelease(trail_ema_handle);if(htf_handle!=INVALID_HANDLE)IndicatorRelease(htf_handle);
}

// H4 UTC candles cross Chicago midnight. Anchor from completed M1 data only,
// while retaining every closed H4 candle for the native indicator audit.
void H4Anchor(datetime now,datetime boundary){
 if(boundary<=MidnightUTC(now)){midnight_open=0;pv=0;vwap_volume=0;vwap=0;return;}
 MqlRates minutes[];int n=CopyRates(_Symbol,PERIOD_M1,MidnightUTC(now),boundary-1,minutes);
 midnight_open=0;pv=0;vwap_volume=0;vwap=0;
 if(n<=0)return;midnight_open=minutes[0].open;
 for(int i=0;i<n;i++){
  pv+=(minutes[i].high+minutes[i].low+minutes[i].close)/3*(double)minutes[i].tick_volume;
  vwap_volume+=(double)minutes[i].tick_volume;
  if(anchor_file!=INVALID_HANDLE && minutes[i].time>last_anchor_epoch){
   FileWrite(anchor_file,(long)minutes[i].time,minutes[i].open,minutes[i].high,minutes[i].low,minutes[i].close,minutes[i].tick_volume);last_anchor_epoch=minutes[i].time;}
 }
 vwap=vwap_volume>0?pv/vwap_volume:0;
}
bool Pending(){for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);if(t>0 && OrderGetInteger(ORDER_MAGIC)==STRATEGY_MAGIC && OrderGetString(ORDER_SYMBOL)==_Symbol)return true;}return false;}
void CancelPending(){for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);if(t>0 && OrderGetInteger(ORDER_MAGIC)==STRATEGY_MAGIC && OrderGetString(ORDER_SYMBOL)==_Symbol){if(!trade.OrderDelete(t))failures++;}}pending_reserved=false;}
bool Gate(bool buy,MqlRates &bar){
 int dir=(int)cfg[13];if((dir==0 && !buy)||(dir==1 && buy))return false;
 MqlDateTime d;TimeToStruct(bar.time+ChicagoOffset(bar.time)*3600,d);int skip=(int)cfg[16];
 if((d.day_of_week==1 && (skip==1 || skip==3)) || (d.day_of_week==5 && (skip==2 || skip==3)))return false;
 if((int)cfg[2]==1){MqlRates old[];if(CopyRates(_Symbol,STRATEGY_TF,2,1,old)!=1)return false;
  if(STRATEGY_MODE==1 && (buy?old[0].close<=midnight_open+InpNoiseFraction*noise_mean:old[0].close>=midnight_open-InpNoiseFraction*noise_mean))return false;
  if(STRATEGY_MODE==3 && (buy?old[0].close<=range_high:old[0].close>=range_low))return false;}
 int f=(int)cfg[14];double threshold=cfg[15],plus=Reading(adx_handle,1),minus=Reading(adx_handle,2),a=Reading(atr_handle),al=Reading(atr_long_handle);
 if((f==1 || f==3) && adx<threshold)return false;
 if((f==2 || f==3) && (buy?plus<=minus:minus<=plus))return false;
 if(f==4){double e=Reading(ema_handle);if(e<=0 || (buy?bar.close<=e:bar.close>=e))return false;}
 if(f==5){double e=Reading(htf_handle);if(e<=0 || (buy?bar.close<=e:bar.close>=e))return false;}
 if(f==6 && (a<=0 || al<=0 || a/al<.75 || a/al>2))return false;
 if(f==7){MqlTick tick;if(!SymbolInfoTick(_Symbol,tick) || a<=0 || tick.ask-tick.bid>.1*a)return false;}
 if(f==8 && adx<=adx_previous)return false;
 if(f==10){double e=Reading(ema_handle),prior=Reading(ema_handle,0,2);if(e<=0 || prior<=0 || (buy?e<=prior:e>=prior))return false;}
 if(f==11){double v[];if(CopyBuffer(atr_handle,0,1,200,v)!=200 || a<=0)return false;int lower=0;for(int i=0;i<200;i++)if(v[i]<=a)lower++;if(lower<50 || lower>150)return false;}
 return true;
}
double StopDistance(bool buy,MqlRates &bar,double entry){
 int model=(int)cfg[4];double x=cfg[5];
 if(model==0)return x;
 if(model==1)return noise_mean*x;
 if(model==2)return Reading(atr_handle)*x;
 if(model==3)return entry*x/100;
 if(model==4)return (buy?entry-bar.low:bar.high-entry)*x;
 MqlRates bars[];int n=CopyRates(_Symbol,STRATEGY_TF,1,20,bars);double lo=bar.low,hi=bar.high;
 if(model==5){for(int i=0;i<n;i++){lo=MathMin(lo,bars[i].low);hi=MathMax(hi,bars[i].high);}}
 if(model==6 && STRATEGY_MODE==3){lo=range_low;hi=range_high;}
 if(model==6 && STRATEGY_MODE==1){lo=midnight_open-InpNoiseFraction*noise_mean;hi=midnight_open+InpNoiseFraction*noise_mean;}
 return (buy?entry-lo:hi-entry)*x;
}
bool Submit(bool buy,MqlRates &bar,MqlTick &tick,double &entry,double &sl,double &tp,double lots){
 int model=(int)cfg[2];bool ok=false;
 if(model<=1)ok=buy?trade.Buy(lots,_Symbol,0,sl,tp,"Golden Trio research"):trade.Sell(lots,_Symbol,0,sl,tp,"Golden Trio research");
 else{pending_expiry=TimeCurrent()+2*PeriodSeconds(STRATEGY_TF);
  if(model==2 || model==4)ok=buy?trade.BuyLimit(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,"Golden limit research"):trade.SellLimit(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,"Golden limit research");
  else ok=buy?trade.BuyStop(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,"Golden stop research"):trade.SellStop(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,"Golden stop research");
 }
 requests++;return ok;
}
void Manage(){
 datetime now=TimeCurrent();int clock=Clock(now);
 if(Pending() && (clock>=(int)cfg[10] || now>=pending_expiry))CancelPending();
 if(!Owned()){tracked_ticket=0;return;}
 ulong ticket=(ulong)PositionGetInteger(POSITION_TICKET);
 bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
 if(ticket!=tracked_ticket){tracked_ticket=ticket;original_entry=PositionGetDouble(POSITION_PRICE_OPEN);original_risk=MathAbs(original_entry-PositionGetDouble(POSITION_SL));entry_clock=(datetime)PositionGetInteger(POSITION_TIME);partial_done=false;last_lock=0;if(pending_reserved){count_today++;pending_reserved=false;}}
 if(cfg[18]>0 && now-entry_clock>=(int)cfg[18]*PeriodSeconds(STRATEGY_TF)){if(!trade.PositionClose(_Symbol))failures++;return;}
 int model=(int)cfg[7];if(model==0 || original_risk<=0)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;double price=buy?tick.bid:tick.ask;
 double favorable=(buy?price-original_entry:original_entry-price);if(favorable<cfg[8]*original_risk)return;
 double proposed=original_entry,old=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
 if(model==2)proposed=price+(buy?-1:1)*Reading(atr_handle)*cfg[9];
 if(model==3)proposed=price+(buy?-1:1)*price*cfg[9]/100;
 if(model==4){double e=Reading(trail_ema_handle);proposed=e;}
 if(model==5){MqlRates b[];if(CopyRates(_Symbol,STRATEGY_TF,1,5,b)!=5)return;proposed=buy?b[0].low:b[0].high;for(int i=1;i<5;i++)proposed=buy?MathMin(proposed,b[i].low):MathMax(proposed,b[i].high);}
 if(model==6)proposed=original_entry+(buy?1:-1)*MathFloor(favorable/original_risk)*original_risk*.5;
 if(model==8){MqlRates b[];if(CopyRates(_Symbol,STRATEGY_TF,1,20,b)!=20)return;double extreme=buy?b[0].high:b[0].low;for(int i=1;i<20;i++)extreme=buy?MathMax(extreme,b[i].high):MathMin(extreme,b[i].low);proposed=extreme+(buy?-1:1)*Reading(atr_handle)*cfg[9];}
 if(model==9){if(favorable-last_lock<.2*original_risk)return;proposed=original_entry+(buy?1:-1)*favorable*.5;}
 if(model==7 && !partial_done){double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),vol=PositionGetDouble(POSITION_VOLUME),minlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double half=NormalizeDouble(MathFloor(vol*.5/step)*step,8);
  if(half>=minlot && vol-half>=minlot){if(trade.PositionClosePartial(_Symbol,half)){partial_count++;partial_done=true;}else failures++;}
  else partial_done=true;
 }
 if(model==7 && partial_done)proposed=buy?MathMax(original_entry,price-Reading(atr_handle)*cfg[9]):MathMin(original_entry,price+Reading(atr_handle)*cfg[9]);
 proposed=Price(proposed);double minimum=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)*_Point);
 bool improves=buy?proposed>old && proposed<price-minimum:proposed<old && proposed>price+minimum;
 if(improves && MathAbs(proposed-old)>=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)){if(trade.PositionModify(_Symbol,proposed,tp)){modifications++;if(model==9)last_lock=favorable;}else failures++;}
}
void AlternateRange(datetime now,MqlRates &bar){
 if(STRATEGY_MODE!=3 || range_ready)return;
 int length=(int)cfg[23],end=0;
 int mins=8*60+30+length;end=(mins/60)*100+mins%60;
 if(Clock(now)<end)return;
 datetime open=MidnightUTC(now)+(8*60+30)*60;
 MqlRates overnight[],opening[];int n=CopyRates(_Symbol,PERIOD_M15,open-(9*60+30)*60,open-1,overnight);
 int m=CopyRates(_Symbol,PERIOD_M1,open,open+length*60-1,opening);
 if(n<=0 || m<=0)return;overnight_high=overnight[0].high;overnight_low=overnight[0].low;
 for(int i=1;i<n;i++){overnight_high=MathMax(overnight_high,overnight[i].high);overnight_low=MathMin(overnight_low,overnight[i].low);}
 if(overnight_high<=overnight_low)return;double third=(overnight_high-overnight_low)/3;
 bias=opening[0].open>=overnight_high-third?1:opening[0].open<=overnight_low+third?-1:0;
 range_high=opening[0].high;range_low=opening[0].low;for(int i=1;i<m;i++){range_high=MathMax(range_high,opening[i].high);range_low=MathMin(range_low,opening[i].low);}
 range_ready=true;Trace("range_locked",bar);
}
double OnTester(){
 HistorySelect(0,TimeCurrent());int out=FileOpen(STUDY_TAG+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 FileWrite(out,"ticket","position_id","epoch","entry","type","volume","price","profit","commission","swap","fee","reason","initial_sl","initial_tp");
 ulong owned_ids[];
 for(int i=0;i<HistoryDealsTotal();i++){ulong t=HistoryDealGetTicket(i);if(t==0 || HistoryDealGetInteger(t,DEAL_MAGIC)!=STRATEGY_MAGIC || HistoryDealGetInteger(t,DEAL_ENTRY)!=DEAL_ENTRY_IN)continue;
  int k=ArraySize(owned_ids);ArrayResize(owned_ids,k+1);owned_ids[k]=(ulong)HistoryDealGetInteger(t,DEAL_POSITION_ID);}
 for(int i=0;i<HistoryDealsTotal();i++){ulong t=HistoryDealGetTicket(i);if(t==0)continue;
  ulong pid=(ulong)HistoryDealGetInteger(t,DEAL_POSITION_ID);bool owned=false;for(int k=0;k<ArraySize(owned_ids);k++)if(owned_ids[k]==pid){owned=true;break;}if(!owned)continue;
  FileWrite(out,t,HistoryDealGetInteger(t,DEAL_POSITION_ID),(long)HistoryDealGetInteger(t,DEAL_TIME),HistoryDealGetInteger(t,DEAL_ENTRY),HistoryDealGetInteger(t,DEAL_TYPE),
   HistoryDealGetDouble(t,DEAL_VOLUME),HistoryDealGetDouble(t,DEAL_PRICE),HistoryDealGetDouble(t,DEAL_PROFIT),HistoryDealGetDouble(t,DEAL_COMMISSION),HistoryDealGetDouble(t,DEAL_SWAP),HistoryDealGetDouble(t,DEAL_FEE),HistoryDealGetInteger(t,DEAL_REASON),HistoryOrderGetDouble((ulong)HistoryDealGetInteger(t,DEAL_ORDER),ORDER_SL),HistoryOrderGetDouble((ulong)HistoryDealGetInteger(t,DEAL_ORDER),ORDER_TP));}
 FileClose(out);out=FileOpen(STUDY_TAG+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 FileWrite(out,"net","equity_dd","failures","modifications","partials","requests","balance","open_position","pending_orders");
 FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),failures,modifications,partial_count,requests,AccountInfoDouble(ACCOUNT_BALANCE),(int)Owned(),(int)Pending());FileClose(out);
 return TesterStatistics(STAT_PROFIT);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result){
 if(quote_file==INVALID_HANDLE || trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0)return;
 if(!HistoryDealSelect(trans.deal) || HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=STRATEGY_MAGIC)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 FileWrite(quote_file,trans.deal,HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID),(long)TimeCurrent(),HistoryDealGetInteger(trans.deal,DEAL_ENTRY),tick.bid,tick.ask,HistoryDealGetDouble(trans.deal,DEAL_VOLUME));FileFlush(quote_file);
}
