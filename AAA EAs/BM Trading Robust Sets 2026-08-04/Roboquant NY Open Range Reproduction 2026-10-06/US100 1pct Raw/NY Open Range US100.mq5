#property strict
#property description "Research-only CFD adaptation of the retrieved Roboquant NY Open Range Breakout"
#include <Trade/Trade.mqh>
input int range_bars=1;
input double rr_target=0.4;
input int risk_mode=0;
input double risk_pct=1.0;
input double risk_usd=3000.0;
input int stop_mode=1;
input double atr_stop_mult=0.4;
input int atr_period=14;
input double max_stop_pts=0.0;
input bool use_rvol=true;
input double min_rvol=1.0;
input int rvol_period=20;
input bool use_atr_regime=true;
input double min_atr_pct=0.10;
input double max_atr_pct=0.60;
input int cutoff_hhmm=1500;
input int flat_hhmm=1555;
input bool one_trade_per_day=true;
input bool allow_long=true;
input bool allow_short=true;
const int MAGIC=26100661;
CTrade trade;
int atr_handle=INVALID_HANDLE,decision_file=INVALID_HANDLE,equity_file=INVALID_HANDLE,bars_file=INVALID_HANDLE;
int day=0,bars_seen=0;
double or_high=0,or_low=0,sizing_equity=0,sizing_balance=0;
bool range_ready=false,traded=false,done=false;
datetime last_bar=0,last_minute=0;

