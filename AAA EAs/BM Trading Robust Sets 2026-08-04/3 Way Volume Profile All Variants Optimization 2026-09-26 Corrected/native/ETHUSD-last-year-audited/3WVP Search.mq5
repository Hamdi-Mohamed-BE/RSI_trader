#property strict
#property version "1.00"
double Cases[][27]={
 {30,2.5,64,60,14,0.1,1,0.5,0.25,2,3,25,2,1.5,2,0,0,0,5,0,0,2,1,0,1,1,0.2},
 {16385,2,96,70,14,0.1,1,0.5,0.25,3,5,2,2,2,1.5,3,0,0,0,0,2,1,1,0,1,2,0.2},
 {16385,2,32,70,14,0.1,1,0.5,0.25,0,4,2,2,2,3,1,3,0,2,0,0,2,1,0,1,4,0.2},
 {16385,6,64,70,14,0.1,1,0.5,0,3,1,1.5,2,2,2,0,0,0,4,0,3,1,1,0,1,7,0.2}
};
#define OnTester OriginalOnTester
#include "SearchLogic.mqh"
#undef OnTester
string AuditTag="ETHUSD-last-year-audited-70598240bb19";
#include "ExportAudit.mqh"
