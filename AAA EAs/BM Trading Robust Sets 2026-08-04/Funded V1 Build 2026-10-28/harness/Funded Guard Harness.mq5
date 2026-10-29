#property strict
#property description "Tester-only harness for CalyxFundedGuard.mqh (funded_v1 defaults, $50k): sizing, SL rules, pending reservation, daily-win close-all,"
#property description "next-day reset, +6% floor lock at $50,000, daily-loss close-all, floor-buffer close-all. Equity moves are made with TesterDeposit / TesterWithdrawal."
#include "..\..\_00 Live profiles\Packages\FundedV1\package\CalyxFundedGuard.mqh"

input int HarnessMode=1;   // 1 = main rules; 2 = daily-loss close-all with a real price loss (run with FundedMaxDailyWinPercent=0)

int step=0,passes=0,fails=0,phaseDay=0;ulong pos1=0,pend=0;datetime waitUntil=0;
void Check(const string name,const bool ok,const string detail){
   if(ok)passes++;else fails++;
   PrintFormat("HARNESS %s %s %s",ok?"PASS":"FAIL",name,detail);
}
double Unit(const bool buy,const double price,const double sl){double u=0;FundedUnitRisk(_Symbol,buy,price,sl,u);return u;}
FundedState State(){int off=0;datetime utc=0;FundedState s={};FundedClock(off,utc);FundedLedger(s,off,utc);return s;}
int Today(){int off=0;datetime utc=0;FundedClock(off,utc);return FundedDay(utc);}
double OpenRisk(){
   double r=0;
   for(int i=0;i<PositionsTotal();i++){ulong t=PositionGetTicket(i);if(!t)continue;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;long id=PositionGetInteger(POSITION_IDENTIFIER);
      double osl=HistoryOrderSelect((ulong)id)?HistoryOrderGetDouble((ulong)id,ORDER_SL):PositionGetDouble(POSITION_SL);
      r+=Unit(buy,PositionGetDouble(POSITION_PRICE_OPEN),osl)*PositionGetDouble(POSITION_VOLUME);}
   for(int i=0;i<OrdersTotal();i++){ulong t=OrderGetTicket(i);if(!t)continue;
      r+=Unit(FundedBuyType(OrderGetInteger(ORDER_TYPE)),OrderGetDouble(ORDER_PRICE_OPEN),OrderGetDouble(ORDER_SL))*OrderGetDouble(ORDER_VOLUME_CURRENT);}
   return r;
}
double Expected(const double open){                         // funded_v1 defaults on $50k, written independently of the guard code
   FundedState s=State();double stress=s.balance-open,room=stress-s.floor;
   return MathMin(MathMin(MathMin(250.0,0.05*room),MathMin(1000-open,750-open)),MathMin(1000-(s.day_ref-stress),room-125));
}
bool Send(MqlTradeRequest &r,MqlTradeResult &res){ZeroMemory(res);r.symbol=_Symbol;r.deviation=1000;r.magic=777;return FundedOrderSend(r,res);}
bool Buy(MqlTradeResult &res,const double lots,const double stopDist){MqlTick q;SymbolInfoTick(_Symbol,q);MqlTradeRequest r={};r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_BUY;r.volume=lots;r.sl=q.ask-stopDist;r.type_filling=ORDER_FILLING_IOC;return Send(r,res);}
bool Flat(){return PositionsTotal()==0 && OrdersTotal()==0;}
int lossDays=0;
void LossMode(){                                        // mode 2: an outside 2-lot position (bypassing the guard, as a manual trade would) until -2% closes all
   if(step>3)return;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   if(step==0){if(PositionsTotal()==0){MqlTradeRequest r={};MqlTradeResult res={};r.action=TRADE_ACTION_DEAL;r.symbol=_Symbol;r.volume=2.0;r.deviation=1000;r.type_filling=ORDER_FILLING_IOC;
         bool buy=lossDays%2==0;r.type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;r.price=buy?q.ask:q.bid;r.sl=buy?q.ask-30:q.bid+30;if(!OrderSend(r,res)){Check("outside_position",false,res.comment);step=9;return;}
         phaseDay=Today();}step=1;return;}
   if(step==1){if(GlobalVariableCheck(FundedKey("LOSS_"+IntegerToString(Today())))){waitUntil=TimeCurrent()+60;step=2;return;}
      if(Today()!=phaseDay){lossDays++;if(lossDays>8){Check("daily_loss_triggered",false,"no -2% day in 8 tries");step=9;return;}
         if(PositionsTotal()>0){ulong t=PositionGetTicket(0);MqlTradeRequest r={};MqlTradeResult res={};r.action=TRADE_ACTION_DEAL;r.position=t;r.symbol=_Symbol;r.volume=PositionGetDouble(POSITION_VOLUME);
            r.type=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?ORDER_TYPE_SELL:ORDER_TYPE_BUY;r.price=r.type==ORDER_TYPE_SELL?q.bid:q.ask;r.deviation=1000;r.type_filling=ORDER_FILLING_IOC;if(!OrderSend(r,res))Print("close failed");}
         step=0;}return;}
   if(step==2){if(TimeCurrent()<waitUntil)return;FundedState s=State();MqlTradeResult res={};
      Check("daily_loss_closes_all",Flat()&&GlobalVariableCheck(FundedKey("LOSS_"+IntegerToString(Today()))),StringFormat("eq=%.2f dayref=%.2f positions=%d",s.equity,s.day_ref,PositionsTotal()));
      bool ok=Buy(res,0.1,10);Check("daily_loss_blocks_entries_today",!ok&&StringFind(res.comment,"daily")>=0,res.comment);
      Check("no_firm_breach_at_minus_2pct",!GlobalVariableCheck(FundedKey("BREACHED")),StringFormat("loss %.2f < firm 3%%",s.day_ref-s.equity));
      PrintFormat("HARNESS_RESULT passes=%d fails=%d",passes,fails);step=9;}
}
void OnTick(){
   FundedPulse();                                          // what every guarded EA does on each tick
   if(HarnessMode==2){LossMode();return;}
   if(step>12 || TimeCurrent()<waitUntil)return;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||!FundedAccountOK())return;
   double sv=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   MqlTradeRequest r={};MqlTradeResult res={};
   if(step==0){FundedState s=State();Check("flat_floor_47000_unlocked",MathAbs(s.floor-47000)<0.01&&!s.locked,StringFormat("floor=%.2f peak=%.2f locked=%d",s.floor,s.peak,(int)s.locked));
      Check("day_reference_recorded",GlobalVariableCheck(FundedKey("DREF_"+IntegerToString(Today())))&&s.day_ref>=s.balance-0.01,StringFormat("dayref=%.2f bal=%.2f",s.day_ref,s.balance));
      phaseDay=Today();step++;return;}
   if(step==1){double exp=Expected(0),u=Unit(true,q.ask,q.ask-10);bool ok=Buy(res,5.0,10);double risk=u*res.volume;   // at the guard's admission price (fills include the 150 ms delay)
      Check("market_sized_to_budget",ok&&res.retcode==TRADE_RETCODE_DONE&&risk<=exp+0.5&&risk>=exp-u*sv-0.5,StringFormat("exp=%.2f risk=%.2f vol=%.2f req=5.00",exp,risk,res.volume));
      if(PositionSelect(_Symbol))pos1=PositionGetInteger(POSITION_TICKET);step++;return;}
   if(step==2){r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_BUY;r.volume=0.1;r.sl=0;bool ok=Send(r,res);Check("no_sl_rejected",!ok&&res.retcode==TRADE_RETCODE_REJECT,res.comment);
      if(!PositionSelectByTicket(pos1)){Check("position_exists",false,"");step=99;return;}
      double sl=PositionGetDouble(POSITION_SL);ZeroMemory(r);r.action=TRADE_ACTION_SLTP;r.position=pos1;r.sl=sl-5;bool wide=Send(r,res);
      Check("widen_sl_rejected",!wide&&res.retcode==TRADE_RETCODE_REJECT,res.comment);step++;return;}
   if(step==3){double open=OpenRisk(),exp=Expected(open),price=NormalizeDouble(q.ask-50,_Digits),sl=price-10,u=Unit(true,price,sl);
      r.action=TRADE_ACTION_PENDING;r.type=ORDER_TYPE_BUY_LIMIT;r.price=price;r.sl=sl;r.volume=5.0;r.type_time=ORDER_TIME_GTC;bool ok=Send(r,res);pend=res.order;double risk=0;
      if(OrderSelect(pend))risk=u*OrderGetDouble(ORDER_VOLUME_CURRENT);
      Check("pending_sized_and_reserved",ok&&risk<=exp+0.5&&risk>=exp-u*sv-0.5&&OpenRisk()>open+risk-1,StringFormat("open=%.2f exp=%.2f risk=%.2f",open,exp,risk));step++;return;}
   if(step==4){if(Today()!=phaseDay){Check("daily_win_triggered_same_day",false,"no +0.75% day");step=6;return;}   // wait for a natural +0.75% equity day
      if(!GlobalVariableCheck(FundedKey("WIN_"+IntegerToString(Today()))))return;
      Check("daily_win_triggered",true,StringFormat("eq=%.2f",AccountInfoDouble(ACCOUNT_EQUITY)));waitUntil=TimeCurrent()+60;step++;return;}
   if(step==5){Check("daily_win_closes_all",Flat()&&GlobalVariableCheck(FundedKey("WIN_"+IntegerToString(Today()))),StringFormat("positions=%d orders=%d",PositionsTotal(),OrdersTotal()));
      bool ok=Buy(res,0.1,10);Check("daily_win_blocks_entries_today",!ok&&StringFind(res.comment,"daily")>=0,res.comment);step++;return;}
   if(step==6){if(Today()==phaseDay)return;phaseDay=Today();
      bool ok=Buy(res,0.1,10);Check("next_day_entries_allowed",ok&&res.retcode==TRADE_RETCODE_DONE,res.comment);step++;return;}
   if(step==7){FundedState a=State();bool ok=TesterDeposit(53600-a.balance);FundedState b=State();
      Check("floor_locks_at_initial_after_plus_6pct",ok&&b.locked&&MathAbs(b.floor-50000)<0.01,StringFormat("bal=%.2f peak=%.2f floor=%.2f locked=%d",b.balance,b.peak,b.floor,(int)b.locked));
      waitUntil=TimeCurrent()+60;step++;return;}
   if(step==8){if(Today()==phaseDay)return;phaseDay=Today();
      bool ok=Buy(res,0.1,10);FundedState a=State();
      Check("locked_floor_room_sizing",ok,StringFormat("bal=%.2f floor=%.2f room=%.2f",a.balance,a.floor,a.balance-a.floor));
      bool w=TesterWithdrawal(1100);waitUntil=TimeCurrent()+60;Check("payout_withdrawal_1100",w,"");step++;return;}
   if(step==9){FundedState s=State();
      Check("payout_is_not_a_daily_loss",!GlobalVariableCheck(FundedKey("LOSS_"+IntegerToString(Today())))&&!GlobalVariableCheck(FundedKey("BREACHED"))&&s.equity-s.day_ref>-100,StringFormat("eq=%.2f dayref=%.2f",s.equity,s.day_ref));
      Check("floor_stays_locked_after_payout",s.locked&&MathAbs(s.floor-50000)<0.01&&s.withdrawals>=1,StringFormat("floor=%.2f withdrawals=%d",s.floor,s.withdrawals));step++;return;}
   if(step==10){if(Today()==phaseDay)return;phaseDay=Today();
      bool ok=Buy(res,0.1,10);FundedState s=State();bool w=TesterWithdrawal(s.balance-50100);waitUntil=TimeCurrent()+60;
      Check("setup_floor_buffer",ok&&w,StringFormat("withdraw to 50100, floor %.2f, buffer 125",s.floor));step++;return;}
   if(step==11){FundedState s=State();
      Check("floor_buffer_closes_all",Flat()&&GlobalVariableCheck(FundedKey("FLOOR_"+IntegerToString(Today()))),StringFormat("positions=%d eq=%.2f floor=%.2f",PositionsTotal(),s.equity,s.floor));
      bool ok=Buy(res,0.1,10);Check("no_entry_inside_buffer",!ok,res.comment);
      Check("no_firm_breach_latched",!GlobalVariableCheck(FundedKey("BREACHED")),"equity stayed above the $50,000 floor");
      PrintFormat("HARNESS_RESULT passes=%d fails=%d",passes,fails);step++;}
}
