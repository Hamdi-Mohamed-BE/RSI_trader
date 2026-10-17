#ifndef CALYX_ORB_COMMENTS_MQH
#define CALYX_ORB_COMMENTS_MQH

// Presentation only. Never use these strings for ownership, sizing or signals.
string CalyxORBRangeLabel(const int minutes)
{
   if(minutes>0 && minutes%60==0) return IntegerToString(minutes/60)+"H";
   return IntegerToString(minutes)+"m";
}

string CalyxORBSignalLabel(const ENUM_TIMEFRAMES timeframe)
{
   int minutes=PeriodSeconds(timeframe)/60;
   if(minutes>0 && minutes%60==0) return "H"+IntegerToString(minutes/60);
   return "M"+IntegerToString(minutes);
}

void CalyxORBAppendTag(string &comment,const string tag,const string compact)
{
   if(tag=="") return;
   if(StringLen(comment)+1+StringLen(tag)<=31) comment+=" "+tag;
   else if(compact!="" && StringLen(comment)+1+StringLen(compact)<=31) comment+=" "+compact;
}

string CalyxORBTradeComment(const int range_minutes,const ENUM_TIMEFRAMES signal_timeframe,
                           const bool utc_session,const int hour,const int minute,
                           const string variant,const bool above_average_volume,
                           const bool profile_filter)
{
   string session=(utc_session
      ? (minute==0 ? StringFormat("%02dUTC",hour) : StringFormat("%02d:%02dUTC",hour,minute))
      : StringFormat("NY%02d:%02d",hour,minute));
   string comment="ORB "+CalyxORBRangeLabel(range_minutes)+" "+CalyxORBSignalLabel(signal_timeframe)+" "+session;
   // Keep the identity first and fit the usual MT5/broker 31-character budget.
   comment=StringSubstr(comment,0,31);
   if(above_average_volume) CalyxORBAppendTag(comment,"VolConf","VC");
   CalyxORBAppendTag(comment,variant,"RT");
   if(profile_filter) CalyxORBAppendTag(comment,"VP","");
   return comment;
}

#endif
