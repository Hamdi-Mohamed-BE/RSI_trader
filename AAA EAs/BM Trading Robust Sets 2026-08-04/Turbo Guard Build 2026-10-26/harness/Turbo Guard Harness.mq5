#property strict
#property description "Tester-only harness for CalyxTurboGuard.mqh: sizing, SL rules, pending reservation, withdrawal re-base, breach latch."
#include "..\..\_00 Live profiles\Packages\Turbo5\package\CalyxTurboGuard.mqh"

int step=0,passes=0,fails=0;ulong pos1=0,pend=0;
void Check(const string name,const bool ok,const string detail){
   if(ok)passes++;else fails++;
   PrintFormat("HARNESS %s %s %s",ok?"PASS":"FAIL",name,detail);
}
double Unit(const bool buy,const double price,const double sl){double u=0;TurboUnitRisk(_Symbol,buy,price,sl,u);return u;}
TurboState State(){int off=0;datetime utc=0;TurboState s={};TurboClock(off,utc);TurboLedger(s,off,utc);return s;}
double OpenRisk(){                                         // independent: original stop risk of every position + pending order
   double r=0;
   for(int i=0;i<PositionsTotal();i++){ulong t=PositionGetTicket(i);if(!t)continue;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;long id=PositionGetInteger(POSITION_IDENTIFIER);
      double osl=HistoryOrderSelect((ulong)id)?HistoryOrderGetDouble((ulong)id,ORDER_SL):PositionGetDouble(POSITION_SL);
      r+=Unit(buy,PositionGetDouble(POSITION_PRICE_OPEN),osl)*PositionGetDouble(POSITION_VOLUME);}
   for(int i=0;i<OrdersTotal();i++){ulong t=OrderGetTicket(i);if(!t)continue;
      r+=Unit(TurboBuyType(OrderGetInteger(ORDER_TYPE)),OrderGetDouble(ORDER_PRICE_OPEN),OrderGetDouble(ORDER_SL))*OrderGetDouble(ORDER_VOLUME_CURRENT);}
   return r;
}
double Expected(const double open){                         // the sim.py rule on $50k, all limits independent of the guard code
   TurboState s=State();double stress=s.balance-open,room=stress-s.floor;
   return MathMin(MathMin(MathMin(375.0,0.05*room),MathMin(1000-open,750-open)),MathMin(1000-(s.anchor-stress),room-125));
}
bool Send(MqlTradeRequest &r,MqlTradeResult &res){ZeroMemory(res);r.symbol=_Symbol;r.deviation=1000;r.magic=777;return TurboOrderSend(r,res);}
void OnTick(){
   if(step>8)return;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||!TurboAccountOK())return;
   double step_v=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   MqlTradeRequest r={};MqlTradeResult res={};
   if(step==0){TurboState s=State();Check("flat_floor_47000",MathAbs(s.floor-47000)<0.01,StringFormat("floor=%.2f peak=%.2f",s.floor,s.peak));step++;return;}
   if(step==1){
      double exp=Expected(0),sl=q.ask-10,u=Unit(true,q.ask,sl);
      r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_BUY;r.volume=5.0;r.sl=sl;r.type_filling=ORDER_FILLING_IOC;
      bool ok=Send(r,res);double risk=Unit(true,res.price>0?res.price:q.ask,sl)*res.volume;
      Check("market_sized_to_budget",ok&&res.retcode==TRADE_RETCODE_DONE&&risk<=exp+0.5&&risk>=exp-u*step_v-0.5,StringFormat("exp=%.2f risk=%.2f vol=%.2f req=5.00",exp,risk,res.volume));
      if(PositionSelect(_Symbol))pos1=PositionGetInteger(POSITION_TICKET);step++;return;}
   if(step==2){r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_BUY;r.volume=0.1;r.sl=0;bool ok=Send(r,res);
      Check("no_sl_rejected",!ok&&res.retcode==TRADE_RETCODE_REJECT,res.comment);step++;return;}
   if(step==3){if(!PositionSelectByTicket(pos1)){Check("position_exists",false,"");step=9;return;}
      double sl=PositionGetDouble(POSITION_SL);
      r.action=TRADE_ACTION_SLTP;r.position=pos1;r.sl=sl-5;bool wide=Send(r,res);
      Check("widen_sl_rejected",!wide&&res.retcode==TRADE_RETCODE_REJECT,res.comment);
      ZeroMemory(r);r.action=TRADE_ACTION_SLTP;r.position=pos1;r.sl=sl+2;bool tight=Send(r,res);
      Check("tighten_sl_allowed",tight&&res.retcode==TRADE_RETCODE_DONE,res.comment);
      ZeroMemory(r);r.action=TRADE_ACTION_SLTP;r.position=pos1;r.sl=0;bool rem=Send(r,res);
      Check("remove_sl_rejected",!rem,res.comment);step++;return;}
   if(step==4){double open=OpenRisk(),exp=Expected(open),price=NormalizeDouble(q.ask-50,_Digits),sl=price-10,u=Unit(true,price,sl);
      r.action=TRADE_ACTION_PENDING;r.type=ORDER_TYPE_BUY_LIMIT;r.price=price;r.sl=sl;r.volume=5.0;r.type_time=ORDER_TIME_GTC;
      bool ok=Send(r,res);pend=res.order;double risk=0;
      if(OrderSelect(pend))risk=u*OrderGetDouble(ORDER_VOLUME_CURRENT);
      Check("pending_sized_to_budget",ok&&res.retcode==TRADE_RETCODE_DONE&&risk<=exp+0.5&&risk>=exp-u*step_v-0.5,StringFormat("open=%.2f exp=%.2f risk=%.2f",open,exp,risk));
      ZeroMemory(r);r.action=TRADE_ACTION_MODIFY;r.order=pend;r.price=price;r.sl=sl-5;r.type_time=ORDER_TIME_GTC;bool wid=Send(r,res);
      Check("pending_widen_rejected",!wid&&res.retcode==TRADE_RETCODE_REJECT,res.comment);step++;return;}
   if(step==5){double open=OpenRisk(),exp=Expected(open),sl=q.ask-10,u=Unit(true,q.ask,sl);
      r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_BUY;r.volume=5.0;r.sl=sl;r.type_filling=ORDER_FILLING_IOC;bool ok=Send(r,res);
      double risk=Unit(true,res.price>0?res.price:q.ask,sl)*res.volume;
      Check("pending_reserved_in_exposure",ok&&risk<=exp+0.5&&risk>=exp-u*step_v-0.5&&open>0,StringFormat("open_incl_pending=%.2f exp=%.2f risk=%.2f",open,exp,risk));step++;return;}
   if(step==6){for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(!t)continue;ZeroMemory(r);r.action=TRADE_ACTION_DEAL;r.position=t;r.volume=PositionGetDouble(POSITION_VOLUME);
         r.type=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?ORDER_TYPE_SELL:ORDER_TYPE_BUY;r.price=r.type==ORDER_TYPE_SELL?q.bid:q.ask;r.type_filling=ORDER_FILLING_IOC;Send(r,res);}
      for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);if(!t)continue;ZeroMemory(r);r.action=TRADE_ACTION_REMOVE;r.order=t;Send(r,res);}
      Check("closes_and_removes_allowed",PositionsTotal()==0&&OrdersTotal()==0,StringFormat("positions=%d orders=%d",PositionsTotal(),OrdersTotal()));step++;return;}
   if(step==7){TurboState a=State();bool w=TesterWithdrawal(1000);TurboState b=State();
      Check("withdrawal_rebases_floor",w&&b.withdrawals==a.withdrawals+1&&MathAbs(b.peak-b.balance)<0.01&&MathAbs(b.floor-(b.balance-3000))<0.01,
            StringFormat("before bal=%.2f floor=%.2f | after bal=%.2f peak=%.2f floor=%.2f",a.balance,a.floor,b.balance,b.peak,b.floor));step++;return;}
   if(step==8){GlobalVariableSet(TurboKey("BREACHED"),1);r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_BUY;r.volume=0.1;r.sl=q.ask-10;r.type_filling=ORDER_FILLING_IOC;bool ok=Send(r,res);
      Check("breach_latch_blocks_entries",!ok&&StringFind(res.comment,"latched")>=0,res.comment);GlobalVariableDel(TurboKey("BREACHED"));
      PrintFormat("HARNESS_RESULT passes=%d fails=%d",passes,fails);step++;}
}
