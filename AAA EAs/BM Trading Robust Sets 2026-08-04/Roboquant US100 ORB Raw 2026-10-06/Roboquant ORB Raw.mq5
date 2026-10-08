#property strict
#include <Trade/Trade.mqh>
input double InpRiskUSD=100.0;
input int InpMagic=26100655;
CTrade trade;
int a14=INVALID_HANDLE,a50=INVALID_HANDLE,dec=INVALID_HANDLE,eq=INVALID_HANDLE;
int lastday=0; datetime minute=0;
int Sunday(int year,int month,int nth){MqlDateTime d={};d.year=year;d.mon=month;d.day=1;TimeToStruct(StructToTime(d),d);return 1+(7-d.day_of_week)%7+7*(nth-1);}
int Offset(datetime t){MqlDateTime d;TimeToStruct(t,d);MqlDateTime x={};x.year=d.year;x.mon=3;x.day=Sunday(d.year,3,2);x.hour=7;datetime s=StructToTime(x);x.mon=11;x.day=Sunday(d.year,11,1);x.hour=6;return t>=s && t<StructToTime(x)?-4:-5;}
void Decision(string reason,double hi=0,double lo=0,double atr=0,double regime=0,double rv=0,double lots=0){FileWrite(dec,(long)TimeCurrent(),reason,hi,lo,atr,regime,rv,lots,trade.ResultRetcode());FileFlush(dec);}
double Price(double p){double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/ts)*ts,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
 a14=iATR(_Symbol,PERIOD_M1,14);a50=iATR(_Symbol,PERIOD_M1,50);
 if(a14==INVALID_HANDLE || a50==INVALID_HANDLE) return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);
 dec=FileOpen("rq-orb-20261006-decisions.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 eq=FileOpen("rq-orb-20261006-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,',');
 if(dec==INVALID_HANDLE || eq==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(dec,"epoch","reason","range_high","range_low","atr14","atr_ratio","relative_volume","lots","retcode");
 FileWrite(eq,"epoch","balance","equity");return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();
 if(now/60!=minute){minute=now/60;FileWrite(eq,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
 if(PositionSelect(_Symbol) && PositionGetInteger(POSITION_MAGIC)==InpMagic){
  if(now-PositionGetInteger(POSITION_TIME)>=480){if(!trade.PositionClose(_Symbol))Decision("time_close_failed");}
 }
 MqlDateTime ny;TimeToStruct(now+Offset(now)*3600,ny);
 int day=ny.year*10000+ny.mon*100+ny.day;
 if(ny.day_of_week==0 || ny.day_of_week==6 || day==lastday)return;
 if(ny.hour<9 || (ny.hour==9 && (ny.min<59 || (ny.min==59 && ny.sec<55))))return;
 lastday=day;
 if(PositionSelect(_Symbol)){Decision("position_still_open");return;}
 MqlDateTime start=ny;start.hour=9;start.min=30;start.sec=0;
 datetime utcstart=StructToTime(start)-Offset(now)*3600;
 MqlRates bars[];int count=CopyRates(_Symbol,PERIOD_M1,utcstart,utcstart+899,bars);
 if(count!=15){Decision("incomplete_range");return;}
 double hi=bars[0].high,lo=bars[0].low;
 for(int i=0;i<count;i++){hi=MathMax(hi,bars[i].high);lo=MathMin(lo,bars[i].low);}
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 bool buy=tick.bid>hi;
 if(!buy && tick.bid>=lo){Decision("inside_range",hi,lo);return;}
 double at[],al[];MqlRates vols[];
 if(CopyBuffer(a14,0,1,1,at)!=1 || CopyBuffer(a50,0,1,1,al)!=1 || CopyRates(_Symbol,PERIOD_M1,1,14,vols)!=14){Decision("indicator_history",hi,lo);return;}
 MqlDateTime first;TimeToStruct(vols[0].time+Offset(vols[0].time)*3600,first);
 if(first.year*10000+first.mon*100+first.day!=day){Decision("daily_volume_warmup",hi,lo);return;}
 double average=0;for(int j=0;j<14;j++)average+=(double)vols[j].tick_volume/14.0;
 double rv=average>0?(double)vols[13].tick_volume/average:0,regime=al[0]>0?at[0]/al[0]:0;
 if(regime<1.0 || regime>2.5 || rv<0.5 || rv>1.5){Decision("filter_skip",hi,lo,at[0],regime,rv);return;}
 double entry=buy?tick.ask:tick.bid;
 double sl=Price(tick.bid+(buy?-1:1)*2.2*at[0]),tp=Price(tick.bid+(buy?1:-1)*0.3*at[0]);
 double minDist=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if((buy && (tick.bid-sl<minDist || tp-tick.bid<minDist || sl>=tick.bid || tp<=tick.bid)) || (!buy && (sl-tick.ask<minDist || tick.ask-tp<minDist || sl<=tick.ask || tp>=tick.ask))){Decision("broker_stop_skip",hi,lo,at[0],regime,rv);return;}
 double loss=0;ENUM_ORDER_TYPE side=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(side,_Symbol,1.0,entry,sl,loss) || loss>=0){Decision("sizing_failed",hi,lo,at[0],regime,rv);return;}
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=MathFloor(InpRiskUSD/-loss/step+1e-9)*step;
 lots=MathMin(lots,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
 if(lots<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)){Decision("minimum_lot_skip",hi,lo,at[0],regime,rv,lots);return;}
 bool ok=buy?trade.Buy(lots,_Symbol,0,sl,tp,"RQ snapshot"):trade.Sell(lots,_Symbol,0,sl,tp,"RQ snapshot");
 Decision(ok?"entry_sent":"entry_failed",hi,lo,at[0],regime,rv,lots);
}
void OnDeinit(const int reason){if(eq!=INVALID_HANDLE){FileWrite(eq,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileClose(eq);}if(dec!=INVALID_HANDLE)FileClose(dec);if(a14!=INVALID_HANDLE)IndicatorRelease(a14);if(a50!=INVALID_HANDLE)IndicatorRelease(a50);}
