#property strict
#property version "1.00"
double Cases[][27]={
 {16388,3,64,60,14,0.1,1,0.5,0.25,4,0,2,7,1,1.5,0,0,0,0,2,0,1,1,0,1,1,0.2},
 {16388,8,64,70,14,0.25,1,0.5,0.25,1,3,500,5,1,1.5,0,0,0,6,0,0,2,1,0,1,2,0.2},
 {16385,2,64,70,14,0.1,0.5,0.5,0.25,2,1,3,2,1,3,1,0,0,2,1,0,1,1,0,1,4,0.2},
 {16388,8,64,70,14,0.1,0.5,0.5,0.25,1,1,0.75,1,1,1.5,0,0,0,0,0,0,1,0,0,1,7,0.2}
};
#define OnTester OriginalOnTester
#include "SearchLogic.mqh"
#undef OnTester
string AuditTag="BTCUSD-last-year-audited-5b8516b78578";
#include "ExportAudit.mqh"
