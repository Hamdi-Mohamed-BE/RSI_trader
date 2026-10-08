#define OnInit RR05BaseOnInit
#define OnDeinit RR05BaseOnDeinit
#define OnTick RR05BaseOnTick
#define OnTimer RR05BaseOnTimer
input double InpRR05ModuleTarget=0;
#include "SourceCopy.mq5"
#undef OnInit
#undef OnDeinit
#undef OnTick
#undef OnTimer
#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/ORB and Range Breakout RR05 Comparison 2026-10-08/ReadOnlyAudit.mqh"
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;int v=RR05BaseOnInit();if(v!=INIT_SUCCEEDED)return v;if(!RR05AuditInit())return INIT_FAILED;RR05Observe();return INIT_SUCCEEDED;}
void OnTick(){RR05Observe();RR05BaseOnTick();RR05Observe();}
void OnDeinit(const int reason){RR05Observe();RR05BaseOnDeinit(reason);RR05Finish();}
