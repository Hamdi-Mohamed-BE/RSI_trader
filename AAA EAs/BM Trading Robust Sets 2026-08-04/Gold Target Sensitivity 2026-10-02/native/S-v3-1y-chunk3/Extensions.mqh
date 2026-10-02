#include <Trade/Trade.mqh>
input int InpCase=0;
input int InpCase2=-1;
input int InpCase3=-1;
input bool InpControl=false;
input bool InpRetryClosed=false;
input double InpFixedRiskUSD=100;
input uint InpSeed=301;
input datetime InpTradeFrom=D'2021.10.01';
input string InpTag="gold-targets";
int entryFails=0,modifyFails=0,closeFails=0,noChanges=0;
bool Successful(uint code){return code==TRADE_RETCODE_DONE||code==TRADE_RETCODE_PLACED||code==TRADE_RETCODE_DONE_PARTIAL;}
class AuditTrade:public CTrade{
public:
 bool Buy(const double volume,const string symbol=NULL,double price=0,const double sl=0,const double tp=0,const string comment=""){
  bool ok=CTrade::Buy(volume,symbol,price,sl,tp,comment);if(!Successful(ResultRetcode())){entryFails++;PrintFormat("TARGET_ENTRY_FAIL %u",ResultRetcode());}return ok;
 }
 bool Sell(const double volume,const string symbol=NULL,double price=0,const double sl=0,const double tp=0,const string comment=""){
  bool ok=CTrade::Sell(volume,symbol,price,sl,tp,comment);if(!Successful(ResultRetcode())){entryFails++;PrintFormat("TARGET_ENTRY_FAIL %u",ResultRetcode());}return ok;
 }
 bool PositionModify(const ulong ticket,const double sl,const double tp){
  bool ok=CTrade::PositionModify(ticket,sl,tp);uint c=ResultRetcode();if(c==TRADE_RETCODE_NO_CHANGES)noChanges++;else if(!Successful(c)){modifyFails++;PrintFormat("TARGET_MODIFY_FAIL %u",c);}return ok;
 }
 bool PositionClose(const ulong ticket,const ulong deviation=ULONG_MAX){
  bool ok=CTrade::PositionClose(ticket,deviation);if(!Successful(ResultRetcode())){closeFails++;PrintFormat("TARGET_CLOSE_FAIL %u",ResultRetcode());}return ok;
 }
};
