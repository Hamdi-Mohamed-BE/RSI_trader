#property strict
datetime guard_expiry=0;
#define CLIENT_ID "TESTER-ONLY-GUARD-HARNESS"
#define CLIENT_ISSUED ((datetime)0)
#define CLIENT_EXPIRES guard_expiry
#define CLIENT_BOUND_LOGIN ((long)0)
#define CLIENT_BOUND_SERVER ""
#define CLIENT_TEST_EXPIRY true
#include "ClientGuard.mqh"
input long InpMagic=93095999;
long ClientMagic(){return InpMagic;}
int stage=0;ulong own_pending=0,foreign_pending=0,position=0;
ENUM_ORDER_TYPE_FILLING Filling(){return (SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE)&SYMBOL_FILLING_FOK)!=0?ORDER_FILLING_FOK:ORDER_FILLING_IOC;}
void Fail(string reason){Print("HARNESS_FAIL ",reason);stage=99;TesterStop();}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return ClientInit();}
bool SendRaw(MqlTradeRequest &r,MqlTradeResult &out){bool ok=OrderSend(r,out);return ok&&(out.retcode==TRADE_RETCODE_DONE||out.retcode==TRADE_RETCODE_PLACED);}
void OnTick(){
 if(stage==99)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
 if(stage==0){
  guard_expiry=TimeCurrent()+60;
  MqlTradeRequest r={};MqlTradeResult out={};
  r.action=TRADE_ACTION_DEAL;r.symbol=_Symbol;r.magic=InpMagic;r.type=ORDER_TYPE_BUY;r.price=q.ask;r.sl=NormalizeDouble(q.bid*.995,digits);r.type_filling=Filling();r.volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  if(!ClientOrderSend(r,out)||!PositionSelect(_Symbol)){Fail("initial guarded entry");return;}
  position=(ulong)PositionGetInteger(POSITION_TICKET);
  r.action=TRADE_ACTION_PENDING;r.type=ORDER_TYPE_BUY_LIMIT;r.type_filling=ORDER_FILLING_RETURN;r.price=NormalizeDouble(q.bid*.9,digits);r.sl=NormalizeDouble(q.bid*.88,digits);r.volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);r.type_time=ORDER_TIME_GTC;
  // Intentionally seed GTC orders using native API: test cleanup and ownership separation.
  if(!SendRaw(r,out)){Fail("seed own pending");return;}own_pending=out.order;
  r.magic=InpMagic+1;r.price=NormalizeDouble(q.bid*.89,digits);
  if(!SendRaw(r,out)){Fail("seed foreign pending");return;}foreign_pending=out.order;
  stage=1;return;
 }
 if(stage==1 && TimeCurrent()>=guard_expiry){
  ClientPulse();
  if(OrderSelect(own_pending)||!OrderSelect(foreign_pending)){Fail("expiry pending ownership cleanup");return;}
  MqlTradeRequest r={};MqlTradeResult out={};r.action=TRADE_ACTION_REMOVE;r.order=foreign_pending;
  if(ClientOrderSend(r,out)){Fail("foreign cancel allowed");return;}
  r.action=TRADE_ACTION_DEAL;r.order=0;r.symbol=_Symbol;r.magic=InpMagic;r.type=ORDER_TYPE_BUY;r.price=q.ask;r.sl=NormalizeDouble(q.bid*.98,digits);r.type_filling=Filling();r.volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  if(ClientOrderSend(r,out)){Fail("entry allowed after expiry");return;}
  if(!PositionSelectByTicket(position)){Fail("position disappeared");return;}
  double volume=PositionGetDouble(POSITION_VOLUME);
  r.action=TRADE_ACTION_SLTP;r.position=position;r.sl=NormalizeDouble(q.bid*.996,digits);r.tp=0;
  if(!ClientOrderSend(r,out)||out.retcode!=TRADE_RETCODE_DONE){Fail("protective modification denied");return;}
  r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_SELL;r.price=q.bid;r.volume=volume;r.sl=0;r.tp=0;
  if(!ClientOrderSend(r,out)||out.retcode!=TRADE_RETCODE_DONE){Fail("protective close denied");return;}
  ZeroMemory(r);r.action=TRADE_ACTION_REMOVE;r.order=foreign_pending;
  if(!SendRaw(r,out)){Fail("test cleanup");return;}
  Print("HARNESS_PASS: expired entries blocked; own pending cancelled; foreign pending protected; SL modification and close allowed.");stage=99;TesterStop();
 }
}
