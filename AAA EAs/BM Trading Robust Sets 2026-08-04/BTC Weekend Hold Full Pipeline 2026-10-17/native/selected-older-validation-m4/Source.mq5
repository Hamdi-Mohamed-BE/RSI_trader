#property strict
#property version "1.00"
#property description "Isolated tester-only Friday/Sunday BTC research; never attach to a trading account."
#include <Trade/Trade.mqh>

input datetime InpFrom=D'2018.01.01 00:00';
input datetime InpTo=D'2026.10.17 00:00';
input datetime InpHistoryFrom=D'2018.01.01 00:00';
input string InpTag="";
input int InpTimeframeMinutes=5;
input int InpEntryMode=0;
input int InpStopMode=0;
input double InpStopValue=0;
input double InpTargetRR=0;
input int InpManagementMode=0;
input double InpManagementValue=0;
input int InpFilterMode=0;
input double InpFilterValue=0;
input int InpEntryMinuteNY=1020;
input int InpExitMinuteNY=1020;
// 0 is the registered one-times-equity notional strategy. Mode1 is a separate
// protective-stop risk overlay, never a replacement label for the no-SL raw.
input int InpSizingMode=0;
input double InpRiskPercent=1;
input double InpNotionalMultiple=1;
// Hash-bound same-broker prefix contains historical feature state only;
// native.py stages no bar ending after InpFrom and verifies its provenance.
input string InpWarmFile="";
input long InpWarmRows=0;
input string InpWarmSHA256="";

CTrade trade;
const ulong MAGIC=86701701;
ENUM_TIMEFRAMES feature_tf=PERIOD_M5;
int feature_seconds=300,decision_file=INVALID_HANDLE,equity_file=INVALID_HANDLE;
bool warmed=false,finished=false;
bool good_ring[200],current_atr_ratio_valid=false;
long processed_bars=0,ratio_count=0,last_m1=-1,last_m5=-1,last_friday=-1,last_close_retry=-1;
long entry_requests=0,entry_fills=0,close_requests=0,failed_entries=0,failed_closes=0,manage_requests=0,failed_manages=0;
datetime last_bar=0,feature_end=0,scheduled_exit=0,actual_entry=0;
long actual_entry_msc=0;
double last_o=0,last_h=0,last_l=0,last_c=0,prior_c=0,ema50=0,ema200=0,atr=0;
double tr_ring[14],tr_total=0,smooth_tr=0,smooth_plus=0,smooth_minus=0,adx=0,di_plus=0,di_minus=0,dx_seed=0;
double previous_h=0,previous_l=0,previous_c=0,ratios[],percentile=0;
double entry_price=0,initial_sl=0,initial_tp=0,initial_r=0,eligible_high=0;
datetime filter_spread_bar=0;
double filter_spread_points=0,filter_spread_close=0,filter_spread_pct=0;
ulong tracked_position=0;

