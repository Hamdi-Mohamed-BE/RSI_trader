#ifndef CALYX_FUNDED_GUARD
#define CALYX_FUNDED_GUARD
// Calyx funded_v1 guard (2026-10-28): a configurable prop / funded-account guard for any MT5 hedging account. Built from the tested Turbo v2
// guard (Turbo Guard Build 2026-10-26). Defaults = Leveraged $50k reward account as answered by the firm on 2026-10-27:
//   max loss 6% trailing on the highest CLOSED balance, locked at the initial balance once the account is +6% and after any payout;
//   daily loss 3% from the higher of balance / equity at the 00:00 UTC reset; news: no opening/closing 5 min either side of high-impact news.
// Admission rules (every new entry, account-wide across all EAs): risk = min(risk %, taper % of the room above the floor), cut to fit open /
// per-symbol / daily-loss / buffer limits, lots round DOWN, skipped under the minimum.
// Account rules (every tick): CLOSE ALL positions and pending orders when the day's equity gain reaches the daily-win limit, when the day's
// equity loss reaches the daily-loss limit, or when equity reaches floor + buffer; new entries stay off for the rest of that day.
// Not a guaranteed loss limiter: gaps, slippage, costs and broker failures can exceed planned stops; SL/TP fills inside a news window are
// not prevented. Shared state = account-wide positions/orders + terminal global variables + one file lock. Hedging accounts only.

input int    FundedGuardMode=1;               // 1=enforce; 0=pass-through (strategy tester research only)
input double FundedAccountSize=50000.0;       // firm nominal size; every % below is of this size
input double FundedRiskPercent=0.5;           // max planned stop risk per trade
input double FundedRoomTaperPercent=5.0;      // risk also <= this % of (equity at stops - floor); 0 = off
input double FundedMaxOpenRiskPercent=2.0;    // all open stops + pending orders
input double FundedMaxSymbolRiskPercent=1.5;
input double FundedMaxDailyLossPercent=2.0;   // entries: today's loss + open stops <= this; equity at -this from day reference -> close all
input double FundedMaxDailyWinPercent=0.75;   // equity at +this from day reference -> close all, no new entries today; 0 = off
input double FundedMaxLossPercent=6.0;        // firm max loss (trailing amount)
input int    FundedTrailMode=0;               // 0 = highest closed balance; 1 = also equity high-water (stricter); 2 = static (initial - max loss)
input bool   FundedLockAtInitial=true;        // floor stops at the initial size once reached, and after any payout
input double FundedBufferPercent=0.25;        // keep this % above the floor; equity at floor + buffer -> close all
input double FundedFirmDailyPercent=3.0;      // firm daily loss (breach monitor)
input int    FundedDayResetUtcHour=0;         // firm daily reset hour, UTC
input int    FundedDailyBasis=1;              // 0 = balance at reset; 1 = higher of balance / equity at reset
input int    FundedNewsBlackoutMinutes=5;     // live only (MT5 calendar, high-impact USD): no new entries +- minutes; 0 = off
input bool   FundedNewsCancelPending=false;   // live only: delete pending orders entering a news window (strategies may not re-place them)
input double FundedMinRiskPercent=0.05;
input long   FundedExpectedLogin=0;
input string FundedExpectedServer="";
input string FundedExpectedSymbol="";
input string FundedExpectedCurrency="";
input double FundedReferenceBalance=0.0;      // FLAT balance at install, frozen by the installer
input long   FundedStartUtcTime=0;            // UTC Unix seconds of the install; deals before it are ignored
input double FundedKnownFloor=0.0;            // firm dashboard max-loss level at install (0 = computed)

struct FundedState {
   double balance,equity,anchor,peak,floor,day_real,day_ref,ops_today;
   int    day,withdrawals;bool locked;
};

bool FundedTester(){return MQLInfoInteger(MQL_TESTER)!=0;}
double FundedSize(){return FundedAccountSize;}
double FundedPct(const double p){return p/100.0*FundedAccountSize;}
datetime funded_last_log=0;

