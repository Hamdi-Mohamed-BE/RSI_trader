#include <Trade/Trade.mqh>
input double InpRiskPct=1.0;
input int InpDailyATRPeriod=14;
input int InpATRMeanSessions=15;
input double InpNoiseFraction=0.30;
input int InpADXPeriod=14;
input double InpADXMinimum=20.0;
input double InpVaultStopPoints=75.0;
input double InpVaultTargetPoints=40.0;
input int InpPullbackMaxTrades=1;
input int InpPullbackEntryStart=1000;
input int InpPullbackEntryEnd=1430;
input int InpPullbackStopBars=20;
input int InpPullbackTargetBars=5;
input double InpOvernightRR=3.0;
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
 FileWrite(sf,key,(long)epoch,o,hi,lo,c,tr,atr_state);
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
 FileFlush(sf);
}
void Reset(datetime now){
 bool initial=(day==0);UpdateSessions(now,initial);day=Day(now);count_today=0;bias=0;
 midnight_open=0;range_high=0;range_low=0;range_ready=false;armed=false;touched=false;reclaimed=false;
 pv=0;vwap_volume=0;vwap=0;
}
void Trace(string reason,MqlRates &bar,double entry=0,double lots=0,double budget=0,double unit_loss=0,double sl=0,double tp=0,double sizing=0){
 FileWrite(df,(long)TimeCurrent(),(long)bar.time,reason,STRATEGY_MODE,range_high,range_low,overnight_high,overnight_low,
  midnight_open,noise_mean,midnight_open+InpNoiseFraction*noise_mean,bar.close,vwap,adx,adx_previous,bias,
  (int)armed,(int)touched,(int)reclaimed,count_today,entry,lots,budget,unit_loss,sl,tp,sizing,
  trade.ResultRetcode(),trade.ResultPrice(),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));
 FileFlush(df);
}
void Enter(bool buy,MqlRates &bar,double sl,double tp,MqlTick &tick){
 double entry=buy?tick.ask:tick.bid;sl=Price(sl);tp=Price(tp);
 double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if((buy && (sl>=tick.bid || tp<=tick.bid || tick.bid-sl<minimum || tp-tick.bid<minimum)) ||
    (!buy && (sl<=tick.ask || tp>=tick.ask || sl-tick.ask<minimum || tick.ask-tp<minimum))){Trace("broker_stop_skip",bar,entry,0,0,0,sl,tp);return;}
 double equity=AccountInfoDouble(ACCOUNT_EQUITY),budget=equity*InpRiskPct/100,profit=0;
 if(!OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1.0,entry,sl,profit) || profit>=0){Trace("sizing_failed",bar);return;}
 double unit_loss=-profit,step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=NormalizeDouble(MathFloor(budget/unit_loss/step+1e-9)*step,8);lots=MathMin(lots,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
 if(lots<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)){Trace("minimum_lot_skip",bar,entry,lots,budget,unit_loss,sl,tp,equity);return;}
 bool ok=buy?trade.Buy(lots,_Symbol,0,sl,tp,"Golden Trio research"):trade.Sell(lots,_Symbol,0,sl,tp,"Golden Trio research");
 if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE){count_today++;Trace("entry_sent",bar,entry,lots,budget,unit_loss,sl,tp,equity);armed=false;touched=false;reclaimed=false;}
 else Trace("entry_failed",bar,entry,lots,budget,unit_loss,sl,tp,equity);
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpRiskPct<=0 || InpDailyATRPeriod<2 || InpATRMeanSessions<2 || InpADXPeriod<2)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber(STRATEGY_MAGIC);trade.SetTypeFillingBySymbol(_Symbol);
 adx_handle=iADXWilder(_Symbol,STRATEGY_TF,InpADXPeriod);if(adx_handle==INVALID_HANDLE)return INIT_FAILED;
 df=FileOpen(STUDY_TAG+"-decisions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 ef=FileOpen(STUDY_TAG+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 bf=FileOpen(STUDY_TAG+"-bars.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 sf=FileOpen(STUDY_TAG+"-sessions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 if(df==INVALID_HANDLE || ef==INVALID_HANDLE || bf==INVALID_HANDLE || sf==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(df,"epoch","bar_epoch","reason","mode","range_high","range_low","overnight_high","overnight_low",
 "midnight_open","noise_mean","barrier","signal_close","vwap","adx","adx_previous","bias","armed","touched","reclaimed","count_today",
 "entry_quote","lots","risk_budget","unit_loss","sl","tp","sizing_equity","retcode","fill_price","volume_step","volume_min");
 FileWrite(ef,"epoch","balance","equity");
 FileWrite(bf,"epoch","open","high","low","close","tick_volume","vwap","adx","adx_previous","noise_mean");
 FileWrite(sf,"day","epoch","open","high","low","close","tr","atr");
 PrintFormat("GOLDEN_TRIO mode=%d symbol=%s server_assumed_UTC=true risk=%.2f%% CFD point_value=%.4f",
 STRATEGY_MODE,_Symbol,InpRiskPct,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE));
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();
 if(day==0)Reset(now);
 if(now/60!=last_minute){last_minute=now/60;FileWrite(ef,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
 int clock=Clock(now),flat=STRATEGY_MODE==2?1555:1430;
 if(clock>=flat && Owned()){
  bool ok=trade.PositionClose(_Symbol);MqlRates dummy={};dummy.time=now;
  Trace(ok?"session_close":"session_close_failed",dummy);
 }
 datetime current_bar=iTime(_Symbol,STRATEGY_TF,0);
 if(current_bar==0 || current_bar==last_bar){if(Day(now)!=day)Reset(now);return;}
 last_bar=current_bar;MqlRates values[];if(CopyRates(_Symbol,STRATEGY_TF,1,1,values)!=1)return;
 MqlRates bar=values[0];
 // Audit yesterday's final candle before resetting the midnight anchor.
 if(Day(bar.time)!=day){Reset(now);return;}
 if(midnight_open==0)midnight_open=bar.open;
 pv+=(bar.high+bar.low+bar.close)/3*(double)bar.tick_volume;vwap_volume+=(double)bar.tick_volume;
 vwap=vwap_volume>0?pv/vwap_volume:0;
 double av[];adx=0;adx_previous=0;
 if(CopyBuffer(adx_handle,0,1,2,av)==2){adx_previous=av[0];adx=av[1];}
 FileWrite(bf,(long)bar.time,bar.open,bar.high,bar.low,bar.close,bar.tick_volume,vwap,adx,adx_previous,noise_mean);
 if(Day(now)!=day){Reset(now);return;}
 int bclock=Clock(bar.time);
 if(STRATEGY_MODE==2 && bclock>=830 && bclock<900){
  if(range_high==0){range_high=bar.high;range_low=bar.low;}
  else{range_high=MathMax(range_high,bar.high);range_low=MathMin(range_low,bar.low);}
 }
 if(STRATEGY_MODE==2 && bclock>=900 && range_high>range_low && !range_ready){range_ready=true;Trace("range_locked",bar);}
 if(STRATEGY_MODE==3 && bclock==830 && !range_ready){
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
 if(clock>=flat || PositionSelect(_Symbol))return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 if(STRATEGY_MODE==1){
  if(clock<1000 || count_today>=3 || noise_mean<=0 || vwap<=0)return;
  if(bar.close<=midnight_open+InpNoiseFraction*noise_mean || bar.close<=vwap){Trace("signal_block",bar);return;}
  Enter(true,bar,tick.ask-InpVaultStopPoints,tick.ask+InpVaultTargetPoints,tick);
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
  if(!range_ready || bias==0 || count_today>=1 || bclock<845 || noise_mean<=0)return;
  bool buy=bias==1 && bar.close>range_high,sell=bias==-1 && bar.close<range_low;
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
}