string Folder(){return "BTCWeekendPipeline20261017\\"+InpTag;}
bool ValidTag(){return StringLen(InpTag)>0 && StringFind(InpTag,"..")<0 && StringFind(InpTag,"\\")<0 && StringFind(InpTag,"/")<0;}
datetime DateValue(int y,int m,int d,int h=0,int minute=0){MqlDateTime z;ZeroMemory(z);z.year=y;z.mon=m;z.day=d;z.hour=h;z.min=minute;return StructToTime(z);}
int Sunday(int year,int month,int ordinal){MqlDateTime z;TimeToStruct(DateValue(year,month,1),z);return 1+(7-z.day_of_week)%7+7*(ordinal-1);}
bool UsDstUTC(datetime utc){MqlDateTime z;TimeToStruct(utc,z);return utc>=DateValue(z.year,3,Sunday(z.year,3,2),7) && utc<DateValue(z.year,11,Sunday(z.year,11,1),6);}
datetime ToNY(datetime utc){return utc-(UsDstUTC(utc)?4:5)*3600;}
datetime FromNY(datetime wall){MqlDateTime z;TimeToStruct(wall,z);bool dst=wall>=DateValue(z.year,3,Sunday(z.year,3,2),2) && wall<DateValue(z.year,11,Sunday(z.year,11,1),2);return wall+(dst?4:5)*3600;}
datetime DayStart(datetime t){return (datetime)((long)t/86400*86400);}
datetime NextMonth(datetime at){MqlDateTime d;TimeToStruct(at,d);d.day=1;d.hour=0;d.min=0;d.sec=0;d.mon++;if(d.mon>12){d.mon=1;d.year++;}return StructToTime(d);}
double TickFloor(double p){double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathFloor(p/tick+1e-9)*tick,_Digits);}
double TickCeil(double p){double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathCeil(p/tick-1e-9)*tick,_Digits);}
bool SelectOurs(){return PositionSelect(_Symbol) && (ulong)PositionGetInteger(POSITION_MAGIC)==MAGIC;}
bool Accepted(){uint rc=trade.ResultRetcode();return rc==TRADE_RETCODE_DONE || rc==TRADE_RETCODE_DONE_PARTIAL;}
bool NeedsFeatures(){return InpEntryMode>0 || InpStopMode==1 || InpStopMode==3 || InpManagementMode>0 || (InpFilterMode>=1 && InpFilterMode<=6);}
int RequiredLookback()
{
 int needed=(InpEntryMode==2?2:(InpEntryMode==1?1:0));
 if(InpStopMode==1 || InpStopMode==3 || InpManagementMode>0 || InpFilterMode==6)needed=(int)MathMax(needed,14);
 if(InpFilterMode==1 || InpFilterMode==2)needed=(int)MathMax(needed,InpFilterMode==1?50:200);
 if(InpFilterMode>=3 && InpFilterMode<=5)needed=(int)MathMax(needed,28);
 return needed;
}

