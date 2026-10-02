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

#define AuditTrade CTrade
