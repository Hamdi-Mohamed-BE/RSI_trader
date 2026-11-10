#ifndef CALYX_PROP_READY_GUARD
#define CALYX_PROP_READY_GUARD
// ftmo 1_step 2026-11-04: derived from the broker-neutral Prop Ready guard for the FTMO 1-Step rules: 10% max loss trailing
// the highest end-of-day balance, 3% max daily loss from the midnight balance, best day <= 50% of total profit.
// Broker-neutral FTMO 1-Step builds. Admission guard, NOT a guaranteed loss limiter.
// Legacy FTMO input/function names preserve the strategy wrapper interface only.
// Fixed allocation is in ACCOUNT CURRENCY, not necessarily USD. No account switching,
// liquidation, asynchronous execution or permission to use netting accounts.
input int FTMOAllocationMode=0; // 0=fixed account-currency amount, 1=current equity %
input double FTMOAllocationValue=50.0;
input double FTMORiskCapPercent=0.5; // per-entry cap, % of the saved reference balance; the installer sets it to the chosen risk (2026-10-30). Totals: the two multiples below
input double FTMOTotalRiskMultiple=4.5; // total open stop risk = this x the per-entry cap; 0 = no total cap (installer: 4.5 / 6 / 8 / none, 2026-11-03)
input double FTMOSymbolRiskMultiple=3.0; // same-symbol open stop risk = this x the per-entry cap; 0 = no per-symbol cap (installer: 3 / none)
input long   FTMOExpectedLogin=0;
input string FTMOExpectedServer="";
input string FTMOExpectedSymbol="";
input string FTMOExpectedCurrency="";
input double FTMOReferenceBalance=0.0; // Flat-account baseline frozen by installer
input long FTMOStartUtcTime=0; // UTC Unix seconds; frozen, never reset on reinstall
input int    FTMOPhase=1; // 1=FTMO 1-Step challenge (target + best-day rule), 3=funded / continuous (no target stop)
input double FTMO1TargetPercent=10.0;      // 1-Step profit target, % of the initial capital
input double FTMO1MaxLossPercent=10.0;     // firm max loss, % of the initial capital below the highest end-of-day balance
input double FTMO1DailyLossPercent=3.0;    // firm max daily loss, % of the initial capital from the midnight balance
input double FTMO1FloorBufferPercent=2.0;  // guard: new entries need projected equity >= trailing floor + this
input double FTMO1DailyReservePercent=2.5; // guard: projected daily loss <= this; the day latches here
input double FTMO1BestDayCapPercent=4.5;   // guard: no new entries today once today P&L >= this (0 = off)

double FTMORiskCap(){return FTMOReferenceBalance*FTMORiskCapPercent/100.0;}
double FTMOTotalRiskCap(){return FTMOTotalRiskMultiple<=0?DBL_MAX:FTMOReferenceBalance*FTMORiskCapPercent*(FTMOTotalRiskMultiple/100.0);}
double FTMOSymbolRiskCap(){return FTMOSymbolRiskMultiple<=0?DBL_MAX:FTMOReferenceBalance*FTMORiskCapPercent*(FTMOSymbolRiskMultiple/100.0);}
double FTMODailyReserve(){return FTMOReferenceBalance*FTMO1DailyReservePercent/100.0;}
// Highest Prague-midnight balance since this install (FTMOLedger stores it); never below the initial capital.
double FTMO1HighWater(){string k=FTMOKey("HWM_"+IntegerToString(FTMOStartUtcTime));
   return MathMax(FTMOReferenceBalance,GlobalVariableCheck(k)?GlobalVariableGet(k):0.0);}
double FTMOHardFloor(){return FTMO1HighWater()-FTMOReferenceBalance*FTMO1MaxLossPercent/100.0;}
double FTMOEquityBuffer(){return FTMOHardFloor()+FTMOReferenceBalance*FTMO1FloorBufferPercent/100.0;}
double FTMODailyHardLoss(){return FTMOReferenceBalance*FTMO1DailyLossPercent/100.0;}
double ftmo1_best_day=0; // best single-day net since the install (FTMOLedger)

