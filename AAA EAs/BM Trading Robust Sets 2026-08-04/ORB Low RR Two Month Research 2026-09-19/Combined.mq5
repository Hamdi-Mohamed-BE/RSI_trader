#property strict
#property tester_file "orb-combined-input.csv"
input double InpTargetPercent=10;
// Virtual ledger replay only. No order submission or live use.
struct T { int group; string ea,symbol; datetime enter,exit; int side,status; double source_lots,price,risk,entry_fee,exit_cash,lots; };
T ts[];
double bal[3],peak[3],dd[3],minimum[3],daybal[3],daymin[3],worst[3],maxrisk[3],maxmargin[3];
int counts[3],days[3],lastday[3],maxopen[3],skips[3];
datetime target[3],breach[3];
int day=0,fday,ftrade,nextentry=0,active=0,futureticks=0;
long maxstale=0;
int marginerrors=0;
double Margin(int i,double lot) {
 double m=0;
 if(!OrderCalcMargin(ts[i].side>0 ? ORDER_TYPE_BUY:ORDER_TYPE_SELL,ts[i].symbol,lot,ts[i].price,m)) {marginerrors++;return 1e12;}
 return m;
}

void FinishDay() {
 if(day==0) return;
 for(int g=0;g<3;g++) {
  double loss=MathMax(0,daybal[g]-daymin[g]); worst[g]=MathMax(worst[g],loss);
  FileWrite(fday,g,TimeToString((datetime)(day*86400),TIME_DATE),daybal[g],bal[g],daymin[g],loss);
 }
}
double Equity(int g, datetime now) {
 double eq=bal[g];
 for(int i=0;i<ArraySize(ts);i++) if(ts[i].group==g && ts[i].status==1) {
  MqlTick q; if(!SymbolInfoTick(ts[i].symbol,q)) { futureticks++; continue; }
  if(q.time>now) futureticks++;
  maxstale=MathMax(maxstale,(long)(now-q.time));
  double contract=ts[i].symbol=="XAUUSD" ? 100.0:1.0;
  double price=ts[i].side>0 ? q.bid:q.ask;
  eq+=NormalizeDouble(ts[i].side*(price-ts[i].price)*contract*ts[i].lots,2);
 }
 return eq;
}
void Observe(datetime now) {
 for(int g=0;g<3;g++) {
  double eq=Equity(g,now),risk=0,margin=0; int opened=0;
  for(int i=0;i<ArraySize(ts);i++) if(ts[i].group==g && ts[i].status==1) {
   risk+=ts[i].risk/ts[i].source_lots*ts[i].lots; opened++;
   margin+=Margin(i,ts[i].lots);
  }
  peak[g]=MathMax(peak[g],eq); dd[g]=MathMax(dd[g],100*(peak[g]-eq)/peak[g]);
  minimum[g]=MathMin(minimum[g],eq); daymin[g]=MathMin(daymin[g],eq);
  maxrisk[g]=MathMax(maxrisk[g],risk); maxmargin[g]=MathMax(maxmargin[g],margin); maxopen[g]=MathMax(maxopen[g],opened);
  if(breach[g]==0 && (eq<9000 || eq<daybal[g]-500)) breach[g]=now;
  if(target[g]==0 && opened==0 && days[g]>=4 && bal[g]>=10000*(1+InpTargetPercent/100)) target[g]=now;
 }
}
void Step() {
 datetime now=TimeCurrent(); int today=(int)(((long)now+7200)/86400);
 if(today!=day) { FinishDay(); day=today; for(int g=0;g<3;g++) {daybal[g]=bal[g];daymin[g]=bal[g];} }
 if(active==0 && (nextentry>=ArraySize(ts) || ts[nextentry].enter>now)) return;
 // Source fills have second precision. Close existing trades first at a tie.
 Observe(now);
 for(int i=0;i<ArraySize(ts);i++) if(ts[i].status==1 && ts[i].exit<=now) {
  int g=ts[i].group; double ratio=ts[i].lots/ts[i].source_lots;
  double cash=NormalizeDouble(ts[i].exit_cash*ratio,2);
  bal[g]+=cash; ts[i].status=2;active--;counts[g]++;
  FileWrite(ftrade,g,ts[i].ea,TimeToString(ts[i].enter,TIME_DATE|TIME_SECONDS),TimeToString(ts[i].exit,TIME_DATE|TIME_SECONDS),ts[i].lots,NormalizeDouble(ts[i].entry_fee*ratio,2)+cash,bal[g]);
 }
 while(nextentry<ArraySize(ts) && ts[nextentry].enter<=now) {
  int i=nextentry++,g=ts[i].group;
  double eq=Equity(g,now),one=ts[i].risk/ts[i].source_lots;
  double step=SymbolInfoDouble(ts[i].symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(ts[i].symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(ts[i].symbol,SYMBOL_VOLUME_MAX);
  double lot=MathMax(mn,MathMin(mx,MathCeil((eq*.01/one-1e-12)/step)*step));
  double needed=0,used=0;
  needed=Margin(i,lot);
  for(int j=0;j<ArraySize(ts);j++) if(ts[j].group==g && ts[j].status==1) used+=Margin(j,ts[j].lots);
  if(needed+used>eq || eq<=0) {ts[i].status=3;skips[g]++;continue;}
  ts[i].lots=lot;ts[i].status=1;active++;
  bal[g]+=NormalizeDouble(ts[i].entry_fee*lot/ts[i].source_lots,2);
  if(lastday[g]!=today) {days[g]++;lastday[g]=today;}
 }
 Observe(now);
}
int OnInit() {
 if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
 SymbolSelect("XAUUSD",true);SymbolSelect("USTEC",true);
 MqlRates warm[]; CopyRates("XAUUSD",PERIOD_M1,0,10,warm);CopyRates("USTEC",PERIOD_M1,0,10,warm);
 int f=FileOpen("orb-combined-input.csv",FILE_READ|FILE_CSV|FILE_ANSI,';');if(f==INVALID_HANDLE)return INIT_FAILED;
 while(!FileIsEnding(f)) {
  string first=FileReadString(f);if(first=="")break;int n=ArraySize(ts);ArrayResize(ts,n+1);
  ts[n].group=(int)StringToInteger(first);ts[n].ea=FileReadString(f);ts[n].symbol=FileReadString(f);
  ts[n].enter=(datetime)FileReadNumber(f);ts[n].exit=(datetime)FileReadNumber(f);ts[n].side=(int)FileReadNumber(f);
  ts[n].source_lots=FileReadNumber(f);ts[n].price=FileReadNumber(f);ts[n].risk=FileReadNumber(f);
  ts[n].entry_fee=FileReadNumber(f);ts[n].exit_cash=FileReadNumber(f);ts[n].status=0;
 }
 FileClose(f);for(int g=0;g<3;g++){bal[g]=peak[g]=minimum[g]=daybal[g]=daymin[g]=10000;}
 fday=FileOpen("orb-combined-days.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,';');
 ftrade=FileOpen("orb-combined-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,';');
 FileWrite(fday,"group","day","start_balance","end_balance","minimum_equity","daily_loss");
 FileWrite(ftrade,"group","ea","entry","exit","lots","net","balance");
 EventSetTimer(1);return INIT_SUCCEEDED;
}
void OnTick(){Step();}
void OnTimer(){Step();}
void OnDeinit(const int reason){
 FinishDay();FileClose(fday);FileClose(ftrade);EventKillTimer();
 for(int g=0;g<3;g++)PrintFormat("COMBINED|group=%d|balance=%.2f|dd=%.4f|min=%.2f|worst_day=%.2f|max_risk=%.2f|max_margin=%.2f|max_open=%d|trades=%d|days=%d|skips=%d|target=%I64d|breach=%I64d",g,bal[g],dd[g],minimum[g],worst[g],maxrisk[g],maxmargin[g],maxopen[g],counts[g],days[g],skips[g],(long)target[g],(long)breach[g]);
 PrintFormat("COMBINED_QA|active=%d|next=%d|total=%d|future_quotes=%d|max_quote_age_seconds=%I64d|margin_errors=%d",active,nextentry,ArraySize(ts),futureticks,maxstale,marginerrors);
}
