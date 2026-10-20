#property strict
#define OnDeinit Top5PackageOnDeinit
#include "PublicWrapperCopy.mq5"
#undef OnDeinit
#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Top5 vs Prop Ready 2026-10-17/native/ReadOnlyAudit.mqh"
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;int code=Top5PackageOnInit();if(code!=INIT_SUCCEEDED)return code;if(!RR05AuditInit())return INIT_FAILED;RR05Observe();return INIT_SUCCEEDED;}
void OnTick(){RR05Observe();Top5PackageOnTick();RR05Observe();}
void OnTimer(){RR05Observe();Top5PackageOnTimer();RR05Observe();}
void OnDeinit(const int reason){RR05Observe();Top5PackageOnDeinit(reason);RR05Finish();}