bool FTMOCapMultipleValid(const double m){return MathIsValidNumber(m) && (m==0 || (m>=1 && m<=20));}   // 0 = that cap OFF
bool FTMOAllocationValid() {
   return FTMOAllocationMode>=0 && FTMOAllocationMode<=1 && MathIsValidNumber(FTMOAllocationValue)
      && FTMOAllocationValue>0 && (FTMOAllocationMode==0 || FTMOAllocationValue<=10)
      && MathIsValidNumber(FTMORiskCapPercent) && FTMORiskCapPercent>0 && FTMORiskCapPercent<=2.0
      && FTMOCapMultipleValid(FTMOTotalRiskMultiple) && FTMOCapMultipleValid(FTMOSymbolRiskMultiple)
      && FTMO1TargetPercent>0 && FTMO1MaxLossPercent>0 && FTMO1DailyLossPercent>0 && FTMO1FloorBufferPercent>=0
      && FTMO1DailyReservePercent>0 && FTMO1DailyReservePercent<FTMO1DailyLossPercent && FTMO1BestDayCapPercent>=0;   // 3% daily reserve admits at most ~2.4% per entry
}
double FTMOAllocationBudget() {
   if(!FTMOAllocationValid())return 0;
   double requested=FTMOAllocationMode==0?FTMOAllocationValue:AccountInfoDouble(ACCOUNT_EQUITY)*FTMOAllocationValue/100.0;
   return MathIsValidNumber(requested)&&requested>0?MathMin(FTMORiskCap(),requested):0;
}

datetime ftmo_last_log=0;
// Stable account/server identity, deliberately NOT deployment start/reference, so
// rerunning an installer cannot clear latched stops. Two hashes keep keys <=63 chars.
string FTMOIdentity() {
   uint a=2166136261,b=5381;
   for(int i=0;i<StringLen(FTMOExpectedServer);i++) {
      uint c=(uint)StringGetCharacter(FTMOExpectedServer,i);
      a=(a^c)*16777619;
      b=((b<<5)+b)^c;
   }
   return "P4O"+IntegerToString(FTMOExpectedLogin)+"_"+StringFormat("%08X%08X",a,b);
}
string FTMOKey(const string suffix){return FTMOIdentity()+"_"+suffix;}
void FTMONote(const string why) {
   if(TimeLocal()-ftmo_last_log>=60) {
      Print("FTMO 1-Step: ",why);ftmo_last_log=TimeLocal();
   }
}
bool FTMOAccountOK() {
   return !MQLInfoInteger(MQL_TESTER) && FTMOExpectedLogin>0 &&
      StringLen(FTMOExpectedServer)>0 && StringLen(FTMOExpectedCurrency)>0 &&
      MathIsValidNumber(FTMOReferenceBalance) && FTMOReferenceBalance>0 &&
      FTMOStartUtcTime>0 && FTMOStartUtcTime<=TimeGMT()+60 &&
      AccountInfoInteger(ACCOUNT_LOGIN)==FTMOExpectedLogin &&
      AccountInfoString(ACCOUNT_SERVER)==FTMOExpectedServer &&
      AccountInfoString(ACCOUNT_CURRENCY)==FTMOExpectedCurrency &&
      AccountInfoInteger(ACCOUNT_MARGIN_MODE)==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING &&
      _Symbol==FTMOExpectedSymbol && FTMOPhase>=1 && FTMOPhase<=3;
}

