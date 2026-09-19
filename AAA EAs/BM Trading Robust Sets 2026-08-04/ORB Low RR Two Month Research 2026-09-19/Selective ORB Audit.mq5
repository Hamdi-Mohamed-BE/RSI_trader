#define OnInit CalyxBaseInit
#define OnDeinit CalyxBaseDeinit
#define OnTick CalyxBaseTick
#define OnTimer CalyxBaseTimer
#include "..\US100 Selective ORB Research 2026-08-21\EA\US100 Selective ORB Retest EA.mq5"
#undef OnInit
#undef OnDeinit
#undef OnTick
#undef OnTimer
#include "TrialAudit.mqh"

int OnInit()
  {
   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   int result=CalyxBaseInit();
   if(result!=INIT_SUCCEEDED) return result;
   return TrialAuditInit();
  }
void OnTick() { TrialAuditObserve(); CalyxBaseTick(); TrialAuditObserve(); }
void OnTimer() { TrialAuditObserve(); CalyxBaseTimer(); TrialAuditObserve(); }
void OnDeinit(const int reason) { TrialAuditObserve(); TrialAuditFinish(); CalyxBaseDeinit(reason); }
