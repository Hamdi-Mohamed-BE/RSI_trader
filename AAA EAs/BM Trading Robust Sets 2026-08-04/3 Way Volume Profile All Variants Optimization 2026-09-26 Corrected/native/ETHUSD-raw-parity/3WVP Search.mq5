#property strict
#property version "1.00"
double Cases[][27]={
 {15,2,64,70,14,0.1,1,0.5,0.25,0,0,2,0,1,1.5,0,0,0,0,0,0,1,1,0,1,1,0.2},
 {15,2,64,70,14,0.1,1,0.5,0.25,0,0,2,0,1,1.5,0,0,0,0,0,0,1,1,0,1,2,0.2},
 {15,2,64,70,14,0.1,1,0.5,0.25,0,0,2,0,1,1.5,0,0,0,0,0,0,1,1,0,1,4,0.2},
 {15,2,64,70,14,0.1,1,0.5,0.25,0,0,2,0,1,1.5,0,0,0,0,0,0,1,1,0,1,7,0.2}
};
#define OnTester OriginalOnTester
#include "SearchLogic.mqh"
#undef OnTester
string AuditTag="ETHUSD-raw-parity-bc9d2f38bb74";
#include "ExportAudit.mqh"