datetime FTMOLastSunday(const int year,const int month) {
   MqlDateTime t={};t.year=year;t.mon=month;t.day=31;t.hour=1;
   datetime d=StructToTime(t);TimeToStruct(d,t);return d-t.day_of_week*86400;
}
int FTMOPragueOffset(const datetime utc) {
   MqlDateTime t={};TimeToStruct(utc,t);
   return utc>=FTMOLastSunday(t.year,3) && utc<FTMOLastSunday(t.year,10)?7200:3600;
}
int FTMODay(const datetime utc) {
   MqlDateTime t={};TimeToStruct(utc+FTMOPragueOffset(utc),t);
   return t.year*10000+t.mon*100+t.day;
}
bool FTMOClock(int &offset,datetime &utc) {
   utc=TimeGMT();
   double delta=(double)(TimeTradeServer()-utc);
   offset=(int)MathRound(delta/900.0)*900;
   return utc>0 && MathAbs(delta-offset)<30 && MathAbs(offset)<=14*3600;
}
bool FTMOHas(const long value,const long &values[]) {
   for(int i=0;i<ArraySize(values);i++)if(values[i]==value)return true;
   return false;
}
void FTMOAppend(long &values[],const long value) {
   if(FTMOHas(value,values))return;
   int n=ArraySize(values);ArrayResize(values,n+1);values[n]=value;
}
bool FTMOLiveID(const long id) {
   for(int i=0;i<PositionsTotal();i++)
      if(PositionGetTicket(i)>0 && PositionGetInteger(POSITION_IDENTIFIER)==id)return true;
   return false;
}
double FTMODealNet(const ulong d) {
   return HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_COMMISSION)+
      HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_FEE);
}
bool FTMOLedger(double &anchor,int &ftmo_entries,int &losses,int &ftmo_days,const int offset,const datetime utc) {
   if(!HistorySelect(0,TimeTradeServer()+60))return false;
   int today=FTMODay(utc),start_day=FTMODay(FTMOStartUtcTime);
   if(today<start_day)return false;
   long opened[],closed[],trading_days[];
   double delta=0,cum=0,day_net=0,best=0,hwm=FTMOReferenceBalance;int cur=-1;
   bool install_day=today==start_day;
   for(int i=0;i<HistoryDealsTotal();i++) {
      ulong d=HistoryDealGetTicket(i);if(d==0)return false;
      int type=(int)HistoryDealGetInteger(d,DEAL_TYPE);
      datetime when=(datetime)HistoryDealGetInteger(d,DEAL_TIME)-offset;
      bool is_today=FTMODay(when)==today;
      bool deployed=when>=FTMOStartUtcTime;
      double net=FTMODealNet(d);
      if(!MathIsValidNumber(net))return false;
      if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL) {
         // Any funding/withdrawal/adjustment after deployment invalidates the
         // frozen capital baseline. Fail closed across ALL dates, not just today.
         if(deployed && MathAbs(net)>0.001)return false;
         if(!install_day && is_today)delta+=net;
         continue;
      }
      if(is_today)delta+=net;
      if(!deployed)continue;
      int dday=FTMODay(when);
      if(dday!=cur){if(cur>=0){hwm=MathMax(hwm,FTMOReferenceBalance+cum);best=MathMax(best,day_net);}cur=dday;day_net=0;}
      cum+=net;day_net+=net;
      long id=HistoryDealGetInteger(d,DEAL_POSITION_ID);
      int entry=(int)HistoryDealGetInteger(d,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT) {
         FTMOAppend(trading_days,(long)FTMODay(when));
         if(is_today)FTMOAppend(opened,id);
      }
      if(is_today && (entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY || entry==DEAL_ENTRY_INOUT))
         FTMOAppend(closed,id);
   }
   // The first day starts at the approved FLAT deployment balance, not at a
   // broker's historic deposit. Later days reconstruct the full day-start cash.
   if(cur>=0){best=MathMax(best,day_net);if(cur<today)hwm=MathMax(hwm,FTMOReferenceBalance+cum);}
   GlobalVariableSet(FTMOKey("HWM_"+IntegerToString(FTMOStartUtcTime)),hwm);ftmo1_best_day=best;
   anchor=install_day?FTMOReferenceBalance:AccountInfoDouble(ACCOUNT_BALANCE)-delta;
   ftmo_entries=ArraySize(opened);ftmo_days=ArraySize(trading_days);losses=0;
   for(int j=0;j<ArraySize(closed);j++) {
      if(FTMOLiveID(closed[j]))continue;
      double net=0;
      for(int i=0;i<HistoryDealsTotal();i++) {
         ulong d=HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(d,DEAL_POSITION_ID)==closed[j])net+=FTMODealNet(d);
      }
      if(!MathIsValidNumber(net))return false;
      if(net<-.005)losses++;
   }
   return MathIsValidNumber(anchor)&&anchor>0;
}
bool FTMOUnitRisk(const string symbol,const ENUM_ORDER_TYPE type,const double price,const double sl,double &risk) {
   if(sl<=0 || price<=0 || (type==ORDER_TYPE_BUY && sl>=price) ||
      (type==ORDER_TYPE_SELL && sl<=price))return false;
   double profit=0;
   if(!OrderCalcProfit(type,symbol,1.0,price,sl,profit) || !MathIsValidNumber(profit) || profit>=0)return false;
   risk=-profit;return risk>0;
}
double FTMOLotsDown(const double desired,const double step) {
   if(desired<=0 || step<=0)return 0;
   return NormalizeDouble(MathFloor(desired/step+1e-9)*step,8);
}
// Compatible execution policy for both CTrade preflight and direct deal requests.
// Preserve a supported caller policy; fall back only when that policy is invalid.
// RETURN is forbidden for Market Execution, including position-closing requests.
bool FTMOMarketFilling(const string symbol,ENUM_ORDER_TYPE_FILLING &filling) {
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
// Initial stop exposure is never released by a profitable trailing stop. Missing
// persistent state is reconstructed from the original filled order, never zero.
bool FTMOExposure(const string symbol,double &total,double &same,double &reserve) {
   total=0;same=0;reserve=0;
   if(OrdersTotal()>0)return false;
   for(int i=0;i<PositionsTotal();i++) {
      ulong ticket=PositionGetTicket(i);if(ticket==0)return false;
      string s=PositionGetString(POSITION_SYMBOL);
      double sl=PositionGetDouble(POSITION_SL),volume=PositionGetDouble(POSITION_VOLUME);
      long id=PositionGetInteger(POSITION_IDENTIFIER);
      string key=FTMOKey("R_"+IntegerToString(id));
      double risk=0;
      if(GlobalVariableCheck(key))risk=GlobalVariableGet(key);
      if(risk<=0) {
         if(!HistoryOrderSelect((ulong)id))return false;
         double original_sl=HistoryOrderGetDouble((ulong)id,ORDER_SL),unit=0;
         ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)PositionGetInteger(POSITION_TYPE);
         if(!FTMOUnitRisk(s,type,PositionGetDouble(POSITION_PRICE_OPEN),original_sl,unit))return false;
         risk=unit*volume;GlobalVariableSet(key,risk);
      }
      if(sl<=0 || volume<=0 || !MathIsValidNumber(risk))return false;
      double at_stop=0;
      if(!OrderCalcProfit((ENUM_ORDER_TYPE)PositionGetInteger(POSITION_TYPE),s,volume,
                        PositionGetDouble(POSITION_PRICE_OPEN),sl,at_stop) || !MathIsValidNumber(at_stop))return false;
      double loss=MathMax(risk,MathMax(0,-at_stop));
      total+=loss;if(s==symbol)same+=loss;
      reserve+=loss*1.25+MathMax(0,-PositionGetDouble(POSITION_SWAP))+FTMOReferenceBalance*0.0005;
   }
   return true;
}
bool FTMOReject(MqlTradeResult &result,const string why) {
   ZeroMemory(result);result.retcode=TRADE_RETCODE_REJECT;result.comment="FTMO 1-Step: "+why;
   FTMONote(why);return false;
}
bool FTMOAdmit(MqlTradeRequest &r,MqlTradeResult &result) {
   if(r.action!=TRADE_ACTION_DEAL || r.position!=0 ||
      (r.type!=ORDER_TYPE_BUY && r.type!=ORDER_TYPE_SELL))return FTMOReject(result,"unsupported entry type");
   if(r.symbol!=FTMOExpectedSymbol || !TerminalInfoInteger(TERMINAL_CONNECTED))return FTMOReject(result,"symbol/connection mismatch");
   MqlTick tick={};
   if(!SymbolInfoTick(r.symbol,tick) || tick.bid<=0 || tick.ask<=0 ||
      TimeTradeServer()-tick.time>30)return FTMOReject(result,"stale quote");
   double price=r.type==ORDER_TYPE_BUY?tick.ask:tick.bid,unit=0;
   if(!FTMOUnitRisk(r.symbol,r.type,price,r.sl,unit))return FTMOReject(result,"missing/invalid SL");
   double step=SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_STEP);
   double volume=FTMOLotsDown(MathMin(r.volume,MathMin(FTMOAllocationBudget()/unit,
                  SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MAX))),step);
   if(volume<SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MIN)-1e-9)return FTMOReject(result,"minimum lot exceeds budget");
   double risk=unit*volume;
   if(risk>FTMORiskCap()+1e-7)return FTMOReject(result,"risk rounding");
   int offset=0,ftmo_entries=0,losses=0,ftmo_days=0;datetime utc=0;double anchor=0;
   if(!FTMOClock(offset,utc) || !FTMOLedger(anchor,ftmo_entries,losses,ftmo_days,offset,utc))return FTMOReject(result,"clock/history/capital baseline unavailable");
   int day=FTMODay(utc);
   string breach=FTMOKey("BREACHED"),daystop=FTMOKey("STOP_"+IntegerToString(day));
   double equity=AccountInfoDouble(ACCOUNT_EQUITY),balance=AccountInfoDouble(ACCOUNT_BALANCE);
   if(!MathIsValidNumber(equity) || !MathIsValidNumber(balance))return FTMOReject(result,"invalid account capital");
   if(equity<=FTMOHardFloor() || equity<=anchor-FTMODailyHardLoss())GlobalVariableSet(breach,1);
   if(equity<=anchor-FTMODailyReserve())GlobalVariableSet(daystop,1);
   if(GlobalVariableCheck(breach) || GlobalVariableCheck(daystop) || GlobalVariableCheck(FTMOKey("UNCERTAIN")))return FTMOReject(result,"latched loss stop: review required");
   if(ftmo_entries>=7 || losses>=3)return FTMOReject(result,"daily entries/losses cap");
   double target=FTMOReferenceBalance*(1.0+FTMO1TargetPercent/100.0);
   if(FTMOPhase==1 && balance>=target && ftmo1_best_day<=0.5*(balance-FTMOReferenceBalance)+0.005)
      return FTMOReject(result,"1-Step target and best-day rule met; await review/new account");
   if(FTMO1BestDayCapPercent>0 && equity-anchor>=FTMOReferenceBalance*FTMO1BestDayCapPercent/100.0)return FTMOReject(result,"best-day cap reached today");
   double total=0,same=0,reserve=0;
   if(!FTMOExposure(r.symbol,total,same,reserve))return FTMOReject(result,"unprotected/unknown exposure or pending order");
   if(total+risk>FTMOTotalRiskCap()+1e-7 || same+risk>FTMOSymbolRiskCap()+1e-7)return FTMOReject(result,"aggregate/symbol risk cap");
   double projected=MathMin(equity,balance-reserve)-risk*1.25-FTMOReferenceBalance*0.0005;
   if(projected<FTMOEquityBuffer() || anchor-projected>FTMODailyReserve())return FTMOReject(result,"floating/reserved loss budget");
   double margin=0;
   if(!OrderCalcMargin(r.type,r.symbol,volume,price,margin) || !MathIsValidNumber(margin) || margin<0 ||
      AccountInfoDouble(ACCOUNT_MARGIN)+margin>projected*.8 || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))return FTMOReject(result,"shared margin cap");
   string last=FTMOKey("ENTRY_WAIT");
   if(GlobalVariableCheck(last) && TimeLocal()<GlobalVariableGet(last))return FTMOReject(result,"entry reconciliation wait");
   GlobalVariableSet(last,(double)(TimeLocal()+3));
   r.volume=volume;r.price=price;return true;
}
bool FTMOOrderSend(const MqlTradeRequest &request,MqlTradeResult &result) {
   if(!FTMOAccountOK())return FTMOReject(result,"account/server/currency/symbol lock");
   MqlTradeRequest r=request;
   bool closing=(r.action==TRADE_ACTION_DEAL && r.position>0);
   bool protection=r.action==TRADE_ACTION_SLTP;
   bool removing=r.action==TRADE_ACTION_REMOVE;
   bool entry=!closing && !protection && !removing;
   if(r.action==TRADE_ACTION_DEAL && !FTMOMarketFilling(r.symbol,r.type_filling))return FTMOReject(result,"unsupported broker filling policy");
   int lock=FileOpen(FTMOIdentity()+".lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(lock==INVALID_HANDLE)return FTMOReject(result,"portfolio busy");
   int offset=0;datetime utc=0;
   if(!FTMOClock(offset,utc) && entry){FileClose(lock);return FTMOReject(result,"clock unavailable");}
   string counter=FTMOKey("REQ_"+IntegerToString(FTMODay(utc)));
   double requests=GlobalVariableCheck(counter)?GlobalVariableGet(counter):0;
   string retry=FTMOKey("W_"+IntegerToString((long)(r.position>0?r.position:r.order)));
   if(!entry && GlobalVariableCheck(retry) && TimeLocal()<GlobalVariableGet(retry)){FileClose(lock);return FTMOReject(result,"management retry cooldown");}
   if(requests>=1900 || (entry && requests>=1400) || (protection && requests>=1700)){FileClose(lock);return FTMOReject(result,"daily request budget");}
   if(protection) {
      if(!PositionSelectByTicket(r.position) || r.sl<=0){FileClose(lock);return FTMOReject(result,"cannot remove SL");}
      double old=PositionGetDouble(POSITION_SL);
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      if(old>0 && ((buy && r.sl<old) || (!buy && r.sl>old))){FileClose(lock);return FTMOReject(result,"cannot widen SL");}
   }
   if(entry && !FTMOAdmit(r,result)){FileClose(lock);return false;}
   GlobalVariableSet(counter,requests+1);
   bool sent=OrderSend(r,result);
   bool filled=sent && (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL);
   if(entry && filled) {
      long id=(long)result.order;
      if(result.deal>0 && HistoryDealSelect(result.deal))id=HistoryDealGetInteger(result.deal,DEAL_POSITION_ID);
      double unit=0;
      if(id>0 && FTMOUnitRisk(r.symbol,r.type,result.price>0?result.price:r.price,r.sl,unit))GlobalVariableSet(FTMOKey("R_"+IntegerToString(id)),unit*result.volume);
      PrintFormat("FTMO 1-Step fill: %s %.3f lots; planned stop-risk cap %.2f %s. Gaps/costs may exceed it.",r.symbol,r.volume,FTMORiskCap(),FTMOExpectedCurrency);
   }
   if(!entry)GlobalVariableSet(retry,(double)(TimeLocal()+(filled?2:result.retcode==TRADE_RETCODE_MARKET_CLOSED?900:60)));
   if(entry && !filled) {
      GlobalVariableSet(FTMOKey("ENTRY_WAIT"),(double)(TimeLocal()+60));
      if(result.retcode==TRADE_RETCODE_TIMEOUT || result.retcode==TRADE_RETCODE_CONNECTION || (sent && result.retcode==TRADE_RETCODE_PLACED)) {
         GlobalVariableSet(FTMOKey("UNCERTAIN"),1);
         Print("FTMO 1-Step: uncertain execution; NEW entries latched off. Reconcile orders/history before review.");
      }
   }
   FileClose(lock);return sent;
}
int FTMOInit() {
   if(!FTMOAllocationValid())return INIT_PARAMETERS_INCORRECT;
   if(!FTMOAccountOK()){Print("FTMO 1-Step initialization blocked: account/server/currency/symbol/baseline lock or tester.");return INIT_FAILED;}
   PrintFormat("FTMO 1-Step armed: stop-risk cap %.2f %s; initial balance %.2f; Prague daily reset; news OFF. Gaps/broker failures remain possible.",FTMORiskCap(),FTMOExpectedCurrency,FTMOReferenceBalance);
   return INIT_SUCCEEDED;
}
// Observation never suppresses strategy management after the account is verified.
bool FTMOPulse() {
   if(!FTMOAccountOK())return false;
   int offset=0;datetime utc=0;
   if(!FTMOClock(offset,utc))return true;
   string poll=FTMOKey("POLL");
   if(GlobalVariableCheck(poll) && TimeLocal()-GlobalVariableGet(poll)<1)return true;
   GlobalVariableSet(poll,(double)TimeLocal());
   int day=FTMODay(utc);
   double balance=AccountInfoDouble(ACCOUNT_BALANCE);
   string anchorKey=FTMOKey("ANCHOR_"+IntegerToString(day));
   if(!GlobalVariableCheck(anchorKey) || !GlobalVariableCheck(FTMOKey("BALANCE")) || GlobalVariableGet(FTMOKey("BALANCE"))!=balance) {
      double anchor=0;int count=0,loss=0,daycount=0;
      if(!FTMOLedger(anchor,count,loss,daycount,offset,utc))return true;
      GlobalVariableSet(anchorKey,anchor);GlobalVariableSet(FTMOKey("BALANCE"),balance);
   }
   double anchor=GlobalVariableGet(anchorKey),equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=FTMOHardFloor() || equity<=anchor-FTMODailyHardLoss())GlobalVariableSet(FTMOKey("BREACHED"),1);
   if(equity<=anchor-FTMODailyReserve())GlobalVariableSet(FTMOKey("STOP_"+IntegerToString(day)),1);
   return true;
}
#endif
