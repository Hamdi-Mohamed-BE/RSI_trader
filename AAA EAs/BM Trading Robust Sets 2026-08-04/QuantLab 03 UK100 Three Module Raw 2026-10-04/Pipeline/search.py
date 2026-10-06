"""Preregistered bounded full staged search; no recent/holdout selection."""
import itertools,json
import batch,runner as n
R=n.R
def one(k,vs):return [{k:v} for v in vs]
rrs=[.5,.75,1,1.25,1.5,2,2.5,3,4,5,6]
STAGES=[
('01-timeframe',one('InpSignalTimeframe',[1,3,5,15,30,16385,16388,16408])),
('02-entry',one('InpEntryMode',[0,1,2,3])+[{'InpEntryMode':mode,'InpEntryOffsetATR':v} for mode in [2,3] for v in [.1,.5]]+one('InpDropATR',[2,3,4])+one('InpOversoldRSI',[5,10,20])+one('InpDropLookback',[12,24,48])+one('InpMondayDipATR',[.25,.5,1])+one('InpPullbackEMA',[10,20,30])+one('InpTrendEMA',[30,50,100])+one('InpSlowEMA',[100,200,300])),
('03-stop',one('InpStopMode',[0,1,2])+[{'InpStopMode':0,'InpStopATR':a} for a in [.5,.75,1,1.5,2,3,4]]+[{'InpStopMode':3,'InpStopPercent':a} for a in [.25,.5,1]]+[{'InpStopMode':4,'InpStopPriceUnits':a} for a in [25,50,100]]),
('04-management',one('InpManagement',range(8))+[{'InpManagement':1,'InpTrailStartR':v} for v in [.5,1,1.5]]+[{'InpManagement':2,'InpTrailATR':v} for v in [.5,1,2]]+[{'InpManagement':6,'InpTrailATR':v} for v in [1,2,3]]),
('05-exit',[{'InpExitMode':0,'InpDropTargetR':v,'InpMondayTargetR':v,'InpTrendTargetR':v} for v in rrs]+[{'InpExitMode':1,'InpManagement':2},{'InpExitMode':2},{'InpExitMode':3},{'InpExitMode':4,'InpManagement':2,'InpDropTargetR':3,'InpMondayTargetR':3,'InpTrendTargetR':3}]),
('06-session',one('InpSessionMode',range(7))+one('InpExcludeDays',[0,1,2,3])),
('07-direction',one('InpDirection',[0,1,-1])),
('08-filter',[{'InpFilter':0},{'InpFilter':2},{'InpFilter':4},{'InpFilter':5},{'InpFilter':6}]+[{'InpFilter':f,'InpADXMin':v} for f in [1,3] for v in [15,20,25,30]]+one('InpMaxSpreadATR',[.04,.08,.16])),
('09-trade-management',one('InpMaxHoldingHours',[6,12,24,48,96])+one('InpMaxPositions',[1,2,3])+one('InpPerModuleDay',[1,2,3])+[{'InpLossesBeforePause':loss,'InpPauseHours':hours} for loss,hours in [(3,24),(3,48),(5,24),(10000,24)]]+[{'InpEnableDrop':a,'InpEnableMonday':b,'InpEnableTrend':c} for a,b,c in itertools.product([True,False],repeat=3) if a or b or c])]
def score(r):
    m=r['net_metrics'];pf=m['net_pf'] or 0;dd=r['export_stats']['equity_dd_pct'];ret=m['return_pct']
    return (m['trades']>=30,min(pf,5)-.006*dd+.03*ret/max(dd,1),m['trades'])
def valid(v):return int(v['InpPullbackEMA'])<int(v['InpTrendEMA'])<int(v['InpSlowEMA'])
def main():
    plan=dict(version='2026-10-04',exploratory_after_raw_failure=True,stages=[dict(stage=k,changes=v) for k,v in STAGES],models=dict(screen=1,confirmation=4),development=n.PERIODS['DEV'],validation=n.PERIODS['VAL'],reserved_holdout=n.PERIODS['HOLD'],recent_is_previously_viewed=True,carry=3,ranking='minimum30 development positions; PF -0.006*DD +0.03*return/max(DD,1); no recent/holdout rankings',omissions={'news_blackout':'No point-in-time multi-year calendar supplied; not invented','same_close_vs_next_open':'Same closed-bar first executable quote; duplicate, not counted twice','no_stop':'Unbounded risk cannot support cash-risk sizing','silver_optimisation':'Frozen transfer only'},neighbours='3x3 stopATR +/-20% and targetR +/-20% around development finalists; >=2/3 positive, PF>1 and >=30positions')
    plan=json.loads(json.dumps(plan))
    pp=R/'SEARCH PLAN.json'
    if pp.exists():assert json.loads(pp.read_text())==plan
    else:n.save(pp,plan)
    parents=[n.norm({})];allrows={};history=[]
    for stage,changes in STAGES:
        configs={}
        for parent in parents:
            for delta in [{}]+changes:
                v=n.norm({**parent,**delta})
                if valid(v):configs[n.key(v)]=v
        print('START '+stage+' '+str(len(configs))+' native configurations',flush=True)
        rows=batch.run(list(configs.values()),stage)
        for row in rows:allrows[row['id']]=row
        chosen=sorted(rows,key=score,reverse=True)[:3];parents=[r['inputs'] for r in chosen]
        history.append(dict(stage=stage,cases=len(rows),selected=[dict(id=r['id'],inputs=r['inputs'],net_metrics=r['net_metrics'],equity_dd_pct=r['export_stats']['equity_dd_pct']) for r in chosen]))
        n.save(R/'SEARCH RESULTS.json',list(allrows.values()));n.save(R/'SEARCH HISTORY.json',history)
        print('DONE '+stage+' selected '+json.dumps([dict(id=r['id'],pf=r['net_metrics']['net_pf'],return_pct=r['net_metrics']['return_pct'],trades=r['net_metrics']['trades']) for r in chosen]),flush=True)
    neighbours=[]
    for parent in parents:
        for a,b in itertools.product([.8,1,1.2],repeat=2):
            v={**parent,'InpStopATR':float(parent['InpStopATR'])*a}
            for k in ['InpDropTargetR','InpMondayTargetR','InpTrendTargetR']:v[k]=float(parent[k])*b
            neighbours.append(n.norm(v))
    configs={n.key(v):v for v in neighbours};rows=batch.run(list(configs.values()),'10-neighbours')
    for row in rows:allrows[row['id']]=row
    n.save(R/'SEARCH RESULTS.json',list(allrows.values()))
    finalists=[]
    for parent in parents:
        group=[r for r in rows if all(r['inputs'][k]==parent[k] for k in parent if k not in ['InpStopATR','InpDropTargetR','InpMondayTargetR','InpTrendTargetR'])]
        positive=sum(r['net_metrics']['trades']>=30 and r['net_metrics']['net_profit']>0 and (r['net_metrics']['net_pf'] or 0)>1 for r in group)
        finalists.append(dict(inputs=parent,plateau_rows=len(group),positive_neighbours=positive,plateau_pass=positive>=2*len(group)/3))
    n.save(R/'FINALISTS.json',finalists)
    print('Development search finished: '+str(len(allrows))+' unique configurations. Validation not yet used.',flush=True)
if __name__=='__main__':main()
