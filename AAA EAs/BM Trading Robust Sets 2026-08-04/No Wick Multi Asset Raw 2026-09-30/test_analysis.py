from analyse import trade_statistics,raw_gate

def t(p,day):
    return dict(net_profit=p,commission=-1,swap=0,open_time=f'2026-01-{day:02d}T01:00:00',close_time=f'2026-01-{day:02d}T02:00:00')

def test_cost_aware_metrics_and_streaks():
    x=trade_statistics([t(v,i+1) for i,v in enumerate([10,10,-10,-10,-10,0,10])],'2026.01.01','2026.02.01','EURUSD')
    assert x['net_profit_factor']==1
    assert x['wins']==3 and x['losses']==3 and x['flats']==1
    assert x['longest_win_streak']==2 and x['longest_loss_streak']==3
    assert x['avg_win_streak']==1.5 and x['avg_loss_streak']==3
    assert x['net_profit']==0 and x['commission']==-7

def test_btc_daily_denominator_includes_weekends():
    rows=[t(10,1),t(-5,2)]
    a=trade_statistics(rows,'2026.01.01','2026.02.01','BTCUSD')
    b=trade_statistics(rows,'2026.01.01','2026.02.01','EURUSD')
    assert a['trades_per_day']==2/31 and a['trades_per_day']<b['trades_per_day']

def test_zero_trades_not_perfect_win_rate():
    x=trade_statistics([],'2026.01.01','2026.02.01','EURUSD')
    assert x['net_profit_factor'] is None and x['net_win_rate_pct']==0 and x['nominal_wilson95_pct'] is None

def test_gate_requires_both_controls_and_windows():
    assert raw_gate('EURUSD','S15',{},dict(min_pf=1.15,min_trades=30))['status']=='INCOMPLETE'
    lookup={}
    for p in ('3y','5y'):
        lookup[('EURUSD','S15',p)]={'net':dict(net_profit=100,net_profit_factor=1.2,trades=50)}
        lookup[('EURUSD','C15',p)]={'net':dict(net_profit=90,net_profit_factor=1.1,trades=50)}
    assert raw_gate('EURUSD','S15',lookup,dict(min_pf=1.15,min_trades=30))['status']=='RAW_PASS_REVIEW_REQUIRED'
    lookup[('EURUSD','C15','5y')]['net']['net_profit']=101
    assert raw_gate('EURUSD','S15',lookup,dict(min_pf=1.15,min_trades=30))['status']=='FAIL'

def test_tick_note_parser_retains_original_matches():
    import re
    from run_study import tick_notes
    sample='ordinary\r\n00\tREAL TICKS BEGIN from 2026.01.01\r\n01 tick generation done\n02 ticks discarded\n03 real ticks absent\nordinary\n01 tick generation done'
    old=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks absent|ticks discarded|tick generation)[^\r\n]*',sample,re.I)))[:30]
    assert tick_notes(sample)==old