void Decision(string reason,MqlTick &tick,double sl=0,double tp=0,double lots=0,double budget=0,double unit_loss=0)
{
 if(decision_file==INVALID_HANDLE)return;
 double spread=(tick.bid>0?(tick.ask-tick.bid)/tick.bid*100:0);
 FileWrite(decision_file,(long)tick.time,tick.time_msc,reason,(long)ToNY(tick.time),(long)scheduled_exit,tick.bid,tick.ask,spread,
  AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),lots,sl,tp,budget,unit_loss,(long)last_bar,(long)feature_end,last_o,last_h,last_l,last_c,prior_c,atr,ema50,ema200,adx,di_plus,di_minus,percentile,ratio_count,
  trade.ResultRetcode(),trade.ResultOrder(),trade.ResultDeal(),(long)actual_entry,entry_price,initial_r,eligible_high,(long)filter_spread_bar,filter_spread_points,filter_spread_close,filter_spread_pct,processed_bars,RequiredLookback(),ValidLookback(RequiredLookback())?1:0);
}
void Equity(MqlTick &tick,string reason)
{
 if(equity_file==INVALID_HANDLE)return;
 bool held=SelectOurs();
 FileWrite(equity_file,(long)tick.time,tick.time_msc,reason,tick.bid,tick.ask,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_MARGIN),AccountInfoDouble(ACCOUNT_MARGIN_FREE),
  held?(long)PositionGetInteger(POSITION_IDENTIFIER):0,held?PositionGetDouble(POSITION_VOLUME):0,held?PositionGetDouble(POSITION_PRICE_OPEN):0,held?PositionGetDouble(POSITION_SL):0,held?PositionGetDouble(POSITION_TP):0,held?PositionGetDouble(POSITION_PROFIT):0,(long)last_bar,(long)feature_end);
}
bool ValidLookback(int length)
{
 if(processed_bars<length)return false;
 for(int i=0;i<length;i++)if(!good_ring[(int)((processed_bars-1-i)%200)])return false;
 return true;
}
void AppendBar(MqlRates &b,bool complete)
{
 if(b.time<=last_bar)return;
 good_ring[(int)(processed_bars%200)]=complete && (processed_bars==0 || b.time-last_bar==feature_seconds);
 double tr=b.high-b.low,plus=0,minus=0;
 if(processed_bars>0){tr=MathMax(tr,MathMax(MathAbs(b.high-previous_c),MathAbs(b.low-previous_c)));double up=b.high-previous_h,down=previous_l-b.low;plus=(up>down && up>0?up:0);minus=(down>up && down>0?down:0);}
 int slot=(int)(processed_bars%14);tr_total-=tr_ring[slot];tr_ring[slot]=tr;tr_total+=tr;
 if(processed_bars==0){ema50=b.close;ema200=b.close;}else{ema50+=2.0/51*(b.close-ema50);ema200+=2.0/201*(b.close-ema200);}
 if(processed_bars<14){smooth_tr+=tr;smooth_plus+=plus;smooth_minus+=minus;}else{smooth_tr=smooth_tr-smooth_tr/14+tr;smooth_plus=smooth_plus-smooth_plus/14+plus;smooth_minus=smooth_minus-smooth_minus/14+minus;}
 if(processed_bars>=13)
 {
  atr=tr_total/14;di_plus=(smooth_tr>0?100*smooth_plus/smooth_tr:0);di_minus=(smooth_tr>0?100*smooth_minus/smooth_tr:0);
  double dx=(di_plus+di_minus>0?100*MathAbs(di_plus-di_minus)/(di_plus+di_minus):0);
  if(processed_bars<=26){dx_seed+=dx;if(processed_bars==26)adx=dx_seed/14;}else adx=(adx*13+dx)/14;
 }
 prior_c=previous_c;last_o=b.open;last_h=b.high;last_l=b.low;last_c=b.close;last_bar=b.time;feature_end=b.time+feature_seconds;
 previous_h=b.high;previous_l=b.low;previous_c=b.close;processed_bars++;
 // A flat (zero ATR) but complete historical observation is valid for rank
 // history. ATR-based order geometry independently still requires ATR>0.
 current_atr_ratio_valid=ValidLookback(14) && MathIsValidNumber(atr) && atr>=0 && b.close>0;
 if(current_atr_ratio_valid){if(ArrayResize(ratios,(int)ratio_count+1,65536)<0){Print("BW_FATAL ratio allocation");ExpertRemove();return;}ratios[(int)ratio_count]=atr/b.close;ratio_count++;}
 if(actual_entry_msc>0 && (long)b.time*1000>=actual_entry_msc)eligible_high=MathMax(eligible_high,b.high);
}
bool LoadPrefix()
{
 if(!NeedsFeatures())return true;
 if(InpWarmFile!="feature-prefix.bin" || InpWarmRows<0 || StringLen(InpWarmSHA256)!=64){Print("BW_FATAL missing hash-bound causal feature prefix");return false;}
 int file=FileOpen(Folder()+"\\"+InpWarmFile,FILE_READ|FILE_BIN|FILE_COMMON);
 if(file==INVALID_HANDLE){Print("BW_FATAL feature prefix unavailable");return false;}
 if(FileSize(file)!=(ulong)InpWarmRows*56){FileClose(file);Print("BW_FATAL prefix byte count");return false;}
 for(long i=0;i<InpWarmRows;i++)
 {
  MqlRates b;ZeroMemory(b);b.time=(datetime)FileReadLong(file);
  // Check time BEFORE reading any associated OHLC value. No future feature
  // bytes are staged, and any unexpected future record is fatal, not ignored.
  if(b.time<InpHistoryFrom || b.time+feature_seconds>InpFrom || (last_bar>0 && b.time<=last_bar)){FileClose(file);Print("BW_FATAL noncausal or unordered feature prefix");return false;}
  b.open=FileReadDouble(file);b.high=FileReadDouble(file);b.low=FileReadDouble(file);b.close=FileReadDouble(file);b.tick_volume=FileReadLong(file);b.spread=FileReadInteger(file,INT_VALUE);int complete=FileReadInteger(file,INT_VALUE);
  if(b.open<=0 || b.close<=0 || b.low<=0 || b.high<b.low || (complete!=0 && complete!=1)){FileClose(file);Print("BW_FATAL invalid feature prefix value");return false;}
  AppendBar(b,complete==1);
 }
 FileClose(file);PrintFormat("BW_PREFIX_COMPLETE rows=%I64d last_end=%I64d cutoff=%I64d sha=%s",processed_bars,(long)feature_end,(long)InpFrom,InpWarmSHA256);return true;
}
bool Ingest(datetime now,bool warm=false)
{
 datetime from=(last_bar>0?last_bar+1:InpHistoryFrom),latest=now-feature_seconds;
 if(from>latest)return true;
 for(datetime begin=from;begin<=latest;)
 {
  datetime until=(datetime)MathMin((double)NextMonth(begin),(double)(latest+1));MqlRates bars[];
  int n=CopyRates(_Symbol,feature_tf,begin,until-1,bars);
  for(int retry=0;retry<10 && n<0;retry++){Sleep(50);n=CopyRates(_Symbol,feature_tf,begin,until-1,bars);}
  if(n<0){PrintFormat("BW_FATAL feature history %d %I64d",GetLastError(),(long)begin);return false;}
  MqlRates fine[];int nf=0,j=0;
  if(n>0 && InpTimeframeMinutes>1)
  {
   nf=CopyRates(_Symbol,PERIOD_M1,bars[0].time,bars[n-1].time+feature_seconds-1,fine);
   for(int retry=0;retry<10 && nf<0;retry++){Sleep(50);nf=CopyRates(_Symbol,PERIOD_M1,bars[0].time,bars[n-1].time+feature_seconds-1,fine);}
   if(nf<0){Print("BW_FATAL constituent history");return false;}
  }
  for(int i=0;i<n;i++)if(bars[i].time>=InpHistoryFrom && bars[i].time+feature_seconds<=now)
  {
   bool complete=true;
   if(InpTimeframeMinutes>1){while(j<nf && fine[j].time<bars[i].time)j++;int k=j;while(k<nf && fine[k].time<bars[i].time+feature_seconds)k++;complete=(k-j==InpTimeframeMinutes);j=k;}
   AppendBar(bars[i],complete);
  }
  begin=until;
 }
 if(warm)PrintFormat("BW_FEATURE_WARM rows=%I64d first_requested=%I64d last=%I64d",processed_bars,(long)InpHistoryFrom,(long)last_bar);
 return true;
}
bool FeatureFilter(MqlTick &tick,string &why)
{
 if(InpFilterMode==0)return true;
 if(InpFilterMode==1){if(!ValidLookback(50) || last_c<=ema50){why="skip_ema50";return false;}}
 if(InpFilterMode==2){if(!ValidLookback(200) || last_c<=ema200){why="skip_ema200";return false;}}
 if(InpFilterMode>=3 && InpFilterMode<=5)
 {
  if(!ValidLookback(28) || adx<(InpFilterMode==4?25:20)){why="skip_adx";return false;}
  if(InpFilterMode==5 && di_plus<=di_minus){why="skip_di";return false;}
 }
 if(InpFilterMode==6)
 {
  if(!current_atr_ratio_valid || ratio_count<61){why="skip_percentile_warmup";return false;}
  long below=0;double current=ratios[(int)ratio_count-1];for(int i=0;i<ratio_count-1;i++)if(ratios[i]<=current)below++;
  percentile=100.0*below/(ratio_count-1);double lows[4]={10,20,20,30},highs[4]={90,80,95,90};int band=(int)InpFilterValue;
  if(percentile<lows[band] || percentile>highs[band]){why="skip_atr_percentile";return false;}
 }
 if(InpFilterMode==7)
 {
  // A completed bar's recorded spread is available causally. The current
  // M5 spread field is not known at its opening and must never gate entry.
  datetime expected=(datetime)((long)tick.time/300*300-300);MqlRates prior[];
  int n=CopyRates(_Symbol,PERIOD_M5,expected,expected,prior);
  if(n!=1 || prior[0].time!=expected || prior[0].time+300>tick.time){why="skip_missing_completed_spread_bar";return false;}
  MqlRates minutes[];int count=CopyRates(_Symbol,PERIOD_M1,expected,expected+299,minutes);
  if(count!=5){why="skip_incomplete_completed_spread_bar";return false;}
  filter_spread_bar=prior[0].time;filter_spread_points=prior[0].spread;filter_spread_close=prior[0].close;
  if(filter_spread_points<=0 || filter_spread_close<=0){why="skip_unknown_nonpositive_spread";return false;}
  filter_spread_pct=filter_spread_points*_Point/filter_spread_close*100;
  if(filter_spread_pct>InpFilterValue){why="skip_spread_cap";return false;}
 }
 return true;
}