string FundedIdentity() {
   uint a=2166136261,b=5381;
   string server=FundedTester()?"TESTER":FundedExpectedServer;
   for(int i=0;i<StringLen(server);i++) {
      uint c=(uint)StringGetCharacter(server,i);
      a=(a^c)*16777619;
      b=((b<<5)+b)^c;
   }
   return "FV1"+IntegerToString(FundedTester()?0:FundedExpectedLogin)+"_"+StringFormat("%08X%08X",a,b);
}
string FundedKey(const string suffix){return FundedIdentity()+"_"+suffix;}
// Strategies may retry a refused entry on every tick: notes and FUNDED_REJECT lines are throttled to one per reason per minute of server time.
string funded_last_why="",funded_last_reject="";
datetime funded_last_reject_t=0;
void FundedNote(const string why) {
   if(why!=funded_last_why || TimeCurrent()-funded_last_log>=60) {
      Print("Funded guard: ",why);funded_last_log=TimeCurrent();funded_last_why=why;
   }
}
void FundedRejectLog(const string reason,const string text) {
   if(reason!=funded_last_reject || TimeCurrent()-funded_last_reject_t>=60) {
      Print("FUNDED_REJECT reason=",reason," ",text);funded_last_reject=reason;funded_last_reject_t=TimeCurrent();
   }
}
bool FundedInputsOK() {
   double p[]={FundedRiskPercent,FundedMaxOpenRiskPercent,FundedMaxSymbolRiskPercent,FundedMaxDailyLossPercent,FundedMaxLossPercent,FundedFirmDailyPercent};
   for(int i=0;i<ArraySize(p);i++)if(!MathIsValidNumber(p[i]) || p[i]<=0 || p[i]>50)return false;
   return MathIsValidNumber(FundedAccountSize) && FundedAccountSize>0 && FundedRoomTaperPercent>=0 && FundedRoomTaperPercent<=100 &&
      FundedMaxDailyWinPercent>=0 && FundedBufferPercent>=0 && FundedBufferPercent<FundedMaxLossPercent && FundedMinRiskPercent>0 &&
      FundedRiskPercent<=FundedMaxOpenRiskPercent && FundedMaxDailyLossPercent<=FundedFirmDailyPercent &&
      FundedTrailMode>=0 && FundedTrailMode<=2 && FundedDailyBasis>=0 && FundedDailyBasis<=1 &&
      FundedDayResetUtcHour>=0 && FundedDayResetUtcHour<=23 && FundedNewsBlackoutMinutes>=0 && FundedNewsBlackoutMinutes<=120;
}
bool FundedAccountOK() {
   if(!FundedInputsOK())return false;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return false;
   if(FundedTester())return FundedGuardMode==0 || FundedGuardMode==1;
   return FundedGuardMode==1 && FundedExpectedLogin>0 && StringLen(FundedExpectedServer)>0 &&
      StringLen(FundedExpectedCurrency)>0 && StringLen(FundedExpectedSymbol)>0 &&
      MathIsValidNumber(FundedReferenceBalance) && FundedReferenceBalance>0 &&
      FundedStartUtcTime>0 && FundedStartUtcTime<=TimeGMT()+60 &&
      AccountInfoInteger(ACCOUNT_LOGIN)==FundedExpectedLogin &&
      AccountInfoString(ACCOUNT_SERVER)==FundedExpectedServer &&
      AccountInfoString(ACCOUNT_CURRENCY)==FundedExpectedCurrency && _Symbol==FundedExpectedSymbol;
}

