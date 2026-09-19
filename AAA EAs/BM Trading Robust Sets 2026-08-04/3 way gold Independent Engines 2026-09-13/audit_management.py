"""Independent audit of native closed-bar SL ratchets and cash risk."""
import csv,math
from pathlib import Path
from datetime import datetime
from params import ROOT,effective

def audit(r):
    stem=f"{r['period']}-engine{r['engine']}-d{r['execution_delay_ms']}"
    with (ROOT/'Audit'/(stem+'-events.csv')).open() as f:events=list(csv.DictReader(f))
    with (ROOT/'Audit'/(stem+'-decisions.csv')).open() as f:decision_rows=list(csv.DictReader(f))
    def stamp(s):return datetime.strptime(s,'%Y.%m.%d %H:%M:%S')
    # Multiple synchronous requests can cross a clock second under execution
    # delay. Match the explicitly logged originating H1 bar, not the fill second.
    decisions={stamp(v['time']).replace(minute=0,second=0):v for v in decision_rows}
    assert len(decisions)==len(decision_rows),'Ambiguous originating decision bar'
    config=r['config'];positions={};checked=0;entries=0
    for e in events:
        if e['event']=='entry':
            pid=e['position_id'];engine=int(e['engine']);direction=int(e['dir']);names={1:'Momentum',2:'Change',3:'Breakout'}
            eq=float(e['equity_before']);requested=eq*config['InpRiskPerEnginePercent']*config['Inp'+names[engine]+'RiskWeight']/100
            assert abs(requested-float(e['requested_risk_cash']))<.0001
            volume=float(e['volume']);price=float(e['entry']);sl=float(e['sl']);risk=100*volume*abs(price-sl)
            # Native OrderCalcProfit returns deposit-currency cents (can truncate).
            assert abs(risk-float(e['risk_cash']))<.01001 and volume>=.01 and abs(volume/.01-round(volume/.01))<1e-6
            assert effective(config,engine)['InpDirection'] in (0,direction)
            positions[pid]=dict(entry=price,sl=sl,tp=float(e['tp']),direction=direction,engine=engine)
            entries+=1
        elif e['event']=='trail':
            assert e['position_id'] in positions
            p=positions[e['position_id']];row=decisions[stamp(e['decision_bar'])]
            assert stamp(row['time'])<=stamp(e['time']),'Stop update precedes its decision'
            assert stamp(row['closed_bar'])<stamp(e['decision_bar']),'Current-bar lookahead'
            direction=p['direction'];cfg=effective(config,p['engine']);rr=config['Inp'+{1:'Momentum',2:'Change',3:'Breakout'}[p['engine']]+'RR'] or config['InpRewardRisk']
            distance=abs(p['tp']-p['entry'])/rr
            assert direction*(float(row['c1'])-p['entry'])>=cfg['InpTriggerR']*distance-1e-6
            new=p['sl'];mode=cfg['InpManagement'];assert mode in (1,2,3)
            if mode in (1,3):new=max(new,p['entry']) if direction>0 else min(new,p['entry'])
            if mode in (2,3):
                candidate=float(row['c1'])-direction*cfg['InpTrailATR']*float(row[{1:'momentum_atr',2:'change_atr',3:'breakout_atr'}[p['engine']]])
                new=max(new,candidate) if direction>0 else min(new,candidate)
            new=(math.floor(new*1000+1e-9) if direction>0 else math.ceil(new*1000-1e-9))/1000
            actual=float(e['sl']);assert abs(actual-new)<.002 and direction*(actual-p['sl'])>0
            assert abs(float(e['tp'])-p['tp'])<.0001
            p['sl']=actual;checked+=1
    assert entries==r['trades']
    return dict(entries=entries,sl_ratchets=checked,cash_risk_validated=True,closed_bar_management_validated=True)
