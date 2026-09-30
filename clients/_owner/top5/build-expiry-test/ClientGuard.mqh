#ifndef CALYX_CLIENT_GUARD
#define CALYX_CLIENT_GUARD
// Owner build constants are supplied by the wrapper, never by installer inputs.
input group "Calyx client risk and account confirmation"
input int ClientRiskMode=0; // 0 = fixed USD, 1 = percent of CURRENT BALANCE
input double ClientRiskValue=50.0;
input long ClientExpectedLogin=0;
input string ClientExpectedServer="";
input string ClientExpectedSymbol="";
long ClientMagic();
datetime client_last_notice=0,client_last_pulse=0;
bool ClientTester(){return (bool)MQLInfoInteger(MQL_TESTER);}
bool ClientContext(){
 if(AccountInfoString(ACCOUNT_CURRENCY)!="USD")return false;
 if(!ClientTester() && AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return false;
 if(!ClientTester() && (ClientExpectedLogin<=0 || ClientExpectedServer=="" || ClientExpectedSymbol==""))return false;
 if(ClientExpectedLogin>0 && AccountInfoInteger(ACCOUNT_LOGIN)!=ClientExpectedLogin)return false;
 if(ClientExpectedServer!="" && AccountInfoString(ACCOUNT_SERVER)!=ClientExpectedServer)return false;
 if(ClientExpectedSymbol!="" && _Symbol!=ClientExpectedSymbol)return false;
 if(CLIENT_BOUND_LOGIN>0 && AccountInfoInteger(ACCOUNT_LOGIN)!=CLIENT_BOUND_LOGIN)return false;
 if(CLIENT_BOUND_SERVER!="" && AccountInfoString(ACCOUNT_SERVER)!=CLIENT_BOUND_SERVER)return false;
 return true;
}
datetime ClientClock(){
 if(ClientTester())return TimeCurrent();
 // Fail closed on backwards clock changes. Broker time may expire earlier than UTC.
 datetime now=(datetime)MathMax((double)TimeGMT(),(double)TimeTradeServer());
 string key="CLX_TOP5_CLOCK_"+IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
 if(GlobalVariableCheck(key)){
   datetime prior=(datetime)GlobalVariableGet(key);
   if(now+300<prior)return CLIENT_EXPIRES;
   now=(datetime)MathMax((double)now,(double)prior);
 }
 if(now>0)GlobalVariableSet(key,(double)now);
 return now;
}
bool ClientLicenseValid(){
 if(ClientTester() && !CLIENT_TEST_EXPIRY)return true;
 datetime now=ClientClock();
 return now>0 && now<CLIENT_EXPIRES && (ClientTester() || now>=CLIENT_ISSUED-86400);
}
double ClientRiskCash(){
 if(ClientRiskMode<0 || ClientRiskMode>1 || !MathIsValidNumber(ClientRiskValue) || ClientRiskValue<=0)return 0;
 if(ClientRiskMode==1 && ClientRiskValue>5.0)return 0;
 return ClientRiskMode==0?ClientRiskValue:AccountInfoDouble(ACCOUNT_BALANCE)*ClientRiskValue/100.0;
}
double ClientSizedVolume(const ENUM_ORDER_TYPE type,const double entry,const double stop){
 double unit=0,target=ClientRiskCash(),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(target<=0 || stop<=0 || entry<=0 || step<=0 || (type!=ORDER_TYPE_BUY && type!=ORDER_TYPE_SELL))return 0;
 if(!OrderCalcProfit(type,_Symbol,1,entry,stop,unit) || unit>=0)return 0;
 double lots=MathFloor((target/MathAbs(unit)+1e-10)/step)*step;
 lots=NormalizeDouble(MathMin(lots,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)),8);
 if(lots<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)-1e-10)return 0;
 return lots;
}
bool ClientOwnPosition(const ulong ticket){
 return ticket>0 && PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==ClientMagic();
}
bool ClientOwnOrder(const ulong ticket){
 return ticket>0 && OrderSelect(ticket) && OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==ClientMagic();
}
bool ClientRefuse(MqlTradeResult &result,const string reason){
 ZeroMemory(result);result.retcode=TRADE_RETCODE_INVALID;result.comment="Calyx: "+reason;
 if(TimeCurrent()-client_last_notice>=60){Print("CLIENT_BLOCK ",reason);client_last_notice=TimeCurrent();}
 return false;
}
bool ClientOrderSend(const MqlTradeRequest &request,MqlTradeResult &result){
 MqlTradeRequest r=request;
 if(!ClientContext())return ClientRefuse(result,"account / symbol / USD hedging confirmation mismatch");
 // Reductions and protective management remain available after expiry, only for our positions.
 if(r.action==TRADE_ACTION_SLTP){
   if(!ClientOwnPosition(r.position))return ClientRefuse(result,"foreign position");
   return ::OrderSend(r,result);
 }
 if(r.action==TRADE_ACTION_REMOVE){
   if(!ClientOwnOrder(r.order))return ClientRefuse(result,"foreign order");
   return ::OrderSend(r,result);
 }
 if(r.action==TRADE_ACTION_DEAL && r.position>0){
   if(!ClientOwnPosition(r.position))return ClientRefuse(result,"foreign close");
   long side=PositionGetInteger(POSITION_TYPE);
   if((side==POSITION_TYPE_BUY && r.type!=ORDER_TYPE_SELL) || (side==POSITION_TYPE_SELL && r.type!=ORDER_TYPE_BUY) || r.volume>PositionGetDouble(POSITION_VOLUME)+1e-9)
      return ClientRefuse(result,"not a position reduction");
   return ::OrderSend(r,result);
 }
 if(!ClientLicenseValid())return ClientRefuse(result,"licence expired; management only");
 if(r.action==TRADE_ACTION_MODIFY){
   if(!ClientOwnOrder(r.order))return ClientRefuse(result,"foreign pending order");
   return ::OrderSend(r,result);
 }
 if((r.action!=TRADE_ACTION_DEAL && r.action!=TRADE_ACTION_PENDING) || r.symbol!=_Symbol || (long)r.magic!=ClientMagic())
    return ClientRefuse(result,"unsupported action / magic");
 ENUM_ORDER_TYPE side=(r.type==ORDER_TYPE_BUY || r.type==ORDER_TYPE_BUY_LIMIT || r.type==ORDER_TYPE_BUY_STOP || r.type==ORDER_TYPE_BUY_STOP_LIMIT)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double entry=r.price;
 if(r.action==TRADE_ACTION_DEAL){MqlTick q;if(!SymbolInfoTick(_Symbol,q))return ClientRefuse(result,"no quote");entry=side==ORDER_TYPE_BUY?q.ask:q.bid;}
 r.volume=ClientSizedVolume(side,entry,r.sl);
 if(r.volume<=0)return ClientRefuse(result,"risk below minimum lot / invalid stop");
 // Limit pending lifetime at the broker too; unsupported specified expiry fails closed.
 if(r.action==TRADE_ACTION_PENDING && (!ClientTester() || CLIENT_TEST_EXPIRY)){
   r.type_time=ORDER_TIME_SPECIFIED;
   if(r.expiration<=0 || r.expiration>CLIENT_EXPIRES)r.expiration=CLIENT_EXPIRES;
 }
 MqlTradeCheckResult check={};
 if(!OrderCheck(r,check))return ClientRefuse(result,"broker order check: "+check.comment);
 bool sent=::OrderSend(r,result);
 if(sent && (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_PLACED || result.retcode==TRADE_RETCODE_DONE_PARTIAL)){
   double stopcash=0;if(!OrderCalcProfit(side,_Symbol,r.volume,entry,r.sl,stopcash))stopcash=EMPTY_VALUE;
   PrintFormat("CLIENT_ENTRY mode=%d target=%.2f planned=%.2f volume=%.8f balance=%.2f",ClientRiskMode,ClientRiskCash(),MathAbs(stopcash),r.volume,AccountInfoDouble(ACCOUNT_BALANCE));
 }
 return sent;
}
void ClientPulse(){
 if(TimeCurrent()==client_last_pulse)return;
 client_last_pulse=TimeCurrent();
 if(!ClientContext() || ClientLicenseValid())return;
 // Keep running; never ExpertRemove and never liquidate positions as a licence action.
 for(int i=OrdersTotal()-1;i>=0;i--){
   ulong ticket=OrderGetTicket(i);
   if(!ClientOwnOrder(ticket))continue;
   MqlTradeRequest r={};MqlTradeResult out={};r.action=TRADE_ACTION_REMOVE;r.order=ticket;
   ClientOrderSend(r,out);
 }
 if(TimeCurrent()-client_last_notice>=3600){Print("CLIENT_EXPIRED: no new entries; existing own positions remain managed.");client_last_notice=TimeCurrent();}
}
int ClientInit(){
 if(!ClientContext() || ClientRiskCash()<=0){Print("CLIENT_INIT: require USD hedging account, valid risk and matching account/server/symbol inputs.");return INIT_PARAMETERS_INCORRECT;}
 Print("CLIENT_LICENCE ",CLIENT_ID," expires ",TimeToString(CLIENT_EXPIRES,TIME_DATE|TIME_SECONDS),"; UTC/broker clock, whichever reaches expiry first. Rounds risk DOWN; costs/gaps can exceed planned stop risk.");
 if(!ClientLicenseValid())Print("CLIENT_EXPIRED: starting in management-only mode.");
 return INIT_SUCCEEDED;
}
#endif