void Enter(MqlTick &tick)
{
 if(SelectOurs()){Decision("skip_existing_position",tick);return;}
 string why="";
 int needed=RequiredLookback();
 if(needed>0 && feature_end!=(datetime)((long)tick.time/feature_seconds*feature_seconds)){Decision("skip_stale_entry_feature",tick);return;}
 if(needed>0 && !ValidLookback(needed)){Decision("skip_entry_feature_warmup_or_incomplete",tick);return;}
 if(InpEntryMode==1 && last_c<=last_o){Decision("skip_signal_not_bullish",tick);return;}
 if(InpEntryMode==2 && last_c<=prior_c){Decision("skip_signal_no_momentum",tick);return;}
 if(!FeatureFilter(tick,why)){Decision(why,tick);return;}
 double sl=0,tp=0;
 if(InpStopMode>0)
 {
  if((InpStopMode==1 || InpStopMode==3) && (!ValidLookback(14) || atr<=0)){Decision("skip_stop_feature_warmup",tick);return;}
  if(InpStopMode==1)sl=tick.ask-atr*InpStopValue;
  if(InpStopMode==2)sl=tick.ask*(1-InpStopValue/100);
  if(InpStopMode==3)sl=last_l-.1*atr;
  sl=TickFloor(sl);
  if(sl<=0 || sl>=tick.ask){Decision("skip_invalid_initial_stop",tick,sl);return;}
  if(InpTargetRR>0)tp=TickCeil(tick.ask+(tick.ask-sl)*InpTargetRR);
 }
 double equity=AccountInfoDouble(ACCOUNT_EQUITY),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 double raw=equity*InpNotionalMultiple/(tick.ask*contract),budget=0,unit_loss=0;
 if(InpSizingMode==1)
 {
  double one=0;if(sl<=0 || !OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1,tick.ask,sl,one) || one>=0){Decision("skip_unpriceable_stop_risk",tick,sl,tp);return;}
  unit_loss=-one;budget=equity*InpRiskPercent/100;raw=MathMin(raw,budget/unit_loss);
 }
 double lots=NormalizeDouble(MathFloor(MathMin(raw,maximum)/step+1e-9)*step,8);
 while(lots>=minimum && (lots*tick.ask*contract>equity*InpNotionalMultiple+1e-7 || (budget>0 && lots*unit_loss>budget+1e-7)))lots=NormalizeDouble(lots-step,8);
 if(lots<minimum){Decision("skip_minimum_lot_not_affordable",tick,sl,tp,lots,budget,unit_loss);return;}
 double margin=0;if(!OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,lots,tick.ask,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){Decision("skip_insufficient_native_margin",tick,sl,tp,lots,budget,unit_loss);return;}
 entry_requests++;Decision("entry_request",tick,sl,tp,lots,budget,unit_loss);
 bool sent=trade.Buy(lots,_Symbol,0,sl,tp,"BTC Weekend Research");
 if(!sent || !Accepted() || !SelectOurs()){failed_entries++;Decision("entry_rejected",tick,sl,tp,lots,budget,unit_loss);return;}
 entry_fills++;tracked_position=(ulong)PositionGetInteger(POSITION_IDENTIFIER);actual_entry=(datetime)PositionGetInteger(POSITION_TIME);actual_entry_msc=PositionGetInteger(POSITION_TIME_MSC);entry_price=PositionGetDouble(POSITION_PRICE_OPEN);initial_sl=PositionGetDouble(POSITION_SL);initial_tp=PositionGetDouble(POSITION_TP);initial_r=(initial_sl>0?entry_price-initial_sl:0);eligible_high=entry_price;
 MqlTick after=tick;SymbolInfoTick(_Symbol,after);Decision("entry_filled",after,initial_sl,initial_tp,PositionGetDouble(POSITION_VOLUME),budget,unit_loss);Equity(after,"after_entry");
}
void CloseScheduled(MqlTick &tick)
{
 if(!SelectOurs() || (long)tick.time==last_close_retry)return;last_close_retry=(long)tick.time;close_requests++;Decision("scheduled_exit_request",tick);
 bool sent=trade.PositionClose(_Symbol);if(!sent || !Accepted()){failed_closes++;Decision("scheduled_exit_rejected",tick);}else{MqlTick after=tick;SymbolInfoTick(_Symbol,after);Decision("scheduled_exit_filled",after);Equity(after,"after_scheduled_exit");}
}
void Manage(MqlTick &tick)
{
 if(InpManagementMode==0 || !SelectOurs() || initial_r<=0 || (long)feature_end*1000<=actual_entry_msc || !ValidLookback(14))return;
 double trigger=(InpManagementMode==1?InpManagementValue:1),candidate=0;
 if(last_c<entry_price+trigger*initial_r)return;
 if(InpManagementMode==1)candidate=entry_price;
 if(InpManagementMode==2 && atr>0)candidate=last_c-atr*InpManagementValue;
 if(InpManagementMode==3)candidate=last_c*(1-InpManagementValue/100);
 if(InpManagementMode==4 && atr>0 && eligible_high>entry_price)candidate=eligible_high-atr*InpManagementValue;
 if(InpManagementMode==5 && eligible_high>entry_price)candidate=entry_price+.5*(eligible_high-entry_price);
 candidate=TickFloor(candidate);double old=PositionGetDouble(POSITION_SL);
 if(candidate<=0 || candidate<=old+SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)*.5)return;
 // Never widen a rejected stop to make the historical strategy appear filled.
 manage_requests++;Decision("management_request",tick,candidate,PositionGetDouble(POSITION_TP));
 if(!trade.PositionModify(_Symbol,candidate,PositionGetDouble(POSITION_TP)) || !Accepted()){failed_manages++;Decision("management_rejected",tick,candidate);}else Decision("management_applied",tick,candidate);
}

