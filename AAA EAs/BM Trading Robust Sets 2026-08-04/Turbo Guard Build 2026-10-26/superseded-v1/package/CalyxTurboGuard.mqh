#ifndef CALYX_TURBO_GUARD
#define CALYX_TURBO_GUARD
// Calyx Turbo guard (2026-10-26) for the Turbo $50k reward account. ADMISSION guard, NOT a guaranteed loss
// limiter: gaps, slippage, swaps, costs and broker failures can exceed planned stop risk. It never closes trades.
// Profile = 'improved 0.75' guard of Turbo 50k Funded Portfolio 2026-10-26 (sim.py kernel), as fractions of
// TurboAccountSize:
//   trade risk = min(0.75%, 5% of trailing room), cut to fit every limit below, skipped under 0.05% ($25);
//   all open stop risk (positions + pending orders) <= 2%; per symbol <= 1.5%;
//   today's realised loss + open stop risk <= 2% (daily soft stop; firm limit 3%);
//   keep 0.25% above the trailing floor; no new entries once today's realised profit >= 0.75%.
// Firm model (CONFIRM WITH THE FIRM): floor = highest closed balance - 6%, re-based to the balance after each
// withdrawal; daily loss 3% of the firm-day start balance; firm day = UTC+2 winter / UTC+3 summer (EU DST).
// Shared state: account-wide positions/orders + terminal global variables + one file lock. Hedging only.

input int    TurboGuardMode=1;            // 1=enforce; 0=pass-through (strategy tester research only)
input double TurboAccountSize=50000.0;    // firm nominal account size; every limit is a fraction of it
input long   TurboExpectedLogin=0;
input string TurboExpectedServer="";
input string TurboExpectedSymbol="";
input string TurboExpectedCurrency="";
input double TurboReferenceBalance=0.0;   // FLAT balance at install, frozen by the installer
input long   TurboStartUtcTime=0;         // UTC Unix seconds of the install; deals before it are ignored
input double TurboKnownFloor=0.0;         // firm dashboard floor at install (0 = reference - 6%)
input bool   TurboRebaseOnWithdrawal=true;// floor re-bases to (balance after a withdrawal) - 6%
input bool   TurboTrailEquity=false;      // stricter: the floor also trails the equity high-water mark
input bool   TurboTesterRewards=false;    // tester only: withdraw eligible profit every 14 days (sim.py rule)

#define TURBO_TRADE   0.0075
#define TURBO_TAPER   0.05
#define TURBO_OPEN    0.02
#define TURBO_SYMBOL  0.015
#define TURBO_DSTOP   0.02
#define TURBO_BUFFER  0.0025
#define TURBO_DCAP    0.0075
#define TURBO_TRAIL   0.06
#define TURBO_DAILY   0.03
#define TURBO_MINRISK 0.0005

struct TurboState {
   double balance,equity,anchor,peak,floor,day_real;
   int    day,withdrawals;
};

bool TurboTester(){return MQLInfoInteger(MQL_TESTER)!=0;}
double TurboSize(){return TurboAccountSize;}
datetime turbo_last_log=0;

string TurboIdentity() {
   uint a=2166136261,b=5381;
   string server=TurboTester()?"TESTER":TurboExpectedServer;
   for(int i=0;i<StringLen(server);i++) {
      uint c=(uint)StringGetCharacter(server,i);
      a=(a^c)*16777619;
      b=((b<<5)+b)^c;
   }
   return "TB"+IntegerToString(TurboTester()?0:TurboExpectedLogin)+"_"+StringFormat("%08X%08X",a,b);
}
string TurboKey(const string suffix){return TurboIdentity()+"_"+suffix;}
void TurboNote(const string why) {
   if(TurboTester() || TimeLocal()-turbo_last_log>=60) {
      Print("Turbo guard: ",why);turbo_last_log=TimeLocal();
   }
}
bool TurboAccountOK() {
   if(!MathIsValidNumber(TurboAccountSize) || TurboAccountSize<=0)return false;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return false;
   if(TurboTester())return TurboGuardMode==0 || TurboGuardMode==1;
   return TurboGuardMode==1 && TurboExpectedLogin>0 && StringLen(TurboExpectedServer)>0 &&
      StringLen(TurboExpectedCurrency)>0 && StringLen(TurboExpectedSymbol)>0 &&
      MathIsValidNumber(TurboReferenceBalance) && TurboReferenceBalance>0 &&
      TurboStartUtcTime>0 && TurboStartUtcTime<=TimeGMT()+60 && !TurboTesterRewards &&
      AccountInfoInteger(ACCOUNT_LOGIN)==TurboExpectedLogin &&
      AccountInfoString(ACCOUNT_SERVER)==TurboExpectedServer &&
      AccountInfoString(ACCOUNT_CURRENCY)==TurboExpectedCurrency && _Symbol==TurboExpectedSymbol;
}

