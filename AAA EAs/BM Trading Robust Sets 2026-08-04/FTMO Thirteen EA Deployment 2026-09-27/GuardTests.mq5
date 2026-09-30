#property strict
// Native MQL tests of the production header with broker APIs replaced by fixtures.
// MockSend NEVER sends an order. No account connection is used by test assertions.
datetime test_utc=D'2026.09.28 10:00:00';
double test_equity=10000,test_balance=10000,test_margin=0,test_free=10000;
double test_min=.01,test_step=.01,test_price=4000,test_stop=3990;
bool test_history=true,test_connected=true,test_firm=true,test_symbol_ok=true;
int test_pending=0,test_pos=0,test_deals=1,test_selected=0,test_requests=0,test_lock=1;
double test_sent_volume=0,test_sent_sl=0;
string test_keys[];double test_values[];
struct TD {long id;int kind,entry;datetime time;double profit;};
TD td[100];
struct TP {long id;string symbol;double volume,price,sl,risk;};
TP tp[10];
long MockAI(const ENUM_ACCOUNT_INFO_INTEGER key) {
   if(key==ACCOUNT_LOGIN)return 123456;
   if(key==ACCOUNT_MARGIN_MODE)return ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
   return 1;
}
string MockAS(const ENUM_ACCOUNT_INFO_STRING key) {
   if(key==ACCOUNT_SERVER)return "FTMO.UnitTest";
   if(key==ACCOUNT_COMPANY)return test_firm?"FTMO Tests":"Different Broker";
   if(key==ACCOUNT_CURRENCY)return "USD";
   return "";
}
double MockAD(const ENUM_ACCOUNT_INFO_DOUBLE key) {
   if(key==ACCOUNT_BALANCE)return test_balance;
   if(key==ACCOUNT_EQUITY)return test_equity;
   if(key==ACCOUNT_MARGIN)return test_margin;
   if(key==ACCOUNT_MARGIN_FREE)return test_free;
   return 0;
}
int MockMI(const ENUM_MQL_INFO_INTEGER key){return 0;}
int MockTI(const ENUM_TERMINAL_INFO_INTEGER key){return test_connected?1:0;}
datetime MockUTC(){return test_utc;}
datetime MockServer(){return test_utc+10800;}
bool MockTick(string symbol,MqlTick &tick){
   ZeroMemory(tick);tick.ask=test_price;tick.bid=test_price-.2;tick.time=MockServer();return true;
}
double MockSD(string symbol,ENUM_SYMBOL_INFO_DOUBLE key){
   if(key==SYMBOL_VOLUME_MIN)return test_min;
   if(key==SYMBOL_VOLUME_STEP)return test_step;
   if(key==SYMBOL_VOLUME_MAX)return 100;
   return .01;
}
bool MockProfit(ENUM_ORDER_TYPE type,string symbol,double lots,double entry,double sl,double &v){
   v=(sl-entry)*100*lots*(type==ORDER_TYPE_BUY?1:-1);return true;
}
bool MockMargin(ENUM_ORDER_TYPE type,string symbol,double lots,double entry,double &v){v=entry*lots*100/15;return true;}
int MockPT(){return test_pos;}
int MockOT(){return test_pending;}
ulong MockPGT(int i){test_selected=i;return (ulong)tp[i].id;}
bool MockPST(ulong id){for(int i=0;i<test_pos;i++)if(tp[i].id==(long)id){test_selected=i;return true;}return false;}
long MockPGI(ENUM_POSITION_PROPERTY_INTEGER p){return p==POSITION_IDENTIFIER?tp[test_selected].id:POSITION_TYPE_BUY;}
string MockPGS(ENUM_POSITION_PROPERTY_STRING p){return tp[test_selected].symbol;}
double MockPGD(ENUM_POSITION_PROPERTY_DOUBLE p){
   if(p==POSITION_VOLUME)return tp[test_selected].volume;
   if(p==POSITION_PRICE_OPEN)return tp[test_selected].price;
   if(p==POSITION_SL)return tp[test_selected].sl;return 0;
}
bool MockHS(datetime a,datetime b){return test_history;}
int MockHDT(){return test_deals;}
ulong MockHDGT(int i){return (ulong)i+1;}
long MockHDI(ulong d,ENUM_DEAL_PROPERTY_INTEGER p){
   int i=(int)d-1;
   if(p==DEAL_TYPE)return td[i].kind;
   if(p==DEAL_ENTRY)return td[i].entry;
   if(p==DEAL_POSITION_ID)return td[i].id;
   if(p==DEAL_TIME)return td[i].time;
   return 0;
}
double MockHDD(ulong d,ENUM_DEAL_PROPERTY_DOUBLE p){return p==DEAL_PROFIT?td[(int)d-1].profit:0;}
bool MockHOS(ulong id){return true;}
double MockHOD(ulong id,ENUM_ORDER_PROPERTY_DOUBLE p){return test_stop;}
bool MockHDS(ulong id){return false;}
bool MockGVC(string k){for(int i=0;i<ArraySize(test_keys);i++)if(test_keys[i]==k)return true;return false;}
double MockGVG(string k){for(int i=0;i<ArraySize(test_keys);i++)if(test_keys[i]==k)return test_values[i];return 0;}
datetime MockGVS(string k,double v){
   for(int i=0;i<ArraySize(test_keys);i++)if(test_keys[i]==k){test_values[i]=v;return test_utc;}
   int n=ArraySize(test_keys);ArrayResize(test_keys,n+1);ArrayResize(test_values,n+1);
   test_keys[n]=k;test_values[n]=v;return test_utc;
}
int MockFO(string name,int flags){return test_lock;}
void MockFC(int handle){}
bool MockSend(const MqlTradeRequest &r,MqlTradeResult &out){
   test_requests++;test_sent_volume=r.volume;test_sent_sl=r.sl;
   ZeroMemory(out);out.retcode=TRADE_RETCODE_DONE;out.order=999;
   out.volume=r.volume;out.price=r.price;return true;
}
#define AccountInfoInteger MockAI
#define AccountInfoString MockAS
#define AccountInfoDouble MockAD
#define MQLInfoInteger MockMI
#define TerminalInfoInteger MockTI
#define TimeGMT MockUTC
#define TimeLocal MockUTC
#define TimeTradeServer MockServer
#define SymbolInfoTick MockTick
#define SymbolInfoDouble MockSD
#define OrderCalcProfit MockProfit
#define OrderCalcMargin MockMargin
#define PositionsTotal MockPT
#define OrdersTotal MockOT
#define PositionGetTicket MockPGT
#define PositionSelectByTicket MockPST
#define PositionGetInteger MockPGI
#define PositionGetString MockPGS
#define PositionGetDouble MockPGD
#define HistorySelect MockHS
#define HistoryDealsTotal MockHDT
#define HistoryDealGetTicket MockHDGT
#define HistoryDealGetInteger MockHDI
#define HistoryDealGetDouble MockHDD
#define HistoryOrderSelect MockHOS
#define HistoryOrderGetDouble MockHOD
#define HistoryDealSelect MockHDS
#define GlobalVariableCheck MockGVC
#define GlobalVariableGet MockGVG
#define GlobalVariableSet MockGVS
#define FileOpen MockFO
#define FileClose MockFC
#define OrderSend MockSend
#include "CalyxFTMOGuard.mqh"
int checks=0,failures=0;
void Check(bool ok,string name){checks++;if(!ok){failures++;Print("GUARD FAIL: ",name);}}
void Reset(){
   ArrayResize(test_keys,0);ArrayResize(test_values,0);
   test_equity=10000;test_balance=10000;test_margin=0;test_free=10000;test_min=.01;test_step=.01;
   test_price=4000;test_stop=3990;test_history=true;test_connected=true;test_firm=true;
   test_pending=0;test_pos=0;test_deals=1;test_requests=0;test_lock=1;
   ZeroMemory(td);ZeroMemory(tp);
   td[0].kind=DEAL_TYPE_BALANCE;td[0].profit=10000;td[0].time=MockServer()-600;
}
MqlTradeRequest Entry(){
   MqlTradeRequest r={};r.action=TRADE_ACTION_DEAL;r.type=ORDER_TYPE_BUY;
   r.symbol=_Symbol;r.volume=.06;r.price=4000;r.sl=3990;return r;
}
void Positions(int count,bool same=true){
   test_pos=count;
   for(int i=0;i<count;i++){
      tp[i].id=100+i;tp[i].symbol=same?_Symbol:"OTHER";
      tp[i].volume=.05;tp[i].price=4000;tp[i].sl=3990;
      MockGVS(FTMOKey("R_"+IntegerToString(tp[i].id)),50);
   }
}
void Losses(int count){
   for(int i=0;i<count;i++){
      int a=1+2*i,b=a+1;td[a].id=100+i;td[a].kind=DEAL_TYPE_BUY;td[a].entry=DEAL_ENTRY_IN;
      td[a].time=MockServer()-100;td[b]=td[a];td[b].kind=DEAL_TYPE_SELL;
      td[b].entry=DEAL_ENTRY_OUT;td[b].profit=-50;td[b].time=MockServer()-50;
   }
   test_deals=1+2*count;test_balance=test_equity=10000-50*count;
}
int OnInit(){
   MqlTradeResult result={};MqlTradeRequest r={};double anchor=0;int n=0,l=0,d=0;
   Reset();Check(FTMOInit()==INIT_SUCCEEDED,"bound account");
   Check(FTMODay(D'2026.03.28 23:00:00')==20260329,"Prague spring midnight");
   Check(FTMOPragueOffset(D'2026.03.29 00:59:59')==3600,"before DST");
   Check(FTMOPragueOffset(D'2026.03.29 01:00:00')==7200,"start DST");
   Check(FTMOPragueOffset(D'2026.10.25 01:00:00')==3600,"end DST");
   Check(FTMOLotsDown(.019,.01)==.01 && FTMOLotsDown(.009,.01)==0,"round DOWN");
   Check(FTMOLedger(anchor,n,l,d,10800,test_utc) && anchor==10000,"first funding day anchor");
   r=Entry();Check(FTMOOrderSend(r,result) && MathAbs(test_sent_volume-.05)<1e-8,"risk resized to 50");
   Reset();r=Entry();test_min=.1;Check(!FTMOOrderSend(r,result) && test_requests==0,"minimum lot skip");
   Reset();r=Entry();r.sl=0;Check(!FTMOOrderSend(r,result),"SL required");
   Reset();r=Entry();r.sl=4010;Check(!FTMOOrderSend(r,result),"SL correct side");
   Reset();r=Entry();test_firm=false;Check(!FTMOOrderSend(r,result),"wrong broker");
   Reset();r=Entry();r.symbol="OTHER";Check(!FTMOOrderSend(r,result),"symbol lock");
   Reset();r=Entry();test_history=false;Check(!FTMOOrderSend(r,result),"history fail closed");
   Reset();r=Entry();test_pending=1;Check(!FTMOOrderSend(r,result),"unknown pending");
   Reset();r=Entry();Positions(3);Check(!FTMOOrderSend(r,result),"150 per symbol");
   Reset();r=Entry();Positions(4,false);Check(!FTMOOrderSend(r,result),"225 aggregate");
   Reset();r=Entry();Positions(1);tp[0].sl=0;Check(!FTMOOrderSend(r,result),"unprotected position");
   Reset();r=Entry();test_free=10;Check(!FTMOOrderSend(r,result),"free margin");
   Reset();r=Entry();test_margin=7900;Check(!FTMOOrderSend(r,result),"80 percent margin");
   Reset();r=Entry();test_equity=9740;Check(!FTMOOrderSend(r,result),"floating loss plus stop reserve");
   Reset();r=Entry();test_balance=test_equity=9250;Check(!FTMOOrderSend(r,result),"9200 reserve floor");
   Reset();r=Entry();Losses(3);Check(!FTMOOrderSend(r,result),"three closed losing positions");
   Reset();r=Entry();for(int i=1;i<=7;i++){td[i].id=i;td[i].kind=DEAL_TYPE_BUY;td[i].entry=DEAL_ENTRY_IN;td[i].time=MockServer()-30;}test_deals=8;
   Check(!FTMOOrderSend(r,result),"seven entries");
   Reset();r=Entry();test_lock=INVALID_HANDLE;Check(!FTMOOrderSend(r,result),"atomic busy fail closed");
   Reset();r=Entry();test_equity=8999;Check(!FTMOOrderSend(r,result),"total loss latch");
   test_equity=10000;Check(!FTMOOrderSend(r,result),"latch survives recovery");
   Reset();r=Entry();r.action=TRADE_ACTION_PENDING;Check(!FTMOOrderSend(r,result),"pending unsupported");
   Reset();r=Entry();Positions(1);r.action=TRADE_ACTION_SLTP;r.position=100;r.sl=3980;
   Check(!FTMOOrderSend(r,result),"widening SL denied");
   r.sl=3995;Check(FTMOOrderSend(r,result),"tightening SL allowed");
   Reset();r=Entry();r.position=100;test_equity=8500;
   Check(FTMOOrderSend(r,result),"closing not blocked by loss gate");
   Reset();r=Entry();td[0].profit=100000;Check(!FTMOOrderSend(r,result),"wrong initial size rejected");
   Reset();r=Entry();test_equity=9600;Check(FTMOPulse(),"pulse allows existing management");
   test_equity=10000;Check(!FTMOOrderSend(r,result),"daily stop observed with no entry signal");
   Reset();r=Entry();MockGVS(FTMOKey("REQ_"+IntegerToString(FTMODay(test_utc))),1400);
   Check(!FTMOOrderSend(r,result),"entry request reserve");
   r.position=100;Check(FTMOOrderSend(r,result),"close allowed inside reserved quota");
   Reset();r=Entry();r.position=100;MockGVS(FTMOKey("REQ_"+IntegerToString(FTMODay(test_utc))),1900);
   Check(!FTMOOrderSend(r,result),"absolute EA request ceiling");
   Reset();r=Entry();MockGVS(FTMOKey("UNCERTAIN"),1);
   Check(!FTMOOrderSend(r,result),"uncertain execution latched off");
   Reset();r=Entry();test_balance=test_equity=11000;
   for(int i=1;i<=4;i++){td[i].kind=DEAL_TYPE_BUY;td[i].entry=DEAL_ENTRY_IN;td[i].id=i;td[i].time=MockServer()-i*86400;}
   test_deals=5;Check(!FTMOOrderSend(r,result),"phase target with four opening days");
   PrintFormat("FTMO13 GUARD TESTS: %d checks, %d failures; MOCK ORDERS ONLY",checks,failures);
   return failures==0?INIT_SUCCEEDED:INIT_FAILED;
}
void OnTick(){}
