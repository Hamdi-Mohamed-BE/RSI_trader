#property strict
#property version "1.00"
double Cases[][27]={
 {30,2,64,70,14,0.1,1,0.5,0.25,2,0,2,2,2,1.5,0,0,0,0,0,0,1,1,0,0,1,0.2},
 {16388,2,64,70,14,0.1,1,0.5,0.25,3,0,2,2,1.5,2,0,0,0,3,0,0,1,1,0,1,2,0.2},
 {30,2.5,64,70,14,0.25,1,0.5,0.25,4,2,0.2,1,0.5,1.5,0,0,0,5,0,0,1,0,0,1,4,0.2},
 {30,2,64,70,14,0.1,1,1,0.25,3,0,2,2,2,1.5,0,0,0,6,0,0,1,1,0,1,7,0.2}
};
#define OnTester OriginalOnTester
#include "SearchLogic.mqh"
#undef OnTester
string AuditTag="GBPJPY-last-year-audited-2c63b875d1b6";
#include "ExportAudit.mqh"
