#define OnInit StudyBaseOnInit
#define OnTick StudyBaseOnTick
#include "..\AAA Final EAs\Calyx DMC Fresh Reaction EA\Calyx DMC Fresh Reaction EA.mq5"
#undef OnInit
#undef OnTick
#include "StudyAudit.mqh"
int OnInit(){if(!StudyGuard())return INIT_FAILED;int code=StudyBaseOnInit();if(code!=INIT_SUCCEEDED)return code;return StudyInit();}
void OnTick(){StudyObserve();StudyBaseOnTick();StudyObserve();}
void OnDeinit(const int reason){StudyFinish();}
