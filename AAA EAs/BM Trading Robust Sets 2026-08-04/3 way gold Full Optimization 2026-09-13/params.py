from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent/'3 way gold Raw Research 2026-09-13'
DEFAULT=dict(InpEngine=0,InpRiskPerEnginePercent=.30,InpStopATR=2.,InpRewardRisk=2.,InpMagicBase=91330000,
 InpDeviationPoints=30,InpDirection=0,InpPullbackEMA=20,InpTrendFastEMA=50,InpTrendSlowEMA=200,
 InpADXPeriod=14,InpADXMin=25.,InpChangeFastEMA=9,InpChangeSlowEMA=21,InpRSIPeriod=14,InpRSIThreshold=50.,
 InpBreakoutBars=20,InpExpansionATR=1.5,InpRisingATR=True,InpATRPeriod=14,InpManagement=0,InpTrailATR=2.,InpTriggerR=1.,
 InpMomentumRiskWeight=1.,InpChangeRiskWeight=1.,InpBreakoutRiskWeight=1.,InpMomentumStopATR=0.,InpChangeStopATR=0.,InpBreakoutStopATR=0.,
 InpMomentumRR=0.,InpChangeRR=0.,InpBreakoutRR=0.,InpExportHistory=True)
SPACE=dict(InpDirection=[0,1,-1],InpATRPeriod=[10,14,20],InpStopATR=[1.,1.5,2.,2.5,3.],InpRewardRisk=[.5,.75,1.,1.5,2.,3.],
 InpManagement=[0,1,2,3],InpTrailATR=[1.,1.5,2.,3.],InpTriggerR=[.75,1.,1.5],
 InpPullbackEMA=[10,20,30],InpTrendFastEMA=[30,50,75],InpTrendSlowEMA=[100,150,200,300],InpADXPeriod=[10,14,20],InpADXMin=[15.,20.,25.,30.,35.],
 InpChangeFastEMA=[5,9,13],InpChangeSlowEMA=[21,34,55],InpRSIPeriod=[7,14,21],InpRSIThreshold=[50.,55.,60.],
 InpBreakoutBars=[10,20,30,55],InpExpansionATR=[1.,1.25,1.5,2.],InpRisingATR=[False,True])
COMMON=['InpDirection','InpATRPeriod','InpStopATR','InpRewardRisk','InpManagement','InpTrailATR','InpTriggerR']
ENGINE={1:['InpPullbackEMA','InpTrendFastEMA','InpTrendSlowEMA','InpADXPeriod','InpADXMin'],
 2:['InpChangeFastEMA','InpChangeSlowEMA','InpRSIPeriod','InpRSIThreshold'],3:['InpBreakoutBars','InpExpansionATR','InpRisingATR']}
WINDOWS={'6m':('2026.03.05','2026.09.05'),'1y':('2025.09.05','2026.09.05'),'3y':('2023.09.05','2026.09.05'),
 '5y':('2021.09.05','2026.09.05'),'2019-2026':('2019.01.01','2026.09.05')}
TRAIN=('2021.09.05','2024.09.05');VALID=('2024.09.05','2025.09.05');LOCKED=WINDOWS['1y']
def normalize(c):return {k:type(v)(c.get(k,v)) for k,v in DEFAULT.items()}
def ident(c):return hashlib.sha256(json.dumps(normalize(c),sort_keys=True).encode()).hexdigest()[:12]
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