int Sunday(int year,int month,int nth){
 MqlDateTime d={};d.year=year;d.mon=month;d.day=1;
 TimeToStruct(StructToTime(d),d);
 return 1+(7-d.day_of_week)%7+7*(nth-1);
}
int NYOffset(datetime utc){
 MqlDateTime d;TimeToStruct(utc,d);MqlDateTime x={};
 x.year=d.year;x.mon=3;x.day=Sunday(d.year,3,2);x.hour=7;
 datetime start=StructToTime(x);
 x.mon=11;x.day=Sunday(d.year,11,1);x.hour=6;
 return utc>=start && utc<StructToTime(x)?-4:-5;
}
double Price(double value){
 double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 return NormalizeDouble(MathRound(value/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
void Decision(string reason,MqlRates &bar,double atr=0,double rv=0,double atrpct=0,
              double lots=0,double budget=0,double unit_loss=0,double sl=0,double tp=0){
 FileWrite(decision_file,(long)TimeCurrent(),(long)bar.time,reason,or_high,or_low,bar.close,
           atr,rv,atrpct,lots,budget,unit_loss,sl,tp,trade.ResultRetcode(),trade.ResultPrice(),
           SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),
           AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),sizing_balance,sizing_equity);
 FileFlush(decision_file);
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(range_bars<1 || atr_period<2 || rvol_period<2 || rr_target<=0 || atr_stop_mult<=0 || risk_pct<=0)
  return INIT_PARAMETERS_INCORRECT;
 atr_handle=iATR(_Symbol,PERIOD_M15,atr_period);
 if(atr_handle==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(MAGIC);trade.SetTypeFillingBySymbol(_Symbol);
 decision_file=FileOpen("rq-ny-orb-1pct-20261006-decisions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 equity_file=FileOpen("rq-ny-orb-1pct-20261006-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 bars_file=FileOpen("rq-ny-orb-1pct-20261006-bars.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 if(decision_file==INVALID_HANDLE || equity_file==INVALID_HANDLE || bars_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(decision_file,"epoch","bar_epoch","reason","range_high","range_low","signal_close",
           "atr","rvol","atr_pct","lots","risk_budget","unit_loss","sl","tp","retcode","fill_price",
           "volume_step","volume_min","balance","equity","sizing_balance","sizing_equity");
 FileWrite(equity_file,"epoch","balance","equity");
 FileWrite(bars_file,"epoch","open","high","low","close","tick_volume","atr");
 PrintFormat("RQ_NY_ORB_RESEARCH symbol=%s tick_size=%.8f contract_size=%.8f min_lot=%.8f lot_step=%.8f server_time_assumed_UTC=true",
             _Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),
             SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP));
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();
 if(now/60!=last_minute){last_minute=now/60;FileWrite(equity_file,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
 MqlRates bars[];
 if(CopyRates(_Symbol,PERIOD_M15,1,1,bars)!=1 || bars[0].time==last_bar)return;
 MqlRates bar=bars[0];last_bar=bar.time;
 sizing_balance=0;sizing_equity=0;
 double bar_atr[],logged_atr=0;if(CopyBuffer(atr_handle,0,1,1,bar_atr)==1)logged_atr=bar_atr[0];
 FileWrite(bars_file,(long)bar.time,bar.open,bar.high,bar.low,bar.close,bar.tick_volume,logged_atr);
 MqlDateTime ny;TimeToStruct(bar.time+NYOffset(bar.time)*3600,ny);
 int thisday=ny.year*10000+ny.mon*100+ny.day,hhmm=ny.hour*100+ny.min;
 if(thisday!=day){
  day=thisday;or_high=bar.high;or_low=bar.low;bars_seen=0;range_ready=false;traded=false;done=false;
 }
 // Source uses the completed bar's OPEN timestamp for these clock checks.
 if(!done && hhmm>=flat_hhmm){
  if(PositionSelect(_Symbol) && PositionGetInteger(POSITION_MAGIC)==MAGIC){
   bool closed=trade.PositionClose(_Symbol);Decision(closed?"session_close":"session_close_failed",bar);
  }
  done=true;return;
 }
 if(hhmm>=930 && bars_seen<range_bars){
  if(bars_seen==0){or_high=bar.high;or_low=bar.low;}
  else {or_high=MathMax(or_high,bar.high);or_low=MathMin(or_low,bar.low);}
  bars_seen++;
  if(bars_seen>=range_bars){range_ready=true;Decision("range_locked",bar);}
  return;
 }
 if(!range_ready || PositionSelect(_Symbol) || (one_trade_per_day && traded) || hhmm>=cutoff_hhmm || or_high<=or_low)return;
 bool buy=allow_long && bar.close>or_high,sell=allow_short && bar.close<or_low;
 if(!buy && !sell)return;
 MqlRates volumes[];
 double average=0,rv=0;
 // Previous bars only: current signal bar excluded; history continues across NY dates.
 int count=CopyRates(_Symbol,PERIOD_M15,2,rvol_period,volumes);
 if(count>0){for(int i=0;i<count;i++)average+=(double)volumes[i].tick_volume/count;}
 if(average>0)rv=(double)bar.tick_volume/average;
 if(use_rvol && (average<=0 || rv<min_rvol)){Decision("rvol_block",bar,0,rv);return;}
 double values[],atr=0;
 if(CopyBuffer(atr_handle,0,1,1,values)==1)atr=values[0];
 double atrpct=bar.close>0?atr/bar.close*100:0;
 if(use_atr_regime && (atrpct<min_atr_pct || atrpct>max_atr_pct)){Decision("atr_regime_block",bar,atr,rv,atrpct);return;}
 double dist=(stop_mode==1 && atr>0)?atr_stop_mult*atr:MathAbs(bar.close-(buy?or_low:or_high));
 if(dist<=0 || (max_stop_pts>0 && dist>max_stop_pts)){Decision("stop_distance_skip",bar,atr,rv,atrpct);return;}
 double sl=Price(bar.close+(buy?-dist:dist)),tp=Price(bar.close+(buy?rr_target*dist:-rr_target*dist));
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double min_dist=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if((buy && (sl>=tick.bid || tp<=tick.bid || tick.bid-sl<min_dist || tp-tick.bid<min_dist)) ||
    (!buy && (sl<=tick.ask || tp>=tick.ask || sl-tick.ask<min_dist || tick.ask-tp<min_dist))){
  Decision("broker_stop_skip",bar,atr,rv,atrpct,0,0,0,sl,tp);return;
 }
 // CFD adaptation: budget includes Bid/Ask entry-to-stop distance; fees/slippage remain additional.
 sizing_equity=AccountInfoDouble(ACCOUNT_EQUITY);sizing_balance=AccountInfoDouble(ACCOUNT_BALANCE);
 double budget=risk_mode==1?risk_usd:sizing_equity*risk_pct/100;
 double profit=0,entry=buy?tick.ask:tick.bid;
 ENUM_ORDER_TYPE side=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(side,_Symbol,1.0,entry,sl,profit) || profit>=0){Decision("sizing_failed",bar,atr,rv,atrpct,0,budget,0,sl,tp);return;}
 double unit_loss=-profit,step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=NormalizeDouble(MathFloor(budget/unit_loss/step+1e-9)*step,8);
 lots=MathMin(lots,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
 if(lots<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)){Decision("minimum_lot_skip",bar,atr,rv,atrpct,lots,budget,unit_loss,sl,tp);return;}
 bool sent=buy?trade.Buy(lots,_Symbol,0,sl,tp,"RQ NY ORB"):trade.Sell(lots,_Symbol,0,sl,tp,"RQ NY ORB");
 Decision(sent?"entry_sent":"entry_failed",bar,atr,rv,atrpct,lots,budget,unit_loss,sl,tp);
 traded=true;
}
void OnDeinit(const int reason){
 if(equity_file!=INVALID_HANDLE){FileWrite(equity_file,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileClose(equity_file);}
 if(decision_file!=INVALID_HANDLE)FileClose(decision_file);
 if(bars_file!=INVALID_HANDLE)FileClose(bars_file);
 if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);
}
