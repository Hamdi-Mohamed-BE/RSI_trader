"""Mechanical copy of immutable raw engine + explicit tester-only research switches."""
from pathlib import Path
import re
R=Path(__file__).resolve().parent
PRE=r'''
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
'''
EXTRA=r'''
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
'''
def build():
    text=(R.parent/'Golden Trio Engine.mqh').read_text()
    text=re.sub(r'input (int|double) (Inp\w+)=',r'\1 \2=',text)
    text=text.replace('double InpRiskPct=','input double InpRiskPct=',1)
    text=text.replace(' FileWrite(sf,key,',' if(sf!=INVALID_HANDLE)FileWrite(sf,key,')
    text=text.replace(' FileFlush(sf);',' if(sf!=INVALID_HANDLE)FileFlush(sf);')
    a=text.index(' FileWrite(df,(long)TimeCurrent()');text=text[:a]+text[a:].replace(' FileWrite(df,(long)TimeCurrent()',' if(df==INVALID_HANDLE)return;\n FileWrite(df,(long)TimeCurrent()',1)
    text=text.replace(' double entry=buy?tick.ask:tick.bid;sl=Price(sl);tp=Price(tp);',r'''
 if(!Gate(buy,bar))return;
 double entry=buy?tick.ask:tick.bid;
 if((int)cfg[2]>=2){double offset=(int)cfg[2]==4?cfg[3]:Reading(atr_handle)*cfg[3];entry+=(buy?1:-1)*((int)cfg[2]==2 || (int)cfg[2]==4?-offset:offset);entry=Price(entry);}
 double distance=StopDistance(buy,bar,entry);if(distance<=0)return;
 sl=Price(entry+(buy?-distance:distance));tp=cfg[6]>0?Price(entry+(buy?1:-1)*distance*cfg[6]):0;
''')
    # Profit/stop constraints for market orders; broker validates pending prices independently.
    a=text.index(' if((buy && (tp<=entry');b=text.index(' double equity=',a)
    text=text[:a]+r'''
 if((buy && (sl>=entry || (tp!=0 && tp<=entry))) || (!buy && (sl<=entry || (tp!=0 && tp>=entry))))return;
 if((int)cfg[2]<=1 && ((buy && (sl>=tick.bid || tick.bid-sl<minimum || (tp!=0 && tp-tick.bid<minimum))) ||
  (!buy && (sl<=tick.ask || sl-tick.ask<minimum || (tp!=0 && tick.ask-tp<minimum))))){Trace("broker_stop_skip",bar,entry,0,0,0,sl,tp);return;}
 if((int)cfg[2]>=2){double offset=MathAbs(entry-(buy?tick.ask:tick.bid));if(offset<minimum){Trace("pending_distance_skip",bar);return;}}
'''+text[b:]
    text=text.replace(' bool ok=buy?trade.Buy(lots,_Symbol,0,sl,tp,"Golden Trio research"):trade.Sell(lots,_Symbol,0,sl,tp,"Golden Trio research");',' bool ok=Submit(buy,bar,tick,entry,sl,tp,lots);')
    text=text.replace('if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE){count_today++;','if(ok && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_PLACED)){if((int)cfg[2]>=2)pending_reserved=true;else count_today++;')
    text=text.replace(' else Trace("entry_failed",bar,entry,lots,budget,unit_loss,sl,tp,equity);',' else{failures++;Trace("entry_failed",bar,entry,lots,budget,unit_loss,sl,tp,equity);}')
    text=text.replace('int OnInit(){',r'''
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
''')
    text=text.replace(' df=FileOpen(STUDY_TAG+"-decisions.csv"',' if(InpVerbose)df=FileOpen(STUDY_TAG+"-decisions.csv"')
    text=text.replace(' ef=FileOpen(STUDY_TAG+"-equity.csv"',' if(InpVerbose)ef=FileOpen(STUDY_TAG+"-equity.csv"')
    text=text.replace(' bf=FileOpen(STUDY_TAG+"-bars.csv"',' if(InpVerbose)bf=FileOpen(STUDY_TAG+"-bars.csv"')
    text=text.replace(' sf=FileOpen(STUDY_TAG+"-sessions.csv"',' if(InpVerbose)sf=FileOpen(STUDY_TAG+"-sessions.csv"')
    text=text.replace(' if(df==INVALID_HANDLE || ef==INVALID_HANDLE || bf==INVALID_HANDLE || sf==INVALID_HANDLE)return INIT_FAILED;',' if(InpVerbose && (df==INVALID_HANDLE || ef==INVALID_HANDLE || bf==INVALID_HANDLE || sf==INVALID_HANDLE))return INIT_FAILED;')
    for handle in ['df','ef','bf','sf']:text=text.replace(' FileWrite('+handle+',',' if('+handle+'!=INVALID_HANDLE)FileWrite('+handle+',')
    text=text.replace(' datetime now=TimeCurrent();\n if(day==0)Reset(now);',' datetime now=TimeCurrent();\n if(day==0)Reset(now);\n Manage();')
    text=text.replace('if(now/60!=last_minute)','if(ef!=INVALID_HANDLE && now/60!=last_minute)')
    text=text.replace(' if(Day(bar.time)!=day){Reset(now);return;}',' if(Day(bar.time)!=day && STRATEGY_TF!=PERIOD_H4){Reset(now);return;}\n if(STRATEGY_TF==PERIOD_H4 && Day(now)!=day)Reset(now);')
    a=text.index(' if(midnight_open==0)midnight_open=bar.open;');b=text.index(' double av[];',a)
    text=text[:a]+''' if(STRATEGY_TF==PERIOD_H4)H4Anchor(now,current_bar);
 else{
  if(midnight_open==0)midnight_open=bar.open;
  pv+=(bar.high+bar.low+bar.close)/3*(double)bar.tick_volume;vwap_volume+=(double)bar.tick_volume;
  vwap=vwap_volume>0?pv/vwap_volume:0;
 }
'''+text[b:]
    text=text.replace('"noise_mean");','"noise_mean","evaluation_epoch");')
    text=text.replace('vwap,adx,adx_previous,noise_mean);','vwap,adx,adx_previous,noise_mean,(long)now);')
    text=text.replace('int clock=Clock(now),flat=STRATEGY_MODE==2?1555:1430;','int clock=Clock(now),flat=(int)cfg[10];')
    text=text.replace('Trace(ok?"session_close":"session_close_failed",dummy);','if(!ok)failures++;Trace(ok?"session_close":"session_close_failed",dummy);')
    text=text.replace('if(STRATEGY_MODE==3 && bclock==830 && !range_ready)','if(STRATEGY_MODE==3 && STRATEGY_TF==PERIOD_M15 && (int)cfg[23]==15 && bclock==830 && !range_ready)')
    text=text.replace(' if(clock>=flat || PositionSelect(_Symbol))return;',' if(STRATEGY_TF!=PERIOD_M15 || (int)cfg[23]!=15)AlternateRange(now,bar);\n if(clock>=flat || clock<(int)cfg[11] || clock>=(int)cfg[12] || PositionSelect(_Symbol) || Pending())return;')
    a=text.index(' if(STRATEGY_MODE==1){',text.index('void OnTick'));b=text.index(' if(STRATEGY_MODE==2){',a)
    text=text[:a]+r'''
 if(STRATEGY_MODE==1){
  if(count_today>=(int)cfg[17] || noise_mean<=0 || vwap<=0)return;
  double barrier=(InpControl==2 || InpControl==5)?0:InpNoiseFraction*noise_mean;
  bool buy=bar.close>midnight_open+barrier && (InpControl==1 || InpControl==5 || bar.close>vwap);
  bool sell=bar.close<midnight_open-barrier && (InpControl==1 || InpControl==5 || bar.close<vwap);
  if(!buy && !sell){Trace("signal_block",bar);return;}
  Enter(buy,bar,tick.ask-InpVaultStopPoints,tick.ask+InpVaultTargetPoints,tick);
 }
'''+text[b:]
    text=text.replace('if(!range_ready || bias==0 || count_today>=1 || bclock<845 || noise_mean<=0)return;','if(!range_ready || (bias==0 && InpControl!=3 && InpControl!=6) || count_today>=(int)cfg[17] || bclock<845 || noise_mean<=0)return;')
    text=text.replace('bool buy=bias==1 && bar.close>range_high,sell=bias==-1 && bar.close<range_low;','bool buy=(bias==1 || InpControl==3 || InpControl==6) && bar.close>range_high,sell=(bias==-1 || InpControl==3 || InpControl==6) && bar.close<range_low;')
    text=text.replace(' if(adx_handle!=INVALID_HANDLE)IndicatorRelease(adx_handle);',' if(adx_handle!=INVALID_HANDLE)IndicatorRelease(adx_handle);\n if(anchor_file!=INVALID_HANDLE)FileClose(anchor_file);if(quote_file!=INVALID_HANDLE)FileClose(quote_file);if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);if(atr_long_handle!=INVALID_HANDLE)IndicatorRelease(atr_long_handle);if(ema_handle!=INVALID_HANDLE)IndicatorRelease(ema_handle);if(trail_ema_handle!=INVALID_HANDLE)IndicatorRelease(trail_ema_handle);if(htf_handle!=INVALID_HANDLE)IndicatorRelease(htf_handle);')
    # Extra functions before the raw body allow calls without changing baseline order.
    return PRE+text+EXTRA
if __name__=='__main__':
    (R/'EA').mkdir(exist_ok=True);(R/'EA/Logic.mqh').write_text(build(),encoding='utf-8')