// Firm day = UTC date after subtracting the reset hour.
int FundedDay(const datetime utc){MqlDateTime t={};TimeToStruct(utc-FundedDayResetUtcHour*3600,t);return t.year*10000+t.mon*100+t.day;}
// Server-to-UTC offset. In the strategy tester TimeGMT() equals server time (offset 0).
bool FundedClock(int &offset,datetime &utc) {
   utc=TimeGMT();
   double delta=(double)(TimeTradeServer()-utc);
   offset=(int)MathRound(delta/900.0)*900;
   return utc>0 && MathAbs(delta-offset)<30 && MathAbs(offset)<=14*3600;
}
double FundedDealNet(const ulong d) {
   return HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_COMMISSION)+
      HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_FEE);
}
// Deal walk since install: closed balance, its peak, today's trading net and the number of balance withdrawals. Cached per EA instance and
// redone only when the deal count, the firm day or the clock offset changes. The rebuilt balance must equal the terminal balance.
int funded_c_total=-1,funded_c_day=-1,funded_c_offset=-1,funded_c_ops=0;
double funded_c_run=0,funded_c_peak=0,funded_c_day_trade=0,funded_c_ops_today=0;
bool FundedWalk(const int today,const int offset,double &run,double &peak,double &day_trade,int &ops,double &ops_today) {
   run=FundedTester()?0.0:FundedReferenceBalance;peak=run;day_trade=0;ops=0;ops_today=0;
   for(int i=0;i<HistoryDealsTotal();i++) {
      ulong d=HistoryDealGetTicket(i);if(d==0)return false;
      datetime when=(datetime)HistoryDealGetInteger(d,DEAL_TIME)-offset;
      if(!FundedTester() && when<(datetime)FundedStartUtcTime)continue;
      int type=(int)HistoryDealGetInteger(d,DEAL_TYPE);
      double net=FundedDealNet(d);
      if(!MathIsValidNumber(net))return false;
      run+=net;
      if(type==DEAL_TYPE_BUY || type==DEAL_TYPE_SELL) {
         if(FundedDay(when)==today)day_trade+=net;
         if(run>peak)peak=run;
         continue;
      }
      if(FundedDay(when)==today)ops_today+=net;   // balance operations today move the day reference too (a payout is not a daily loss)
      if(net>0.001) {
         // Deposits/credits after install change the capital base: live entries stay blocked until reinstall.
         if(!FundedTester())return false;
         peak=MathMax(peak,run);continue;
      }
      if(net<-0.001)ops++;                     // a payout / withdrawal: the floor stays where the firm says (locked at the initial size)
   }
   return MathIsValidNumber(run);
}
bool FundedLedger(FundedState &s,const int offset,const datetime utc) {
   if(!HistorySelect(0,TimeTradeServer()+60))return false;
   s.day=FundedDay(utc);
   double size=FundedSize(),trail=FundedPct(FundedMaxLossPercent);
   int total=HistoryDealsTotal();
   if(total!=funded_c_total || s.day!=funded_c_day || offset!=funded_c_offset) {
      if(!FundedWalk(s.day,offset,funded_c_run,funded_c_peak,funded_c_day_trade,funded_c_ops,funded_c_ops_today)){funded_c_total=-1;return false;}
      funded_c_total=total;funded_c_day=s.day;funded_c_offset=offset;
   }
   double peak=funded_c_peak;int ops=funded_c_ops;
   s.balance=AccountInfoDouble(ACCOUNT_BALANCE);s.equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(s.balance) || !MathIsValidNumber(s.equity) || MathAbs(funded_c_run-s.balance)>0.05)return false;
   if(FundedTrailMode==1) {
      string k=FundedKey("EQPEAK");
      if(!GlobalVariableCheck(k))GlobalVariableSet(k,MathMin(s.equity,s.balance));
      peak=MathMax(peak,GlobalVariableGet(k));
   }
   double base=FundedTester()?size:FundedReferenceBalance;
   double floor=FundedTrailMode==2?base-trail:peak-trail;
   s.locked=FundedLockAtInitial && FundedTrailMode!=2 && (peak-trail>=size-1e-6 || ops>0 || FundedKnownFloor>=size-1e-6);
   if(s.locked)floor=size;
   if(FundedKnownFloor>0)floor=MathMax(floor,FundedKnownFloor);
   s.peak=peak;s.floor=floor;s.day_real=funded_c_day_trade;s.withdrawals=ops;s.ops_today=funded_c_ops_today;
   s.anchor=s.balance-funded_c_day_trade;
   // Day reference = higher of balance / equity at the first tick after the reset (recorded by FundedPulse with that moment's balance-operation
   // total), moved by any withdrawal / deposit made since; the balance anchor already excludes balance operations.
   string dk=FundedKey("DREF_"+IntegerToString(s.day)),ok_=FundedKey("DREFOPS_"+IntegerToString(s.day));
   s.day_ref=FundedDailyBasis==1 && GlobalVariableCheck(dk) && GlobalVariableCheck(ok_)?MathMax(s.anchor,GlobalVariableGet(dk)+s.ops_today-GlobalVariableGet(ok_)):s.anchor;
   return s.anchor>0;
}
bool FundedUnitRisk(const string symbol,const bool buy,const double price,const double sl,double &risk) {
   if(sl<=0 || price<=0 || (buy && sl>=price) || (!buy && sl<=price))return false;
   double profit=0;
   if(!OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,symbol,1.0,price,sl,profit) || !MathIsValidNumber(profit) || profit>=0)return false;
   risk=-profit;return risk>0;
}
double FundedLotsDown(const double desired,const double step) {
   if(desired<=0 || step<=0)return 0;
   return NormalizeDouble(MathFloor(desired/step+1e-9)*step,8);
}
bool FundedBuyType(const long type){return type==ORDER_TYPE_BUY || type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_BUY_STOP;}
bool FundedPendingType(const long type){return type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_SELL_LIMIT || type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_SELL_STOP;}
// Same broker filling adaptation as the Prop Ready guard (IOC-only brokers); RETURN is never sent to Market Execution.
bool FundedMarketFilling(const string symbol,ENUM_ORDER_TYPE_FILLING &filling) {
   long execution=0,flags=0;
   if(StringLen(symbol)==0 || !SymbolInfoInteger(symbol,SYMBOL_TRADE_EXEMODE,execution) ||
      !SymbolInfoInteger(symbol,SYMBOL_FILLING_MODE,flags))return false;
   bool request=execution==SYMBOL_TRADE_EXECUTION_REQUEST || execution==SYMBOL_TRADE_EXECUTION_INSTANT;
   if(!request && execution!=SYMBOL_TRADE_EXECUTION_MARKET && execution!=SYMBOL_TRADE_EXECUTION_EXCHANGE)return false;
   bool fok=(flags&SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK;
   bool ioc=(flags&SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC;
   if(filling==ORDER_FILLING_FOK && (request || fok))return true;
   if(filling==ORDER_FILLING_IOC && (request || ioc))return true;
   if(filling==ORDER_FILLING_RETURN && execution!=SYMBOL_TRADE_EXECUTION_MARKET)return true;
   if(fok || request){filling=ORDER_FILLING_FOK;return true;}
   if(ioc){filling=ORDER_FILLING_IOC;return true;}
   if(execution!=SYMBOL_TRADE_EXECUTION_MARKET){filling=ORDER_FILLING_RETURN;return true;}
   return false;
}
// Account-wide planned stop risk (Turbo v2 rule): a position keeps its initial stop risk per lot until it closes; pending orders reserve
// their full risk until they fill or are removed. stress = lower of (balance - planned risk) and (equity - pending - distance to stops).
bool FundedExposure(const string symbol,const double balance,const double equity,double &total,double &same,double &stress) {
   total=0;same=0;double pending=0,to_stop=0;
   for(int i=0;i<OrdersTotal();i++) {
      ulong t=OrderGetTicket(i);if(t==0)return false;
      long type=OrderGetInteger(ORDER_TYPE);
      if(!FundedPendingType(type))return false;
      string s=OrderGetString(ORDER_SYMBOL);
      double unit=0,v=OrderGetDouble(ORDER_VOLUME_CURRENT);
      if(!FundedUnitRisk(s,FundedBuyType(type),OrderGetDouble(ORDER_PRICE_OPEN),OrderGetDouble(ORDER_SL),unit))return false;
      total+=unit*v;pending+=unit*v;if(s==symbol)same+=unit*v;
   }
   for(int i=0;i<PositionsTotal();i++) {
      ulong ticket=PositionGetTicket(i);if(ticket==0)return false;
      string s=PositionGetString(POSITION_SYMBOL);
      long id=PositionGetInteger(POSITION_IDENTIFIER);
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double sl=PositionGetDouble(POSITION_SL),v=PositionGetDouble(POSITION_VOLUME),open=PositionGetDouble(POSITION_PRICE_OPEN);
      if(sl<=0 || v<=0)return false;
      string key=FundedKey("R_"+IntegerToString(id));
      double unit=GlobalVariableCheck(key)?GlobalVariableGet(key):0;
      if(unit<=0) {
         double osl=HistoryOrderSelect((ulong)id)?HistoryOrderGetDouble((ulong)id,ORDER_SL):0;
         if(!FundedUnitRisk(s,buy,open,osl>0?osl:sl,unit))return false;
         GlobalVariableSet(key,unit);
      }
      double at_stop=0,now_to_stop=0;
      if(!OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,s,v,open,sl,at_stop) || !MathIsValidNumber(at_stop))return false;
      double risk=MathMax(unit*v,MathMax(0,-at_stop));
      double price=buy?SymbolInfoDouble(s,SYMBOL_BID):SymbolInfoDouble(s,SYMBOL_ASK);
      if(price>0 && OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,s,v,price,sl,now_to_stop) && MathIsValidNumber(now_to_stop))
         to_stop+=MathMax(0,-now_to_stop);
      total+=risk;if(s==symbol)same+=risk;
   }
   string lid=FundedKey("LAST_ID");                // an entry filled in the last 10 s that is not visible yet (cross-chart race) still counts
   if(GlobalVariableCheck(lid) && TimeLocal()-GlobalVariableGet(FundedKey("LAST_T"))<10) {
      ulong id=(ulong)GlobalVariableGet(lid);bool seen=false;
      for(int i=0;i<PositionsTotal() && !seen;i++)if(PositionGetTicket(i)>0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER)==id)seen=true;
      for(int i=0;i<OrdersTotal() && !seen;i++)if(OrderGetTicket(i)==id)seen=true;
      if(!seen && !FundedTester()){double r=GlobalVariableGet(FundedKey("LAST_R"));total+=r;pending+=r;}
   }
   stress=MathMin(balance-total,equity-pending-to_stop);
   return MathIsValidNumber(total) && MathIsValidNumber(stress);
}
// High-impact USD calendar events within +-N minutes (live only; the strategy tester has no economic calendar). Cached for 60 s.
datetime funded_news_t=0;bool funded_news_on=false;
bool FundedNewsWindow() {
   if(FundedNewsBlackoutMinutes<=0 || FundedTester())return false;
   datetime now=TimeTradeServer();
   if(now-funded_news_t<60)return funded_news_on;
   funded_news_t=now;funded_news_on=false;
   MqlCalendarValue v[];long span=(long)FundedNewsBlackoutMinutes*60+60;
   if(CalendarValueHistory(v,now-span,now+span,NULL,"USD")>0)
      for(int i=0;i<ArraySize(v) && !funded_news_on;i++) {
         MqlCalendarEvent e;
         if(CalendarEventById(v[i].event_id,e) && e.importance==CALENDAR_IMPORTANCE_HIGH && MathAbs((long)(v[i].time-now))<=(long)FundedNewsBlackoutMinutes*60)funded_news_on=true;
      }
   return funded_news_on;
}
bool FundedReject(MqlTradeResult &result,const string why) {
   ZeroMemory(result);result.retcode=TRADE_RETCODE_REJECT;result.comment="Funded guard: "+why;
   FundedNote(why);return false;
}
string FundedStateText(const FundedState &s,const double total,const double same,const double stress) {
   return StringFormat("bal=%.2f eq=%.2f open=%.2f sym=%.2f stress=%.2f anchor=%.2f dayref=%.2f peak=%.2f floor=%.2f locked=%d dayreal=%.2f day=%d",
      s.balance,s.equity,total,same,stress,s.anchor,s.day_ref,s.peak,s.floor,(int)s.locked,s.day_real,s.day);
}
bool FundedDayLocked(const int day){return GlobalVariableCheck(FundedKey("WIN_"+IntegerToString(day))) || GlobalVariableCheck(FundedKey("LOSS_"+IntegerToString(day))) ||
   GlobalVariableCheck(FundedKey("FLOOR_"+IntegerToString(day)));}
