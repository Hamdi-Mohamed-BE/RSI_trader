#ifndef CALYX_FTMO_GUARD
#define CALYX_FTMO_GUARD
// Isolated FTMO builds only. Admission guard, NOT a guaranteed loss limiter.
// No credentials, no account switching, no liquidation, no asynchronous orders.
input long   FTMOExpectedLogin=0;
input string FTMOExpectedServer="";
input string FTMOExpectedSymbol="";
input int    FTMOPhase=1; // 1 Challenge, 2 Verification, 3 Funded
const double FTMO_RISK=50.0, FTMO_TOTAL_RISK=225.0, FTMO_SYMBOL_RISK=150.0;
const double FTMO_DAILY_RESERVE=300.0, FTMO_EQUITY_BUFFER=9200.0;
datetime ftmo_last_log=0;
string FTMOKey(const string suffix) {
   return "CF13_"+IntegerToString(FTMOExpectedLogin)+"_"+suffix;
}
void FTMONote(const string why) {
   if(TimeLocal()-ftmo_last_log>=60) {
      Print("FTMO13: ",why); ftmo_last_log=TimeLocal();
   }
}
bool FTMOAccountOK() {
   string firm=AccountInfoString(ACCOUNT_COMPANY);
   StringToUpper(firm);
   return !MQLInfoInteger(MQL_TESTER) && FTMOExpectedLogin>0 &&
      AccountInfoInteger(ACCOUNT_LOGIN)==FTMOExpectedLogin &&
      AccountInfoString(ACCOUNT_SERVER)==FTMOExpectedServer &&
      AccountInfoString(ACCOUNT_CURRENCY)=="USD" &&
      StringFind(firm,"FTMO")>=0 &&
      AccountInfoInteger(ACCOUNT_MARGIN_MODE)==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING &&
      _Symbol==FTMOExpectedSymbol && FTMOPhase>=1 && FTMOPhase<=3;
}
datetime FTMOLastSunday(const int year,const int month) {
   MqlDateTime t={}; t.year=year;t.mon=month;t.day=31;t.hour=1;
   datetime d=StructToTime(t);TimeToStruct(d,t);return d-t.day_of_week*86400;
}
int FTMOPragueOffset(const datetime utc) {
   MqlDateTime t={};TimeToStruct(utc,t);
   return utc>=FTMOLastSunday(t.year,3) && utc<FTMOLastSunday(t.year,10) ? 7200:3600;
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
   for(int i=0;i<ArraySize(values);i++) if(values[i]==value)return true;
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
   int today=FTMODay(utc);
   long opened[],closed[],trading_days[];
   double delta=0;
   bool funding_seen=false;
   for(int i=0;i<HistoryDealsTotal();i++) {
      ulong d=HistoryDealGetTicket(i);if(d==0)return false;
      int type=(int)HistoryDealGetInteger(d,DEAL_TYPE);
      datetime when=(datetime)HistoryDealGetInteger(d,DEAL_TIME)-offset;
      bool is_today=FTMODay(when)==today;
      if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL) {
         // Verify the initial reference capital from history. Never subtract funding
         // from the first day's anchor; subsequent cash flows require review.
         if(type==DEAL_TYPE_BALANCE && !funding_seen) {
            funding_seen=true;
            if(MathAbs(FTMODealNet(d)-10000.0)>.01)return false;
            continue;
         }
         if(is_today && MathAbs(FTMODealNet(d))>0.001)return false;
         continue;
      }
      if(is_today)delta+=FTMODealNet(d);
      long id=HistoryDealGetInteger(d,DEAL_POSITION_ID);
      int entry=(int)HistoryDealGetInteger(d,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT) {
         FTMOAppend(trading_days,(long)FTMODay(when));
         if(is_today)FTMOAppend(opened,id);
      }
      if(is_today && (entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY || entry==DEAL_ENTRY_INOUT))
         FTMOAppend(closed,id);
   }
   anchor=AccountInfoDouble(ACCOUNT_BALANCE)-delta;
   ftmo_entries=ArraySize(opened);ftmo_days=ArraySize(trading_days);losses=0;
   for(int j=0;j<ArraySize(closed);j++) {
      if(FTMOLiveID(closed[j]))continue;
      double net=0;
      for(int i=0;i<HistoryDealsTotal();i++) {
         ulong d=HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(d,DEAL_POSITION_ID)==closed[j])net+=FTMODealNet(d);
      }
      if(net<-.005)losses++;
   }
   return anchor>0 && funding_seen;
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
// Initial open risk never released by a profitable trailing stop. Missing persistent
// state is reconstructed from the original filled order, never treated as zero.
bool FTMOExposure(const string symbol,double &total,double &same,double &reserve) {
   total=0;same=0;reserve=0;
   if(OrdersTotal()>0)return false; // This 13-EA profile has market entries only.
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
         double original_sl=HistoryOrderGetDouble((ulong)id,ORDER_SL);
         double unit=0;
         ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)PositionGetInteger(POSITION_TYPE);
         if(!FTMOUnitRisk(s,type,PositionGetDouble(POSITION_PRICE_OPEN),original_sl,unit))return false;
         risk=unit*volume;GlobalVariableSet(key,risk);
      }
      if(sl<=0 || volume<=0)return false;
      double at_stop=0;
      if(!OrderCalcProfit((ENUM_ORDER_TYPE)PositionGetInteger(POSITION_TYPE),s,volume,
                        PositionGetDouble(POSITION_PRICE_OPEN),sl,at_stop))return false;
      // Include any widened stop. Do not assume unrealised profits can finance fresh trades.
      double loss=MathMax(risk,MathMax(0,-at_stop));
      total+=loss;if(s==symbol)same+=loss;
      reserve+=loss*1.25+MathMax(0,-PositionGetDouble(POSITION_SWAP))+5.0;
   }
   return true;
}
bool FTMOReject(MqlTradeResult &result,const string why) {
   ZeroMemory(result);result.retcode=TRADE_RETCODE_REJECT;result.comment="FTMO13: "+why;
   FTMONote(why);return false;
}
bool FTMOAdmit(MqlTradeRequest &r,MqlTradeResult &result) {
   if(r.action!=TRADE_ACTION_DEAL || r.position!=0 ||
      (r.type!=ORDER_TYPE_BUY && r.type!=ORDER_TYPE_SELL))
      return FTMOReject(result,"unsupported entry type");
   if(r.symbol!=FTMOExpectedSymbol || !TerminalInfoInteger(TERMINAL_CONNECTED))
      return FTMOReject(result,"symbol/connection mismatch");
   MqlTick tick={};
   if(!SymbolInfoTick(r.symbol,tick) || tick.bid<=0 || tick.ask<=0 ||
      TimeTradeServer()-tick.time>30)return FTMOReject(result,"stale quote");
   double price=r.type==ORDER_TYPE_BUY?tick.ask:tick.bid;
   double unit=0;
   if(!FTMOUnitRisk(r.symbol,r.type,price,r.sl,unit))return FTMOReject(result,"missing/invalid SL");
   double step=SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_STEP);
   double volume=FTMOLotsDown(MathMin(r.volume,MathMin(FTMO_RISK/unit,
                  SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MAX))),step);
   if(volume<SymbolInfoDouble(r.symbol,SYMBOL_VOLUME_MIN)-1e-9)
      return FTMOReject(result,"minimum lot exceeds budget");
   double risk=unit*volume;
   if(risk>FTMO_RISK+1e-7)return FTMOReject(result,"risk rounding");
   int offset=0,ftmo_entries=0,losses=0,ftmo_days=0;datetime utc=0;double anchor=0;
   if(!FTMOClock(offset,utc) || !FTMOLedger(anchor,ftmo_entries,losses,ftmo_days,offset,utc))
      return FTMOReject(result,"clock/history unavailable");
   int day=FTMODay(utc);
   string breach=FTMOKey("BREACHED"),daystop=FTMOKey("STOP_"+IntegerToString(day));
   double equity=AccountInfoDouble(ACCOUNT_EQUITY),balance=AccountInfoDouble(ACCOUNT_BALANCE);
   if(equity<=9000)GlobalVariableSet(breach,1);
   if(equity<=anchor-500)GlobalVariableSet(breach,1);
   if(equity<=anchor-300)GlobalVariableSet(daystop,1);
   if(GlobalVariableCheck(breach) || GlobalVariableCheck(daystop) || GlobalVariableCheck(FTMOKey("UNCERTAIN")))
      return FTMOReject(result,"latched loss stop: review required");
   if(ftmo_entries>=7 || losses>=3)return FTMOReject(result,"daily entries/losses cap");
   double target=FTMOPhase==1?11000:10500;
   if(FTMOPhase<3 && ftmo_days>=4 && balance>=target)
      return FTMOReject(result,"phase target reached; await review/new account");
   double total=0,same=0,reserve=0;
   if(!FTMOExposure(r.symbol,total,same,reserve))
      return FTMOReject(result,"unprotected/unknown exposure or pending order");
   if(total+risk>FTMO_TOTAL_RISK+1e-7 || same+risk>FTMO_SYMBOL_RISK+1e-7)
      return FTMOReject(result,"aggregate/symbol risk cap");
   double projected=MathMin(equity,balance-reserve)-risk*1.25-5.0;
   if(projected<FTMO_EQUITY_BUFFER || anchor-projected>FTMO_DAILY_RESERVE)
      return FTMOReject(result,"floating/reserved loss budget");
   double margin=0;
   if(!OrderCalcMargin(r.type,r.symbol,volume,price,margin) || margin<0 ||
      AccountInfoDouble(ACCOUNT_MARGIN)+margin>projected*.8 ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return FTMOReject(result,"shared margin cap");
   string last=FTMOKey("ENTRY_WAIT");
   if(GlobalVariableCheck(last) && TimeLocal()<GlobalVariableGet(last))
      return FTMOReject(result,"entry reconciliation wait");
   // Requote/reject churn limited account-wide; no repeated retry in this handler.
   GlobalVariableSet(last,(double)(TimeLocal()+3));
   r.volume=volume;r.price=price;
   return true;
}
bool FTMOOrderSend(const MqlTradeRequest &request,MqlTradeResult &result) {
   if(!FTMOAccountOK())return FTMOReject(result,"account/server/symbol lock");
   MqlTradeRequest r=request;
   bool closing=(r.action==TRADE_ACTION_DEAL && r.position>0);
   bool protection=r.action==TRADE_ACTION_SLTP;
   bool removing=r.action==TRADE_ACTION_REMOVE;
   bool entry=!closing && !protection && !removing;
   // Exclusive COMMON file prevents entry races across all 13 charts and local terminals.
   int lock=FileOpen("CalyxFTMO13_"+IntegerToString(FTMOExpectedLogin)+".lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(lock==INVALID_HANDLE)return FTMOReject(result,"portfolio busy");
   int offset=0;datetime utc=0;
   if(!FTMOClock(offset,utc) && entry) {FileClose(lock);return FTMOReject(result,"clock unavailable");}
   string counter=FTMOKey("REQ_"+IntegerToString(FTMODay(utc)));
   double requests=GlobalVariableCheck(counter)?GlobalVariableGet(counter):0;
   string retry=FTMOKey("WAIT_"+IntegerToString((long)(r.position>0?r.position:r.order)));
   if(!entry && GlobalVariableCheck(retry) && TimeLocal()<GlobalVariableGet(retry)) {
      FileClose(lock);return FTMOReject(result,"management retry cooldown");
   }
   if(requests>=1900 || (entry && requests>=1400) || (protection && requests>=1700)) {
      FileClose(lock);return FTMOReject(result,"daily request budget");
   }
   // SL changes must never remove/widen protection. Profit-taking and exits remain available.
   if(protection) {
      if(!PositionSelectByTicket(r.position) || r.sl<=0) {
         FileClose(lock);return FTMOReject(result,"cannot remove SL");
      }
      double old=PositionGetDouble(POSITION_SL);
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      if(old>0 && ((buy && r.sl<old) || (!buy && r.sl>old))) {
         FileClose(lock);return FTMOReject(result,"cannot widen SL");
      }
   }
   if(entry && !FTMOAdmit(r,result)) {FileClose(lock);return false;}
   GlobalVariableSet(counter,requests+1);
   bool sent=OrderSend(r,result);
   bool filled=sent && (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL);
   if(entry && filled) {
      long id=(long)result.order;
      if(result.deal>0 && HistoryDealSelect(result.deal))id=HistoryDealGetInteger(result.deal,DEAL_POSITION_ID);
      double unit=0;
      if(id>0 && FTMOUnitRisk(r.symbol,r.type,result.price>0?result.price:r.price,r.sl,unit))
         GlobalVariableSet(FTMOKey("R_"+IntegerToString(id)),unit*result.volume);
      PrintFormat("FTMO13 fill: %s %.3f lots, requested stop risk <= $50. Gaps may exceed budget.",r.symbol,r.volume);
   }
   if(!entry)GlobalVariableSet(retry,(double)(TimeLocal()+(filled?2:
      result.retcode==TRADE_RETCODE_MARKET_CLOSED?900:60)));
   if(entry && !filled) {
      GlobalVariableSet(FTMOKey("ENTRY_WAIT"),(double)(TimeLocal()+60));
      if(result.retcode==TRADE_RETCODE_TIMEOUT || result.retcode==TRADE_RETCODE_CONNECTION ||
         (sent && result.retcode==TRADE_RETCODE_PLACED)) {
         GlobalVariableSet(FTMOKey("UNCERTAIN"),1);
         Print("FTMO13: uncertain execution; NEW entries latched off. Reconcile orders/history before review.");
      }
   }
   FileClose(lock);
   return sent;
}
int FTMOInit() {
   if(!FTMOAccountOK()) {Print("FTMO13 initialization blocked: account/server/symbol lock or tester.");return INIT_FAILED;}
   Print("FTMO13 armed: $50 maximum planned stop risk, news OFF; gaps and broker failures remain possible.");
   return INIT_SUCCEEDED;
}
// Observe equity even when an EA has no new signal. Gates never suppress existing
// position management; the strategy still gets its tick after this observation.
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
   if(!GlobalVariableCheck(anchorKey) || !GlobalVariableCheck(FTMOKey("BALANCE")) ||
      GlobalVariableGet(FTMOKey("BALANCE"))!=balance) {
      double anchor=0;int count=0,loss=0,daycount=0;
      if(!FTMOLedger(anchor,count,loss,daycount,offset,utc))return true;
      GlobalVariableSet(anchorKey,anchor);
      GlobalVariableSet(FTMOKey("BALANCE"),balance);
   }
   double anchor=GlobalVariableGet(anchorKey),equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=9000 || equity<=anchor-500)GlobalVariableSet(FTMOKey("BREACHED"),1);
   if(equity<=anchor-300)GlobalVariableSet(FTMOKey("STOP_"+IntegerToString(day)),1);
   return true;
}
#endif
