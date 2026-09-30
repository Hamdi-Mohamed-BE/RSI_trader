#property strict
#property version "1.00"
double Cases[][27]={
 {16385,2,96,70,14,0.1,1,0.5,0.25,4,1,0.5,2,1,3,1,0,0,0,0,0,1,0,0,1,1,0.2},
 {16385,8,64,70,14,0.25,1,0.5,0.25,1,2,0.1,6,1,2,0,0,0,6,0,0,1,1,0,0,2,0.2},
 {16385,4,32,70,14,0.1,1,0.5,0.25,3,5,2,1,1.5,1.5,0,0,0,2,0,0,1,0,0,1,4,0.2},
 {16388,2,64,70,14,0.1,1,0.5,0,3,3,0.001,2,1,3,5,0,0,5,1,0,1,1,0,1,7,0.2}
};
#define OnTester OriginalOnTester
#include "SearchLogic.mqh"
#undef OnTester
string AuditTag="EURUSD-last-year-audited-91d0075703a5";
#include "ExportAudit.mqh"