// Firm day: EET/EEST (UTC+2, UTC+3 from the last Sunday of March to the last Sunday of October, 01:00 UTC).
datetime TurboLastSunday(const int year,const int month) {
   MqlDateTime t={};t.year=year;t.mon=month;t.day=31;t.hour=1;
   datetime d=StructToTime(t);TimeToStruct(d,t);return d-t.day_of_week*86400;
}
int TurboFirmOffset(const datetime utc) {
   MqlDateTime t={};TimeToStruct(utc,t);
   return utc>=TurboLastSunday(t.year,3) && utc<TurboLastSunday(t.year,10)?10800:7200;
}
int TurboDay(const datetime utc) {
   MqlDateTime t={};TimeToStruct(utc+TurboFirmOffset(utc),t);
   return t.year*10000+t.mon*100+t.day;
}
int TurboDayIndex(const datetime utc){return (int)((long)(utc+TurboFirmOffset(utc))/86400);}
// Server-to-UTC offset. In the strategy tester TimeGMT() equals server time (offset 0).
bool TurboClock(int &offset,datetime &utc) {
   utc=TimeGMT();
   double delta=(double)(TimeTradeServer()-utc);
   offset=(int)MathRound(delta/900.0)*900;
   return utc>0 && MathAbs(delta-offset)<30 && MathAbs(offset)<=14*3600;
}
double TurboDealNet(const ulong d) {
   return HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_COMMISSION)+
      HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_FEE);
}
// Rebuilds balance, peak closed balance, floor and the firm-day start balance from the deal history since
// install, and requires the rebuilt balance to equal the terminal balance (fail closed on any gap).
bool TurboLedger(TurboState &s,const int offset,const datetime utc) {
   if(!HistorySelect(0,TimeTradeServer()+60))return false;
   s.day=TurboDay(utc);
   double size=TurboSize(),run=TurboTester()?0.0:TurboReferenceBalance;
   double peak=run;
   if(TurboKnownFloor>0)peak=MathMax(peak,TurboKnownFloor+TURBO_TRAIL*size);
   double day_trade=0;int ops=0;
   for(int i=0;i<HistoryDealsTotal();i++) {
      ulong d=HistoryDealGetTicket(i);if(d==0)return false;
      datetime when=(datetime)HistoryDealGetInteger(d,DEAL_TIME)-offset;
      if(!TurboTester() && when<(datetime)TurboStartUtcTime)continue;
      int type=(int)HistoryDealGetInteger(d,DEAL_TYPE);
      double net=TurboDealNet(d);
      if(!MathIsValidNumber(net))return false;
      run+=net;
      if(type==DEAL_TYPE_BUY || type==DEAL_TYPE_SELL) {
         if(TurboDay(when)==s.day)day_trade+=net;
         if(run>peak)peak=run;
         continue;
      }
      if(net>0.001) {
         // Deposits/credits after install change the capital base: live entries stay blocked until reinstall.
         if(!TurboTester())return false;
         peak=run;ops++;continue;
      }
      if(net<-0.001){ops++;if(TurboRebaseOnWithdrawal)peak=run;}
   }
   s.balance=AccountInfoDouble(ACCOUNT_BALANCE);s.equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(s.balance) || !MathIsValidNumber(s.equity) || MathAbs(run-s.balance)>0.05)return false;
   if(TurboTrailEquity) {
      string k=TurboKey("EQPEAK"),n=TurboKey("EQPEAK_OPS");
      if(!GlobalVariableCheck(k) || !GlobalVariableCheck(n) || (int)GlobalVariableGet(n)!=ops) {
         GlobalVariableSet(k,MathMin(s.equity,s.balance));GlobalVariableSet(n,ops);
      }
      peak=MathMax(peak,GlobalVariableGet(k));
   }
   s.peak=peak;s.floor=peak-TURBO_TRAIL*size;s.anchor=s.balance-day_trade;s.day_real=day_trade;s.withdrawals=ops;
   return s.anchor>0;
}
double TurboDayTradeNet(const int day,const int offset) {
   if(!HistorySelect(0,TimeTradeServer()+60))return 0;
   double sum=0;
   for(int i=0;i<HistoryDealsTotal();i++) {
      ulong d=HistoryDealGetTicket(i);if(d==0)continue;
      int type=(int)HistoryDealGetInteger(d,DEAL_TYPE);
      if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)continue;
      if(TurboDay((datetime)HistoryDealGetInteger(d,DEAL_TIME)-offset)==day)sum+=TurboDealNet(d);
   }
   return sum;
}
bool TurboUnitRisk(const string symbol,const bool buy,const double price,const double sl,double &risk) {
   if(sl<=0 || price<=0 || (buy && sl>=price) || (!buy && sl<=price))return false;
   double profit=0;
   if(!OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,symbol,1.0,price,sl,profit) || !MathIsValidNumber(profit) || profit>=0)return false;
   risk=-profit;return risk>0;
}
double TurboLotsDown(const double desired,const double step) {
   if(desired<=0 || step<=0)return 0;
   return NormalizeDouble(MathFloor(desired/step+1e-9)*step,8);
}
bool TurboBuyType(const long type) {
   return type==ORDER_TYPE_BUY || type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_BUY_STOP;
}
bool TurboPendingType(const long type) {
   return type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_SELL_LIMIT || type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_SELL_STOP;
}
// Same broker filling adaptation as the Prop Ready guard (IOC-only brokers); RETURN is never sent to Market Execution.
bool TurboMarketFilling(const string symbol,ENUM_ORDER_TYPE_FILLING &filling) {
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
// Account-wide planned stop risk. A position keeps its initial stop risk (per lot, scaled by the remaining volume)
// until it closes, like sim.py; a stop moved beyond entry never releases it. Pending orders reserve their full
// risk until they fill or are removed. 'stress' = the lower of (balance - all planned risk) and
// (equity - pending risk - remaining distance of every position to its stop): a gap beyond a stop shows up.
bool TurboExposure(const string symbol,const double balance,const double equity,double &total,double &same,double &stress) {
   total=0;same=0;double pending=0,to_stop=0;
   for(int i=0;i<OrdersTotal();i++) {
      ulong t=OrderGetTicket(i);if(t==0)return false;
      long type=OrderGetInteger(ORDER_TYPE);
      if(!TurboPendingType(type))return false;
      string s=OrderGetString(ORDER_SYMBOL);
      double unit=0,v=OrderGetDouble(ORDER_VOLUME_CURRENT);
      if(!TurboUnitRisk(s,TurboBuyType(type),OrderGetDouble(ORDER_PRICE_OPEN),OrderGetDouble(ORDER_SL),unit))return false;
      total+=unit*v;pending+=unit*v;if(s==symbol)same+=unit*v;
   }
   for(int i=0;i<PositionsTotal();i++) {
      ulong ticket=PositionGetTicket(i);if(ticket==0)return false;
      string s=PositionGetString(POSITION_SYMBOL);
      long id=PositionGetInteger(POSITION_IDENTIFIER);
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double sl=PositionGetDouble(POSITION_SL),v=PositionGetDouble(POSITION_VOLUME),open=PositionGetDouble(POSITION_PRICE_OPEN);
      if(sl<=0 || v<=0)return false;
      string key=TurboKey("R_"+IntegerToString(id));
      double unit=GlobalVariableCheck(key)?GlobalVariableGet(key):0;
      if(unit<=0) {
         double osl=HistoryOrderSelect((ulong)id)?HistoryOrderGetDouble((ulong)id,ORDER_SL):0;
         if(!TurboUnitRisk(s,buy,open,osl>0?osl:sl,unit))return false;
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
   // An entry filled in the last 10 s that is not visible yet (cross-chart race) still counts.
   string lid=TurboKey("LAST_ID");
   if(GlobalVariableCheck(lid) && TimeLocal()-GlobalVariableGet(TurboKey("LAST_T"))<10) {
      ulong id=(ulong)GlobalVariableGet(lid);bool seen=false;
      for(int i=0;i<PositionsTotal() && !seen;i++)if(PositionGetTicket(i)>0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER)==id)seen=true;
      for(int i=0;i<OrdersTotal() && !seen;i++)if(OrderGetTicket(i)==id)seen=true;
      if(!seen && !TurboTester()){double r=GlobalVariableGet(TurboKey("LAST_R"));total+=r;pending+=r;}
   }
   stress=MathMin(balance-total,equity-pending-to_stop);
   return MathIsValidNumber(total) && MathIsValidNumber(stress);
}
bool TurboReject(MqlTradeResult &result,const string why) {
   ZeroMemory(result);result.retcode=TRADE_RETCODE_REJECT;result.comment="Turbo guard: "+why;
   TurboNote(why);return false;
}
string TurboStateText(const TurboState &s,const double total,const double same,const double stress) {
   return StringFormat("bal=%.2f eq=%.2f open=%.2f sym=%.2f stress=%.2f anchor=%.2f peak=%.2f floor=%.2f dayreal=%.2f day=%d",
      s.balance,s.equity,total,same,stress,s.anchor,s.peak,s.floor,s.day_real,s.day);
}
bool TurboAdmit(MqlTradeRequest &r,MqlTradeResult &result,double &admitted) {
   bool market=r.action==TRADE_ACTION_DEAL && r.position==0 && (r.type==ORDER_TYPE_BUY || r.type==ORDER_TYPE_SELL);
   bool pending=r.action==TRADE_ACTION_PENDING && TurboPendingType(r.type);
   if(!market && !pending)return TurboReject(result,"unsupported entry type");
   if(!TurboTester() && (r.symbol!=TurboExpectedSymbol || !TerminalInfoInteger(TERMINAL_CONNECTED)))return TurboReject(result,"symbol/connection mismatch");
   MqlTick tick={};
   if(!SymbolInfoTick(r.symbol,tick) || tick.bid<=0 || tick.ask<=0 || (!TurboTester() && TimeTradeServer()-tick.time>30))return TurboReject(result,"stale quote");
   bool buy=TurboBuyType(r.type);
   double price=market?(buy?tick.ask:tick.bid):r.price,unit=0;
   if(!TurboUnitRisk(r.symbol,buy,price,r.sl,unit))return TurboReject(result,"missing/invalid SL");
   int offset=0;datetime utc=0;TurboState s={};
   if(!TurboClock(offset,utc) || !TurboLedger(s,offset,utc))return TurboReject(result,"clock/history/capital baseline unavailable");
   if(GlobalVariableCheck(TurboKey("BREACHED")) || GlobalVariableCheck(TurboKey("UNCERTAIN")))return TurboReject(result,"latched stop: review required");
   double size=TurboSize(),total=0,same=0,stress=0;
   if(!TurboExposure(r.symbol,s.balance,s.equity,total,same,stress))return TurboReject(result,"unprotected/unknown exposure");
   string state=TurboStateText(s,total,same,stress);
   if(s.day_real>=TURBO_DCAP*size-1e-9){TurboReject(result,"daily profit cap");Print("TURBO_REJECT reason=profitcap ",state);return false;}
   double room=stress-s.floor,risk=TURBO_TRADE*size;
   if(TURBO_TAPER*room<risk)risk=TURBO_TAPER*room;
   double fit_open=TURBO_OPEN*size-total,fit_sym=TURBO_SYMBOL*size-same,fit_day=TURBO_DSTOP*size-(s.anchor-stress),fit_room=room-TURBO_BUFFER*size;
   double fit=MathMin(MathMin(fit_open,fit_sym),MathMin(fit_day,fit_room));
   if(fit<risk)risk=fit;
   string why=risk==fit?(fit==fit_open?"open":fit==fit_sym?"symbol":fit==fit_day?"daily":"buffer"):(risk<TURBO_TRADE*size?"taper":"cap");
   if(risk<TURBO_MINRISK*size){TurboReject(result,"below minimum risk ("+why+")");Print("TURBO_REJECT reason=min_",why," budget=",DoubleToString(risk,2)," ",state);return false;}
   double step=SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_STEP);
   double volume=TurboLotsDown(MathMin(r.volume,MathMin(risk/unit,SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MAX))),step);
   if(volume<SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MIN)-1e-9){TurboReject(result,"minimum lot exceeds budget");Print("TURBO_REJECT reason=minlot budget=",DoubleToString(risk,2)," unit=",DoubleToString(unit,4)," ",state);return false;}
   double margin=0;
   if(!OrderCalcMargin(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,r.symbol,volume,price,margin) || !MathIsValidNumber(margin) || margin<0 ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.9){TurboReject(result,"margin");Print("TURBO_REJECT reason=margin ",state);return false;}
   if(!TurboTester()) {
      string last=TurboKey("ENTRY_WAIT");
      if(GlobalVariableCheck(last) && TimeLocal()<GlobalVariableGet(last))return TurboReject(result,"entry reconciliation wait");
      GlobalVariableSet(last,(double)(TimeLocal()+1));
   }
   admitted=unit*volume;
   PrintFormat("TURBO_ADMIT sym=%s type=%d price=%.5f sl=%.5f unit=%.6f step=%.4f req=%.4f vol=%.4f risk=%.2f budget=%.2f bind=%s room=%.2f %s",
      r.symbol,(int)r.type,price,r.sl,unit,step,r.volume,volume,admitted,risk,why,room,state);
   r.volume=volume;if(market)r.price=price;
   return true;
}
bool TurboOrderSend(const MqlTradeRequest &request,MqlTradeResult &result) {
   if(TurboTester() && TurboGuardMode==0) {
      // Research pass-through: identical request, plus the unit risk of each new entry for the parity audit.
      bool sent=OrderSend(request,result);
      if(sent && request.position==0 && (request.action==TRADE_ACTION_DEAL || request.action==TRADE_ACTION_PENDING) &&
         (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL || result.retcode==TRADE_RETCODE_PLACED)) {
         double unit=0,price=request.action==TRADE_ACTION_DEAL?(result.price>0?result.price:request.price):request.price;
         TurboUnitRisk(request.symbol,TurboBuyType(request.type),price,request.sl,unit);
         PrintFormat("TURBO_SEEN order=%I64u deal=%I64u sym=%s type=%d price=%.5f sl=%.5f vol=%.4f unit=%.6f",
            result.order,result.deal,request.symbol,(int)request.type,price,request.sl,result.volume>0?result.volume:request.volume,unit);
      }
      return sent;
   }
   if(!TurboAccountOK())return TurboReject(result,"account/server/currency/symbol lock");
   MqlTradeRequest r=request;
   bool closing=(r.action==TRADE_ACTION_DEAL && r.position>0) || r.action==TRADE_ACTION_CLOSE_BY;
   bool protection=r.action==TRADE_ACTION_SLTP;
   bool modify=r.action==TRADE_ACTION_MODIFY;
   bool removing=r.action==TRADE_ACTION_REMOVE;
   bool entry=!closing && !protection && !modify && !removing;
   if(r.action==TRADE_ACTION_DEAL && !TurboMarketFilling(r.symbol,r.type_filling))return TurboReject(result,"unsupported broker filling policy");
   int lock=FileOpen(TurboIdentity()+".lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(lock==INVALID_HANDLE)return TurboReject(result,"portfolio busy");
   int offset=0;datetime utc=0;
   if(!TurboClock(offset,utc) && entry){FileClose(lock);return TurboReject(result,"clock unavailable");}
   string counter=TurboKey("REQ_"+IntegerToString(TurboDay(utc)));
   double requests=GlobalVariableCheck(counter)?GlobalVariableGet(counter):0;
   if(requests>=1900 || (entry && requests>=1400)){FileClose(lock);return TurboReject(result,"daily request budget");}
   if(protection) {
      if(!PositionSelectByTicket(r.position) || r.sl<=0){FileClose(lock);return TurboReject(result,"cannot remove SL");}
      double old=PositionGetDouble(POSITION_SL);
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      if(old>0 && ((buy && r.sl<old-1e-10) || (!buy && r.sl>old+1e-10))){FileClose(lock);return TurboReject(result,"cannot widen SL");}
   }
   if(modify) {
      // A pending order may move, but its planned stop risk may not grow and its SL may not be removed.
      if(!OrderSelect(r.order) || r.sl<=0){FileClose(lock);return TurboReject(result,"cannot remove pending SL");}
      long type=OrderGetInteger(ORDER_TYPE);string s=OrderGetString(ORDER_SYMBOL);
      double v=OrderGetDouble(ORDER_VOLUME_CURRENT),before=0,after=0;
      if(!TurboUnitRisk(s,TurboBuyType(type),OrderGetDouble(ORDER_PRICE_OPEN),OrderGetDouble(ORDER_SL),before) ||
         !TurboUnitRisk(s,TurboBuyType(type),r.price,r.sl,after) || after*v>before*v+0.01){FileClose(lock);return TurboReject(result,"pending modify raises risk");}
   }
   double admitted=0;
   if(entry && !TurboAdmit(r,result,admitted)){FileClose(lock);return false;}
   GlobalVariableSet(counter,requests+1);
   bool sent=OrderSend(r,result);
   bool done=sent && (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL || (r.action==TRADE_ACTION_PENDING && result.retcode==TRADE_RETCODE_PLACED));
   if(entry && done) {
      ulong id=result.order;
      if(result.deal>0 && HistoryDealSelect(result.deal))id=(ulong)HistoryDealGetInteger(result.deal,DEAL_POSITION_ID);
      double unit=0,fill=r.action==TRADE_ACTION_DEAL?(result.price>0?result.price:r.price):r.price;
      if(id>0 && TurboUnitRisk(r.symbol,TurboBuyType(r.type),fill,r.sl,unit)) {
         GlobalVariableSet(TurboKey("R_"+IntegerToString((long)id)),unit);
         GlobalVariableSet(TurboKey("LAST_ID"),(double)id);GlobalVariableSet(TurboKey("LAST_R"),unit*r.volume);
         GlobalVariableSet(TurboKey("LAST_T"),(double)TimeLocal());
      }
      PrintFormat("TURBO_FILL id=%I64u sym=%s type=%d price=%.5f sl=%.5f vol=%.4f unit=%.6f risk=%.2f",id,r.symbol,(int)r.type,fill,r.sl,r.volume,unit,unit*r.volume);
   }
   if(entry && !done && (result.retcode==TRADE_RETCODE_TIMEOUT || result.retcode==TRADE_RETCODE_CONNECTION ||
      (sent && r.action==TRADE_ACTION_DEAL && result.retcode==TRADE_RETCODE_PLACED))) {
      GlobalVariableSet(TurboKey("UNCERTAIN"),1);
      Print("Turbo guard: uncertain execution; NEW entries latched off. Reconcile orders/history, then clear the latch.");
   }
   FileClose(lock);return sent;
}

// Monitoring: latches a firm-limit breach (equity) and journals each firm day. Never suppresses strategy management.
int    turbo_day=0,turbo_day_index=-1,turbo_cycle_start=-1,turbo_prof_days=0;
double turbo_balance=-1,turbo_floor=0,turbo_anchor=0,turbo_max_day=0,turbo_min_eq_room=1e18,turbo_min_day_room=1e18;
void TurboTesterReward(const TurboState &s,const int index,const int offset,const int prev_day) {
   double size=TurboSize(),prev=TurboDayTradeNet(prev_day,offset);
   if(prev>=0.005*size)turbo_prof_days++;
   if(prev>turbo_max_day)turbo_max_day=prev;
   if(turbo_cycle_start<0){turbo_cycle_start=index;return;}
   if(index-turbo_cycle_start<14)return;
   double prof=s.balance-size;
   if(prof>0 && turbo_prof_days>=3 && turbo_max_day<=0.2*prof) {
      bool ok=TesterWithdrawal(prof);
      PrintFormat("TURBO_PAY day=%d ok=%d amount=%.2f prof_days=%d max_day=%.2f",s.day,ok,prof,turbo_prof_days,turbo_max_day);
      if(ok){turbo_cycle_start=index;turbo_prof_days=0;turbo_max_day=0;}
   }
}
bool TurboPulse() {
   if(TurboTester() && TurboGuardMode==0)return true;
   if(!TurboAccountOK())return false;
   int offset=0;datetime utc=0;
   if(!TurboClock(offset,utc))return true;
   int day=TurboDay(utc);
   double balance=AccountInfoDouble(ACCOUNT_BALANCE),equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(day!=turbo_day || balance!=turbo_balance) {
      TurboState s={};
      if(!TurboLedger(s,offset,utc))return true;
      if(day!=turbo_day) {
         int index=TurboDayIndex(utc),prev=turbo_day;
         if(turbo_day!=0)PrintFormat("TURBO_DAYEND day=%d min_eq_room=%.2f min_daily_room=%.2f",turbo_day,turbo_min_eq_room,turbo_min_day_room);
         turbo_min_eq_room=1e18;turbo_min_day_room=1e18;
         if(TurboTester() && TurboTesterRewards && prev!=0) {
            TurboTesterReward(s,index,offset,prev);
            if(!TurboLedger(s,offset,utc))return true;
         } else if(TurboTester() && TurboTesterRewards)turbo_cycle_start=index;
         turbo_day=day;turbo_day_index=index;
         PrintFormat("TURBO_DAY day=%d index=%d bal=%.2f anchor=%.2f peak=%.2f floor=%.2f eq=%.2f",day,index,s.balance,s.anchor,s.peak,s.floor,s.equity);
      }
      turbo_balance=s.balance;turbo_floor=s.floor;turbo_anchor=s.anchor;
   }
   double size=TurboSize();
   if(TurboTrailEquity) {
      string k=TurboKey("EQPEAK");
      if(GlobalVariableCheck(k) && equity>GlobalVariableGet(k))GlobalVariableSet(k,equity);
   }
   turbo_min_eq_room=MathMin(turbo_min_eq_room,equity-turbo_floor);
   turbo_min_day_room=MathMin(turbo_min_day_room,equity-turbo_anchor*(1-TURBO_DAILY));
   if((equity<=turbo_floor || equity<=turbo_anchor*(1-TURBO_DAILY)) && !GlobalVariableCheck(TurboKey("BREACHED"))) {
      GlobalVariableSet(TurboKey("BREACHED"),1);
      PrintFormat("TURBO_BREACH day=%d eq=%.2f floor=%.2f daily=%.2f (new entries latched off)",day,equity,turbo_floor,turbo_anchor*(1-TURBO_DAILY));
   }
   return true;
}
int TurboInit() {
   if(!TurboAccountOK()){Print("Turbo guard initialization blocked: account/server/currency/symbol/baseline lock, netting account or invalid mode.");return INIT_FAILED;}
   if(TurboTester() && TurboGuardMode==0){Print("Turbo guard PASS-THROUGH (tester research only).");return INIT_SUCCEEDED;}
   PrintFormat("Turbo guard armed: size %.0f; trade risk <= %.2f and <= 5%% of trailing room; open <= %.2f; symbol <= %.2f; daily soft stop %.2f; profit cap %.2f; buffer %.2f. Gaps/broker failures remain possible.",
      TurboSize(),TURBO_TRADE*TurboSize(),TURBO_OPEN*TurboSize(),TURBO_SYMBOL*TurboSize(),TURBO_DSTOP*TurboSize(),TURBO_DCAP*TurboSize(),TURBO_BUFFER*TurboSize());
   return INIT_SUCCEEDED;
}
#endif
