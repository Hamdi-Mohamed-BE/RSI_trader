#define OnInit StudyBaseOnInit
#define OnTick StudyBaseOnTick
#define OnTimer StudyBaseOnTimer
#define OnDeinit StudyBaseOnDeinit
#include "..\Month End Institutional Flow Research 2026-09-06\EA\Calyx Month End Flow EA.mq5"
#undef OnInit
#undef OnTick
#undef OnTimer
#undef OnDeinit
#include "StudyAudit.mqh"
int OnInit(){if(!StudyGuard())return INIT_FAILED;int code=StudyBaseOnInit();if(code!=INIT_SUCCEEDED)return code;return StudyInit();}
void OnTick(){StudyObserve();StudyBaseOnTick();StudyObserve();}
void OnTimer(){StudyObserve();StudyBaseOnTimer();StudyObserve();}
void OnDeinit(const int reason){StudyFinish();StudyBaseOnDeinit(reason);}
