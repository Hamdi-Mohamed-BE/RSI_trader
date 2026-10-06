#ifndef CALYX_NEWS_PULSE_PLACEMENT_MQH
#define CALYX_NEWS_PULSE_PLACEMENT_MQH

// Pure geometry, also exercised by the isolated native-MT5 regression harness.
// Price distances are symbol units, not account risk. Never reuse the old SL
// when a crossed pending level is replaced by a market entry.
double NP_RoundPrice(const double value,const double quantum,const bool up)
{
   return (up ? MathCeil(value/quantum-1e-9) : MathFloor(value/quantum+1e-9))*quantum;
}
bool NP_PlanSide(const bool buy,const double level,const double bid,const double ask,
                 const double stop_distance,const double tp_r,const double min_gap,
                 const double quantum,const bool fallback,double &entry,double &sl,
                 double &tp,bool &market)
{
   if(level<=0 || bid<=0 || ask<bid || stop_distance<=0 || quantum<=0) return false;
   market=(buy ? ask>=level : bid<=level);
   if(market && !fallback) return false;
   const double gap=MathMax(0.0,min_gap)+quantum;
   entry=market ? (buy ? ask : bid) :
      NP_RoundPrice(buy ? MathMax(level,ask+gap) : MathMin(level,bid-gap),quantum,buy);
   sl=NP_RoundPrice(buy ? entry-MathMax(stop_distance,gap) : entry+MathMax(stop_distance,gap),quantum,!buy);
   if(market) sl=NP_RoundPrice(buy ? MathMin(sl,bid-gap) : MathMax(sl,ask+gap),quantum,!buy);
   const double distance=MathAbs(entry-sl);
   tp=0;
   if(tp_r>0) tp=NP_RoundPrice(buy ? entry+MathMax(tp_r*distance,gap) :
                                     entry-MathMax(tp_r*distance,gap),quantum,buy);
   return sl>0 && distance>0 && (!buy || sl<entry) && (buy || sl>entry) && tp>=0;
}
#endif
