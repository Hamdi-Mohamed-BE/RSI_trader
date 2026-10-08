"""Declared before optimisation; all candidate selection ends before 2024."""
from build_engine import RAW,FIELDS
STAGES=['anchor','timeframe','ema','stop','target','trail','breakeven','holding','quality','direction','adaptive','dynamic']
def variants(stage):
 if stage=='anchor':return [dict(ResearchAnchor=x) for x in range(8)]
 if stage=='timeframe':return [dict(InpSignalTimeframe=x) for x in [1,3,5,10,15,30]]
 if stage=='ema':return [dict(InpEMAPeriod=x) for x in [8,12,20,34,50]]
 if stage=='stop':return ([dict(InpStopMode=2,InpInitialStopPercent=x) for x in [.2,.3,.4,.6,.8,1.0]]+
  [dict(InpStopMode=0,InpInitialStopATR=x) for x in [2,3,4,6]]+
  [dict(InpStopMode=1,InpSignalStopBufferATR=x) for x in [.1,.25,.5]])
 if stage=='target':return [dict(InpUseFixedTarget=0,InpUseAdaptiveRR=0)]+[dict(InpUseFixedTarget=1,InpUseAdaptiveRR=0,InpRewardRisk=x) for x in [.5,.6,.75,1,1.5,2,3,4]]
 if stage=='trail':return [dict(InpUseATRTrailing=0,InpUseMATrailing=0)]+[dict(InpUseATRTrailing=1,InpUseMATrailing=0,InpTrailingATR=x,InpTrailStartR=t) for x in [2,4,6,8] for t in [.5,1]]+[dict(InpUseATRTrailing=0,InpUseMATrailing=1,InpTrailMAPeriod=p,InpTrailMAStartR=.5) for p in [50,100,200]]
 if stage=='breakeven':return [dict(InpUseBreakEven=0)]+[dict(InpUseBreakEven=1,InpBreakEvenTriggerR=x,InpBreakEvenLockR=y) for x,y in [(.5,0),(1,0),(1,.25),(1.5,.5)]]
 if stage=='holding':return ([dict(InpCloseAtSessionEnd=0,InpMaximumHoldingMinutes=0,ResearchBerlinClose=0)]+
  [dict(InpCloseAtSessionEnd=0,InpMaximumHoldingMinutes=x,ResearchBerlinClose=0) for x in [30,60,120,240,360]]+
  [dict(InpCloseAtSessionEnd=1,InpMaximumHoldingMinutes=0,ResearchBerlinClose=x) for x in [0,1]])
 if stage=='quality':
  cleared=dict(InpRequireDIAgreement=0,ResearchADXMinimum=0,ResearchADXMaximum=0,ResearchRequireBodyDirection=0,
   InpRequireEMASlope=0,InpMinimumBodyATR=0,InpMinimumBodyFraction=0,InpMinimumEMADistanceATR=0,InpMaximumEMADistanceATR=0,InpRelativeVolumePeriod=0,InpMinimumRelativeVolume=0)
  changes=[{},dict(InpRequireDIAgreement=1),dict(ResearchRequireBodyDirection=1),dict(InpRequireEMASlope=1)]
  changes +=[dict(ResearchADXMinimum=x) for x in [15,20,25]]+[dict(InpRequireDIAgreement=1,ResearchADXMinimum=x) for x in [15,20,25]]
  changes +=[dict(InpMinimumBodyFraction=x) for x in [.5,.65]]+[dict(InpMinimumBodyATR=x) for x in [.3,.5,1]]
  changes +=[dict(InpMinimumEMADistanceATR=x) for x in [.1,.25]]+[dict(InpMaximumEMADistanceATR=2)]
  changes +=[dict(InpRelativeVolumePeriod=20,InpMinimumRelativeVolume=x) for x in [1,1.2,1.5]]
  return [cleared|x for x in changes]
 if stage=='direction':return [dict(InpAllowLong=a,InpAllowShort=b,ResearchSkipWeekday=x) for a,b in [(1,1),(1,0),(0,1)] for x in [0,1,2,3]]
 if stage=='adaptive':return [dict(InpUseAdaptiveRR=0)]+[dict(InpUseFixedTarget=1,InpUseAdaptiveRR=1,InpRewardRisk=x,InpAdaptiveStrongRR=y,InpAdaptiveStrongBodyATR=1) for x,y in [(.5,1),(1,2),(1.5,3),(2,3)]]
 if stage=='dynamic':return [dict(InpUseDynamicTrailingSL=0)]+[dict(InpUseDynamicTrailingSL=1,InpDynamicTriggerFraction=x,InpDynamicLockFraction=y) for x,y in [(.5,.2),(.75,.25)]]
 raise KeyError(stage)
def freeze():
 return dict(schema=1,stages={s:variants(s) for s in STAGES},baseline=RAW,fields=FIELDS,
  beam_width=2,one_factor_at_a_time=True,minimum_development_trades=60,preferred_trades=100,
  preferred_win_rate=50,preferred_pf=1.15,selection_target='balanced PF, sample size, win rate/streak and drawdown; stable parameter neighbourhood, not maximum return',
  neighbourhood='Stop distance × [0.8,1,1.2] and TP RR (if used) or trailing distance × [0.8,1,1.2]; one-factor axis neighbours, including center',
  internal_validation='2023 only; at most three development finalists, plus unchanged raw control',
  final_holdout='2024-01-01 onward, evaluated only after FROZEN.json exists; no candidate reselection after seeing holdout results',
  previously_viewed_baseline_future=True,markov_overlay='OFF throughout; not added to this study',
  execution='original retry, volume ceiling/minimum and 1% maximum allocation policies retained',
  research_only=True)