bool FundedAdmit(MqlTradeRequest &r,MqlTradeResult &result,double &admitted) {
   bool market=r.action==TRADE_ACTION_DEAL && r.position==0 && (r.type==ORDER_TYPE_BUY || r.type==ORDER_TYPE_SELL);
   bool pending=r.action==TRADE_ACTION_PENDING && FundedPendingType(r.type);
   if(!market && !pending)return FundedReject(result,"unsupported entry type");
   if(!FundedTester() && (r.symbol!=FundedExpectedSymbol || !TerminalInfoInteger(TERMINAL_CONNECTED)))return FundedReject(result,"symbol/connection mismatch");
   MqlTick tick={};
   if(!SymbolInfoTick(r.symbol,tick) || tick.bid<=0 || tick.ask<=0 || (!FundedTester() && TimeTradeServer()-tick.time>30))return FundedReject(result,"stale quote");
   bool buy=FundedBuyType(r.type);
   double price=market?(buy?tick.ask:tick.bid):r.price,unit=0;
   if(!FundedUnitRisk(r.symbol,buy,price,r.sl,unit))return FundedReject(result,"missing/invalid SL");
   int offset=0;datetime utc=0;FundedState s={};
   if(!FundedClock(offset,utc) || !FundedLedger(s,offset,utc))return FundedReject(result,"clock/history/capital baseline unavailable");
   if(GlobalVariableCheck(FundedKey("BREACHED")) || GlobalVariableCheck(FundedKey("UNCERTAIN")))return FundedReject(result,"latched stop: review required");
   double total=0,same=0,stress=0;
   if(!FundedExposure(r.symbol,s.balance,s.equity,total,same,stress))return FundedReject(result,"unprotected/unknown exposure");
   string state=FundedStateText(s,total,same,stress);
   if(FundedDayLocked(s.day)){FundedReject(result,"daily win/loss/floor stop reached today");FundedRejectLog("daylock",state);return false;}
   if(FundedMaxDailyWinPercent>0 && s.equity-s.day_ref>=FundedPct(FundedMaxDailyWinPercent)-1e-9){FundedReject(result,"daily win limit");FundedRejectLog("dailywin",state);return false;}
   if(FundedNewsWindow()){FundedReject(result,"high-impact news window");FundedRejectLog("news",state);return false;}
   double room=stress-s.floor,cap=FundedPct(FundedRiskPercent),risk=cap;
   if(FundedRoomTaperPercent>0 && FundedRoomTaperPercent/100.0*room<risk)risk=FundedRoomTaperPercent/100.0*room;
   double fit_open=FundedPct(FundedMaxOpenRiskPercent)-total,fit_sym=FundedPct(FundedMaxSymbolRiskPercent)-same;
   double fit_day=FundedPct(FundedMaxDailyLossPercent)-(s.day_ref-stress),fit_room=room-FundedPct(FundedBufferPercent);
   double fit=MathMin(MathMin(fit_open,fit_sym),MathMin(fit_day,fit_room));
   if(fit<risk)risk=fit;
   string why=risk==fit?(fit==fit_open?"open":fit==fit_sym?"symbol":fit==fit_day?"daily":"buffer"):(risk<cap?"taper":"cap");
   if(risk<FundedPct(FundedMinRiskPercent)){FundedReject(result,"below minimum risk ("+why+")");FundedRejectLog("min_"+why,"budget="+DoubleToString(risk,2)+" "+state);return false;}
   double step=SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_STEP);
   double volume=FundedLotsDown(MathMin(r.volume,MathMin(risk/unit,SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MAX))),step);
   if(volume<SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MIN)-1e-9){FundedReject(result,"minimum lot exceeds budget");FundedRejectLog("minlot","budget="+DoubleToString(risk,2)+" unit="+DoubleToString(unit,4)+" "+state);return false;}
   double margin=0;
   if(!OrderCalcMargin(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,r.symbol,volume,price,margin) || !MathIsValidNumber(margin) || margin<0 ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.9){FundedReject(result,"margin");FundedRejectLog("margin",state);return false;}
   if(!FundedTester()) {
      string last=FundedKey("ENTRY_WAIT");
      if(GlobalVariableCheck(last) && TimeLocal()<GlobalVariableGet(last))return FundedReject(result,"entry reconciliation wait");
      GlobalVariableSet(last,(double)(TimeLocal()+1));
   }
   admitted=unit*volume;
   PrintFormat("FUNDED_ADMIT sym=%s type=%d price=%.5f sl=%.5f unit=%.6f step=%.4f req=%.4f vol=%.4f risk=%.2f budget=%.2f bind=%s room=%.2f %s",
      r.symbol,(int)r.type,price,r.sl,unit,step,r.volume,volume,admitted,risk,why,room,state);
   r.volume=volume;if(market)r.price=price;
   return true;
}
bool FundedOrderSend(const MqlTradeRequest &request,MqlTradeResult &result) {
   if(FundedTester() && FundedGuardMode==0) {
      bool sent=OrderSend(request,result);         // research pass-through: identical request
      if(sent && request.position==0 && (request.action==TRADE_ACTION_DEAL || request.action==TRADE_ACTION_PENDING) &&
         (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL || result.retcode==TRADE_RETCODE_PLACED))
         PrintFormat("FUNDED_SEEN order=%I64u deal=%I64u sym=%s type=%d price=%.5f sl=%.5f vol=%.4f",result.order,result.deal,request.symbol,(int)request.type,
            request.action==TRADE_ACTION_DEAL?(result.price>0?result.price:request.price):request.price,request.sl,result.volume>0?result.volume:request.volume);
      return sent;
   }
   if(!FundedAccountOK())return FundedReject(result,"account/server/currency/symbol lock or invalid inputs");
   MqlTradeRequest r=request;
   bool closing=(r.action==TRADE_ACTION_DEAL && r.position>0) || r.action==TRADE_ACTION_CLOSE_BY;
   bool protection=r.action==TRADE_ACTION_SLTP;
   bool modify=r.action==TRADE_ACTION_MODIFY;
   bool removing=r.action==TRADE_ACTION_REMOVE;
   bool entry=!closing && !protection && !modify && !removing;
   if(r.action==TRADE_ACTION_DEAL && !FundedMarketFilling(r.symbol,r.type_filling))return FundedReject(result,"unsupported broker filling policy");
   int lock=FileOpen(FundedIdentity()+".lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(lock==INVALID_HANDLE)return FundedReject(result,"portfolio busy");
   int offset=0;datetime utc=0;
   if(!FundedClock(offset,utc) && entry){FileClose(lock);return FundedReject(result,"clock unavailable");}
   string counter=FundedKey("REQ_"+IntegerToString(FundedDay(utc)));
   double requests=GlobalVariableCheck(counter)?GlobalVariableGet(counter):0;
   if(requests>=1900 || (entry && requests>=1400)){FileClose(lock);return FundedReject(result,"daily request budget");}
   if(protection) {
      if(!PositionSelectByTicket(r.position) || r.sl<=0){FileClose(lock);return FundedReject(result,"cannot remove SL");}
      double old=PositionGetDouble(POSITION_SL);
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      if(old>0 && ((buy && r.sl<old-1e-10) || (!buy && r.sl>old+1e-10))){FileClose(lock);return FundedReject(result,"cannot widen SL");}
   }
   if(modify) {
      if(!OrderSelect(r.order) || r.sl<=0){FileClose(lock);return FundedReject(result,"cannot remove pending SL");}
      long type=OrderGetInteger(ORDER_TYPE);string s=OrderGetString(ORDER_SYMBOL);
      double v=OrderGetDouble(ORDER_VOLUME_CURRENT),before=0,after=0;
      if(!FundedUnitRisk(s,FundedBuyType(type),OrderGetDouble(ORDER_PRICE_OPEN),OrderGetDouble(ORDER_SL),before) ||
         !FundedUnitRisk(s,FundedBuyType(type),r.price,r.sl,after) || after*v>before*v+0.01){FileClose(lock);return FundedReject(result,"pending modify raises risk");}
   }
   double admitted=0;
   if(entry && !FundedAdmit(r,result,admitted)){FileClose(lock);return false;}
   GlobalVariableSet(counter,requests+1);
   bool sent=OrderSend(r,result);
   bool done=sent && (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL || (r.action==TRADE_ACTION_PENDING && result.retcode==TRADE_RETCODE_PLACED));
   if(entry && done) {
      ulong id=result.order;
      if(result.deal>0 && HistoryDealSelect(result.deal))id=(ulong)HistoryDealGetInteger(result.deal,DEAL_POSITION_ID);
      double unit=0,fill=r.action==TRADE_ACTION_DEAL?(result.price>0?result.price:r.price):r.price;
      if(id>0 && FundedUnitRisk(r.symbol,FundedBuyType(r.type),fill,r.sl,unit)) {
         GlobalVariableSet(FundedKey("R_"+IntegerToString((long)id)),unit);
         GlobalVariableSet(FundedKey("LAST_ID"),(double)id);GlobalVariableSet(FundedKey("LAST_R"),unit*r.volume);
         GlobalVariableSet(FundedKey("LAST_T"),(double)TimeLocal());
      }
      PrintFormat("FUNDED_FILL id=%I64u sym=%s type=%d price=%.5f sl=%.5f vol=%.4f unit=%.6f risk=%.2f",id,r.symbol,(int)r.type,fill,r.sl,r.volume,unit,unit*r.volume);
   }
   if(entry && !done && (result.retcode==TRADE_RETCODE_TIMEOUT || result.retcode==TRADE_RETCODE_CONNECTION ||
      (sent && r.action==TRADE_ACTION_DEAL && result.retcode==TRADE_RETCODE_PLACED))) {
      GlobalVariableSet(FundedKey("UNCERTAIN"),1);
      Print("Funded guard: uncertain execution; NEW entries latched off. Reconcile orders/history, then clear the latch.");
   }
   FileClose(lock);return sent;
}

// Account-wide close of every position and pending order (daily win / daily loss / floor buffer). Throttled to one attempt per 5 s.
datetime funded_close_t=0;
int FundedCloseAll(const string why) {
   if(TimeCurrent()-funded_close_t<5)return -1;
   funded_close_t=TimeCurrent();int left=0;
   for(int i=OrdersTotal()-1;i>=0;i--) {
      ulong t=OrderGetTicket(i);if(t==0)continue;
      MqlTradeRequest q={};MqlTradeResult res={};q.action=TRADE_ACTION_REMOVE;q.order=t;
      if(!OrderSend(q,res) || res.retcode!=TRADE_RETCODE_DONE)left++;
   }
   for(int i=PositionsTotal()-1;i>=0;i--) {
      ulong t=PositionGetTicket(i);if(t==0)continue;
      string s=PositionGetString(POSITION_SYMBOL);bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      MqlTick k={};if(!SymbolInfoTick(s,k)){left++;continue;}
      MqlTradeRequest q={};MqlTradeResult res={};
      q.action=TRADE_ACTION_DEAL;q.position=t;q.symbol=s;q.volume=PositionGetDouble(POSITION_VOLUME);q.magic=PositionGetInteger(POSITION_MAGIC);
      q.type=buy?ORDER_TYPE_SELL:ORDER_TYPE_BUY;q.price=buy?k.bid:k.ask;q.deviation=1000;q.type_filling=ORDER_FILLING_IOC;q.comment="funded_v1 "+why;
      if(!FundedMarketFilling(s,q.type_filling) || !OrderSend(q,res) || (res.retcode!=TRADE_RETCODE_DONE && res.retcode!=TRADE_RETCODE_DONE_PARTIAL))left++;
   }
   PrintFormat("FUNDED_CLOSEALL reason=%s left=%d",why,left);
   return left;
}
// Monitoring + account rules. Never suppresses strategy management (returns true unless the account lock fails).
int    funded_day=0;
double funded_balance=-1,funded_floor=0,funded_ref=0,funded_min_eq_room=1e18,funded_min_day_room=1e18;
bool FundedPulse() {
   if(FundedTester() && FundedGuardMode==0)return true;
   if(!FundedAccountOK())return false;
   int offset=0;datetime utc=0;
   if(!FundedClock(offset,utc))return true;
   int day=FundedDay(utc);
   double balance=AccountInfoDouble(ACCOUNT_BALANCE),equity=AccountInfoDouble(ACCOUNT_EQUITY);
   string dk=FundedKey("DREF_"+IntegerToString(day));
   if(day!=funded_day || balance!=funded_balance || !GlobalVariableCheck(dk)) {
      FundedState s={};
      if(!FundedLedger(s,offset,utc))return true;
      if(!GlobalVariableCheck(dk)) {             // first tick after the reset: balance / equity reference + that moment's balance-operation total
         GlobalVariableSet(FundedKey("DREFOPS_"+IntegerToString(day)),s.ops_today);GlobalVariableSet(dk,MathMax(balance,equity));
         if(!FundedLedger(s,offset,utc))return true;
      }
      if(day!=funded_day) {
         if(funded_day!=0)PrintFormat("FUNDED_DAYEND day=%d min_eq_room=%.2f min_daily_room=%.2f",funded_day,funded_min_eq_room,funded_min_day_room);
         funded_min_eq_room=1e18;funded_min_day_room=1e18;funded_day=day;
         PrintFormat("FUNDED_DAY day=%d bal=%.2f eq=%.2f anchor=%.2f dayref=%.2f peak=%.2f floor=%.2f locked=%d",day,s.balance,s.equity,s.anchor,s.day_ref,s.peak,s.floor,(int)s.locked);
      }
      funded_balance=s.balance;funded_floor=s.floor;funded_ref=s.day_ref;
   }
   if(FundedTrailMode==1) {
      string k=FundedKey("EQPEAK");
      if(GlobalVariableCheck(k) && equity>GlobalVariableGet(k))GlobalVariableSet(k,equity);
   }
   double firm_daily=funded_ref-FundedFirmDailyPercent/100.0*funded_ref;
   funded_min_eq_room=MathMin(funded_min_eq_room,equity-funded_floor);
   funded_min_day_room=MathMin(funded_min_day_room,equity-firm_daily);
   string sd=IntegerToString(day);
   bool open=PositionsTotal()>0 || OrdersTotal()>0;
   if(FundedMaxDailyWinPercent>0 && equity-funded_ref>=FundedPct(FundedMaxDailyWinPercent)) {
      if(!GlobalVariableCheck(FundedKey("WIN_"+sd))){GlobalVariableSet(FundedKey("WIN_"+sd),1);PrintFormat("FUNDED_DAILYWIN day=%d eq=%.2f dayref=%.2f",day,equity,funded_ref);}
      if(open && !FundedNewsWindow())FundedCloseAll("daily win");                 // closing inside a news window is prohibited: wait
   }
   if(equity<=funded_ref-FundedPct(FundedMaxDailyLossPercent)) {
      if(!GlobalVariableCheck(FundedKey("LOSS_"+sd))){GlobalVariableSet(FundedKey("LOSS_"+sd),1);PrintFormat("FUNDED_DAILYLOSS day=%d eq=%.2f dayref=%.2f",day,equity,funded_ref);}
      if(open)FundedCloseAll("daily loss");
   }
   if(equity<=funded_floor+FundedPct(FundedBufferPercent)) {
      if(!GlobalVariableCheck(FundedKey("FLOOR_"+sd))){GlobalVariableSet(FundedKey("FLOOR_"+sd),1);PrintFormat("FUNDED_FLOORSTOP day=%d eq=%.2f floor=%.2f",day,equity,funded_floor);}
      if(open)FundedCloseAll("floor buffer");
   }
   if(FundedNewsCancelPending && OrdersTotal()>0 && FundedNewsWindow()) {
      for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);if(t==0)continue;MqlTradeRequest q={};MqlTradeResult res={};q.action=TRADE_ACTION_REMOVE;q.order=t;if(!OrderSend(q,res))FundedNote("news pending delete failed "+IntegerToString(res.retcode));}
   }
   if((equity<=funded_floor || equity<=firm_daily) && !GlobalVariableCheck(FundedKey("BREACHED"))) {
      GlobalVariableSet(FundedKey("BREACHED"),1);
      PrintFormat("FUNDED_BREACH day=%d eq=%.2f floor=%.2f daily=%.2f (new entries latched off)",day,equity,funded_floor,firm_daily);
   }
   return true;
}
int FundedInit() {
   if(!FundedAccountOK()){Print("Funded guard initialization blocked: account/server/currency/symbol/baseline lock, netting account or invalid inputs.");return INIT_FAILED;}
   if(FundedTester() && FundedGuardMode==0){Print("Funded guard PASS-THROUGH (tester research only).");return INIT_SUCCEEDED;}
   PrintFormat("Funded guard armed: size %.0f; risk %.2f%% (taper %.1f%% of room); open %.2f%%; symbol %.2f%%; daily loss %.2f%% close-all; daily win %.2f%% close-all; max loss %.2f%% mode %d lock %d; buffer %.2f%%; reset %02d:00 UTC; news +-%d min.",
      FundedSize(),FundedRiskPercent,FundedRoomTaperPercent,FundedMaxOpenRiskPercent,FundedMaxSymbolRiskPercent,FundedMaxDailyLossPercent,FundedMaxDailyWinPercent,
      FundedMaxLossPercent,FundedTrailMode,(int)FundedLockAtInitial,FundedBufferPercent,FundedDayResetUtcHour,FundedNewsBlackoutMinutes);
   return INIT_SUCCEEDED;
}
#endif