int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER) || _Symbol!="BTCUSD" || !ValidTag() || InpTo<=InpFrom || InpHistoryFrom>InpFrom)return INIT_PARAMETERS_INCORRECT;
 if(InpEntryMode<0 || InpEntryMode>2 || InpStopMode<0 || InpStopMode>3 || InpManagementMode<0 || InpManagementMode>5 || InpFilterMode<0 || InpFilterMode>7)return INIT_PARAMETERS_INCORRECT;
 if(InpEntryMinuteNY<0 || InpEntryMinuteNY>=1440 || InpExitMinuteNY<0 || InpExitMinuteNY>=1440 || InpNotionalMultiple<=0 || InpNotionalMultiple>1 || InpSizingMode<0 || InpSizingMode>1)return INIT_PARAMETERS_INCORRECT;
 if((InpStopMode==0 && (InpTargetRR>0 || InpManagementMode>0 || InpSizingMode==1)) || (InpStopMode>0 && InpStopMode<3 && InpStopValue<=0) || InpTargetRR<0)return INIT_PARAMETERS_INCORRECT;
 if(InpManagementMode>=1 && InpManagementMode<=4 && InpManagementValue<=0)return INIT_PARAMETERS_INCORRECT;
 if(InpFilterMode==6 && (InpFilterValue<0 || InpFilterValue>3 || MathFloor(InpFilterValue)!=InpFilterValue))return INIT_PARAMETERS_INCORRECT;
 if(InpFilterMode==7 && InpFilterValue<=0)return INIT_PARAMETERS_INCORRECT;
 switch(InpTimeframeMinutes){case 1:feature_tf=PERIOD_M1;break;case 3:feature_tf=PERIOD_M3;break;case 5:feature_tf=PERIOD_M5;break;case 15:feature_tf=PERIOD_M15;break;case 30:feature_tf=PERIOD_M30;break;case 60:feature_tf=PERIOD_H1;break;case 240:feature_tf=PERIOD_H4;break;case 1440:feature_tf=PERIOD_D1;break;default:return INIT_PARAMETERS_INCORRECT;}
 feature_seconds=InpTimeframeMinutes*60;ArrayInitialize(tr_ring,0);ArrayInitialize(good_ring,false);trade.SetExpertMagicNumber(MAGIC);trade.SetAsyncMode(false);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(100000);
 FolderCreate("BTCWeekendPipeline20261017",FILE_COMMON);FolderCreate(Folder(),FILE_COMMON);
 decision_file=FileOpen(Folder()+"\\decisions.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');equity_file=FileOpen(Folder()+"\\equity-m1.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(decision_file==INVALID_HANDLE || equity_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(decision_file,"epoch","time_msc","reason","ny_wall_epoch","scheduled_exit_epoch","bid","ask","spread_pct","balance","equity","lots","sl","tp","risk_budget","unit_loss","feature_open_epoch","feature_end_epoch","open","high","low","close","prior_close","atr14_sma","ema50","ema200","adx14_wilder","di_plus","di_minus","atr_percentile","valid_atr_ratios","retcode","order","deal","entry_epoch","entry_price","filled_initial_r","eligible_completed_high","filter_spread_bar_epoch","filter_spread_points","filter_spread_close","filter_spread_pct","processed_feature_bars","required_entry_lookback","entry_lookback_valid");
 FileWrite(equity_file,"epoch","time_msc","reason","bid","ask","balance","equity","margin","free_margin","position_id","lots","entry_price","sl","tp","floating_profit","feature_open_epoch","feature_end_epoch");
 Print("BW_RESEARCH_TESTER_ONLY 1x-equity-notional default; no live API; no hidden SL");return INIT_SUCCEEDED;
}
void OnTick()
{
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 if(!warmed){if(!LoadPrefix()){ExpertRemove();return;}warmed=true;}
 long m5=(long)tick.time/300;
 if(m5!=last_m5){if(NeedsFeatures() && !Ingest(tick.time)){ExpertRemove();return;}last_m5=m5;}
 long m1=(long)tick.time/60;if(m1!=last_m1){Equity(tick,"minute_first_tick");last_m1=m1;}
 // Scheduled exit has priority over any management decision at that tick.
 if(SelectOurs() && scheduled_exit>0 && tick.time>=scheduled_exit){CloseScheduled(tick);return;}
 if(SelectOurs()) // management only once per M5 bucket below
 {
  static long managed_m5=-1;if(managed_m5!=m5){managed_m5=m5;Manage(tick);}
 }
 if(tick.time<InpFrom || tick.time>=InpTo)return;
 datetime ny=ToNY(tick.time);MqlDateTime d;TimeToStruct(ny,d);long day=(long)DayStart(ny);int minute=d.hour*60+d.min;
 if(d.day_of_week!=5 || minute<InpEntryMinuteNY || day==last_friday)return;
 last_friday=day;datetime requested_entry=FromNY((datetime)(day+InpEntryMinuteNY*60));scheduled_exit=FromNY((datetime)(day+2*86400+InpExitMinuteNY*60));
 if(requested_entry<InpFrom || scheduled_exit>=InpTo){Decision("skip_administratively_incomplete_weekend",tick);return;}
 if(minute!=InpEntryMinuteNY){Decision("skip_missing_entry_minute",tick);return;}
 Enter(tick);
}
void ExportDeals()
{
 int f=FileOpen(Folder()+"\\deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(f==INVALID_HANDLE){Print("BW_NATIVE_AUDIT_ERROR deals");return;}
 FileWrite(f,"ticket","order","position_id","epoch","time_msc","symbol","type","entry","reason","magic","volume","price","profit","commission","swap","fee","comment");
 HistorySelect(0,TimeCurrent()+1);uint total=HistoryDealsTotal();
 for(uint i=0;i<total;i++){ulong ticket=HistoryDealGetTicket(i);FileWrite(f,ticket,HistoryDealGetInteger(ticket,DEAL_ORDER),HistoryDealGetInteger(ticket,DEAL_POSITION_ID),HistoryDealGetInteger(ticket,DEAL_TIME),HistoryDealGetInteger(ticket,DEAL_TIME_MSC),HistoryDealGetString(ticket,DEAL_SYMBOL),HistoryDealGetInteger(ticket,DEAL_TYPE),HistoryDealGetInteger(ticket,DEAL_ENTRY),HistoryDealGetInteger(ticket,DEAL_REASON),HistoryDealGetInteger(ticket,DEAL_MAGIC),HistoryDealGetDouble(ticket,DEAL_VOLUME),HistoryDealGetDouble(ticket,DEAL_PRICE),HistoryDealGetDouble(ticket,DEAL_PROFIT),HistoryDealGetDouble(ticket,DEAL_COMMISSION),HistoryDealGetDouble(ticket,DEAL_SWAP),HistoryDealGetDouble(ticket,DEAL_FEE),HistoryDealGetString(ticket,DEAL_COMMENT));}FileClose(f);
 int orders=FileOpen(Folder()+"\\orders.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(orders==INVALID_HANDLE){Print("BW_NATIVE_AUDIT_ERROR orders");return;}
 FileWrite(orders,"ticket","position_id","setup_epoch","done_epoch","type","state","magic","volume_initial","volume_current","price_open","sl","tp","comment");
 for(int i=0;i<HistoryOrdersTotal();i++){ulong ticket=HistoryOrderGetTicket(i);FileWrite(orders,ticket,HistoryOrderGetInteger(ticket,ORDER_POSITION_ID),HistoryOrderGetInteger(ticket,ORDER_TIME_SETUP),HistoryOrderGetInteger(ticket,ORDER_TIME_DONE),HistoryOrderGetInteger(ticket,ORDER_TYPE),HistoryOrderGetInteger(ticket,ORDER_STATE),HistoryOrderGetInteger(ticket,ORDER_MAGIC),HistoryOrderGetDouble(ticket,ORDER_VOLUME_INITIAL),HistoryOrderGetDouble(ticket,ORDER_VOLUME_CURRENT),HistoryOrderGetDouble(ticket,ORDER_PRICE_OPEN),HistoryOrderGetDouble(ticket,ORDER_SL),HistoryOrderGetDouble(ticket,ORDER_TP),HistoryOrderGetString(ticket,ORDER_COMMENT));}FileClose(orders);
}
double OnTester()
{
 if(!MQLInfoInteger(MQL_TESTER) || finished)return 0;finished=true;MqlTick tick;if(SymbolInfoTick(_Symbol,tick))Equity(tick,"tester_final_snapshot");ExportDeals();
 int f=FileOpen(Folder()+"\\stats.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(f==INVALID_HANDLE)return 0;
 FileWrite(f,"entry_requests","entry_fills","failed_entries","close_requests","failed_closes","management_requests","failed_management","last_quote_epoch","balance","equity","open_position_at_on_tester","feature_bars","valid_atr_ratios");
 FileWrite(f,entry_requests,entry_fills,failed_entries,close_requests,failed_closes,manage_requests,failed_manages,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),SelectOurs()?1:0,processed_bars,ratio_count);FileClose(f);
 FileFlush(decision_file);FileFlush(equity_file);PrintFormat("BW_NATIVE_COMPLETE requests=%I64d fills=%I64d last=%I64d",entry_requests,entry_fills,(long)TimeCurrent());return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason){if(decision_file!=INVALID_HANDLE)FileClose(decision_file);if(equity_file!=INVALID_HANDLE)FileClose(equity_file);}
