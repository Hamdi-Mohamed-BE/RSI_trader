#property strict

int OnInit()
{
   for(int day=0;day<7;day++)
   {
      for(uint index=0;index<16;index++)
      {
         datetime from=0,to=0;
         if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)day,index,from,to)) break;
         PrintFormat("SESSION_PROBE symbol=%s day=%d index=%d from=%s to=%s",
                     _Symbol,day,index,TimeToString(from,TIME_MINUTES),TimeToString(to,TIME_MINUTES));
      }
   }
   return INIT_FAILED;
}

void OnTick() {}
