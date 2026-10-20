// V2 adds read-only price provenance benchmarks, not trading or signal logic.
#define RR05Finish RR05OriginalFinish
#include "ReadOnlyAuditBaseV3.mqh"
#undef RR05Finish
void RR05Finish()
{
 RR05OriginalFinish();
 int file=FileOpen(RR05Path("benchmarks"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(file==INVALID_HANDLE){Print("RR05_EXPORT_FAILED benchmarks");return;}
 FileWrite(file,"symbol","requested_epoch","found_epoch","open","high","low","close","tick_volume","spread","real_volume","found");
 datetime dates[]={D'2026.08.17 12:30:00',D'2026.09.16 13:30:00',D'2026.10.15 14:00:00'};
 for(int i=0;i<ArraySize(dates);i++){
   MqlRates bars[];int count=CopyRates(_Symbol,PERIOD_M1,dates[i],dates[i],bars);
   if(count==1 && bars[0].time==dates[i])FileWrite(file,_Symbol,(long)dates[i],(long)bars[0].time,
      DoubleToString(bars[0].open,8),DoubleToString(bars[0].high,8),DoubleToString(bars[0].low,8),DoubleToString(bars[0].close,8),
      bars[0].tick_volume,bars[0].spread,bars[0].real_volume,1);
   else FileWrite(file,_Symbol,(long)dates[i],0,0,0,0,0,0,0,0,0);
 }
 FileClose(file);
}
