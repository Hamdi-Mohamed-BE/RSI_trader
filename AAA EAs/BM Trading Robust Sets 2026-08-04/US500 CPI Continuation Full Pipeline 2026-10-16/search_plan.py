"""Small preregistered search; no OOS input or risk/execution-quality tuning."""
import hashlib, json, math, statistics
BASE = dict(hold_minutes=15, target_r=1.5, entry_window_minutes=5, impulse_mult=1.0, close_fraction=0.25)
STAGES = [('target','target_r',[0.5,1.0,1.5,2.0]), ('hold','hold_minutes',[5,15,30]), ('impulse','impulse_mult',[0.75,1.0,1.25])]
PLAN = dict(baseline=BASE, stages=STAGES, beam_width=1,
            neighbours={'target_r':[-0.25,0.25], 'hold_minutes':[-5,5], 'impulse_mult':[-0.25,0.25]},
            bounds={'target_r':[0.25,4], 'hold_minutes':[2,45], 'impulse_mult':[0.5,2]},
            centres='Greedy development-only final centre and unchanged baseline; maximum two validation finalists',
            max_main_unique_configurations=20,
            selection='Stable development-neighbour median plus predeclared validation score; no selection on final two years',
            raw_gate_end='2023-10-16',
            walk_forward=dict(grid_target_r=[0.5,1.5,2.0],grid_hold_minutes=[5,15,30],fixed_other_fields=BASE,
                 folds=[dict(train_start='2020-01-01',train_end='2022-01-01',test_start='2022-01-01',test_end='2023-01-01'),
                        dict(train_start='2020-01-01',train_end='2023-01-01',test_start='2023-01-01',test_end='2023-10-16')],
                 selection='Each fold uses ONLY its training interval; diagnostic tests never select final parameters'),
            execution_scenarios=[dict(delay_ms=500,model=4),dict(delay_ms=1000,model=4),dict(delay_ms=150,model=0)])

def key(case):
    return hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()

def complexity(case):
    return sum(abs(float(case[k])-float(BASE[k]))/max(abs(float(BASE[k])),1e-6) for k in BASE)

def score(row, minimum=30):
    m=row['metrics']; n=int(m['trades']); net=float(m['net'])
    if not n:
        return -100.0
    pf=m['pf'] if m['pf'] is not None else (3.0 if net>0 else 0.0)
    years=m.get('yearly',[])
    positive=sum(y['net']>0 for y in years)/max(1,len(years))
    wins=m['win_rate_pct']/100*n
    shrunk_win=(wins+10)/(n+20)
    return 2*(min(float(pf),3)-1)+0.5*positive+0.3*shrunk_win+0.5*min(n/minimum,1)-0.04*m['equity_dd']-(2 if n<minimum else 0)-(3 if net<=0 else 0)

def rank(rows, minimum=30):
    return sorted(rows,key=lambda r:(-score(r,minimum),complexity(r['parameters']),key(r['parameters'])))

def neighbours(case):
    out=[dict(case)]
    for name, steps in PLAN['neighbours'].items():
        for step in steps:
            value=round(case[name]+step,5)
            lo,hi=PLAN['bounds'][name]
            if lo<=value<=hi:
                out.append(dict(case,**{name:int(value) if name=='hold_minutes' else value}))
    return list({key(x):x for x in out}.values())
