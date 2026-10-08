"""Frozen, finite research grid. No values depend on validation or final OOS."""
FIELDS='mode tf entry offset stop sl rr trail arm dist flat start end direction filter threshold day maxday hold noise atr mean adx orminutes'.split()
RAW={
 'vault':dict(zip(FIELDS,[1,30,0,0,0,75,40/75,0,1,1,1430,1000,1430,0,0,20,0,3,0,.3,14,15,20,15])),
 'overnight':dict(zip(FIELDS,[3,15,0,0,1,.3,3,0,1,1,1430,845,1430,2,9,20,0,1,0,.3,14,15,20,15]))}
STAGES=['timeframe','entry','stop','stop_management','exit','session','direction','filters','management','logic']
def variants(stage,bot):
    if stage=='timeframe':return [dict(tf=x) for x in ([1,3,5,15,30,60,240] if bot=='vault' else [1,3,5,15,30,60])]
    if stage=='entry':return [dict(entry=0),dict(entry=1)]+[dict(entry=e,offset=x) for e in [2,3] for x in [.1,.3]]+[dict(entry=4,offset=x) for x in [2,5,10]]
    if stage=='stop':return ([dict(stop=0,sl=x) for x in [40,75,100,150]]+[dict(stop=1,sl=x) for x in [.15,.3,.5]]+
       [dict(stop=2,sl=x) for x in [.5,.75,1,1.5,2,3,4]]+[dict(stop=3,sl=x) for x in [.25,.5]]+[dict(stop=x,sl=1) for x in [4,5,6]])
    if stage=='stop_management':return ([dict(trail=0)]+[dict(trail=1,arm=x) for x in [.5,1,1.5]]+
       [dict(trail=2,arm=1,dist=x) for x in [1,2,3]]+[dict(trail=3,arm=1,dist=x) for x in [.1,.25]]+
       [dict(trail=x,arm=1,dist=2) for x in [4,5,6,7,8,9]])
    if stage=='exit':return [dict(rr=x,hold=0) for x in [0,.5,.75,1,1.25,1.5,2,2.5,3,4,5,6]]+[dict(hold=x) for x in [4,8,16]]
    if stage=='session':return [dict(start=a,end=b) for a,b in ([(0,300),(200,900),(700,1100),(845,1200),(1000,1430),(1100,1430),(0,1430)] if bot=='vault' else [(845,1000),(845,1200),(900,1200),(1000,1430),(1100,1430),(845,1430)])]
    if stage=='direction':return [dict(direction=x) for x in [0,1,2]]
    if stage=='filters':return [dict(filter=x) for x in [0,2,4,5,6,7,8,9,10,11]]+[dict(filter=f,threshold=x) for f in [1,3] for x in [15,20,25,30,35]]
    if stage=='management':return [dict(day=x) for x in [0,1,2,3]]+[dict(maxday=x) for x in [1,2,3]]+[dict(flat=x) for x in [1200,1300,1400,1430,1500,1600]]
    if stage=='logic':return (([dict(noise=x) for x in [.15,.3,.45,.6]] if bot=='vault' else [])+[dict(atr=x) for x in [7,14,21,28]]+
       [dict(mean=x) for x in [10,15,20]]+([dict(adx=x) for x in [15,20,25,30]]+[dict(orminutes=x) for x in [15,30,60]] if bot=='overnight' else []))
    raise ValueError(stage)
def freeze():
    return {'schema':2,'revision_reason':'Pre-search review: avoid inert noise-fraction neighbours for Overnight; structural stop scale must change distance. No development search or finalist selection had occurred.',
      'raw':RAW,'stages':STAGES,'variants':{b:{s:variants(s,b) for s in STAGES} for b in RAW},
      'top_per_stage':3,'minimum_development_trades':30,'minimum_validation_trades':15,
      'development_rank':'(net PF - 1) * sqrt(trades) / (1 + native equity DD / 10), clean execution first',
      'validation_rank':'same score, minimum 15 trades, never recent/OOS',
      'neighbourhood':'three older-data finalists; stop scale .8/1/1.2 and RR .8/1/1.2 (9 Overnight neighbours); also noise barrier .8/1/1.2 for Vault (27 neighbours). Structural stop scale applies to distance. Zero-R/no-target dimensions may collapse and are reported honestly.',
      'plateau':'report profitable-neighbour share, median PF and return; favour >=60% positive neighbours before validation ranking',
      'controls':['Vault: no VWAP confirmation','Vault: zero noise barrier','Overnight: direction without frozen overnight bias','Overnight: ADX removed'],
      'codes':{'entry':{'0':'next-bar market (same executable quote as completed-signal close)','1':'additional closed-bar confirmation','2':'ATR-offset pullback limit, 2-bar expiry','3':'ATR-offset continuation stop, 2-bar expiry','4':'fixed-points pullback limit, 2-bar expiry'},
       'stop':{'0':'fixed price points','1':'SMA of completed session ATR times fraction','2':'closed strategy-TF ATR multiplier','3':'entry-price percent','4':'signal candle opposite extreme','5':'last 20 closed-bar swing','6':'opening/overnight range opposite side'},
       'trail':{'0':'unchanged','1':'break even','2':'ATR trail','3':'percent-price trail','4':'EMA12 trail','5':'closed 5-bar swing trail','6':'50% profit integer-R step lock','7':'50% partial at 1R plus break even / ATR trail','8':'20-bar chandelier trail','9':'dynamic 50% profit lock, 0.2R update steps'},
       'filter':{'0':'no extra filter; also disables overnight ADX','1':'ADX threshold','2':'DI agreement','3':'ADX + DI','4':'EMA50 direction','5':'H1 EMA200 direction','6':'ATR14/ATR50 0.75..2','7':'spread <= 10% ATR','8':'ADX rising','9':'source ADX (Overnight) / no extra (Vault)','10':'EMA50 slope direction','11':'ATR14 percentile 25..75 over last 200 closed readings'},
       'direction':{'0':'long','1':'short','2':'both'},'day':{'0':'all','1':'exclude Monday','2':'exclude Friday','3':'exclude both'}},
      'exclusions':{'news_blackout':'No timestamped point-in-time event feed frozen for this run; not fabricated.',
        'daily_timeframe':'Intraday closing-bar entry windows and overnight OR make D1 signals non-equivalent; intraday TFs only.',
        'exchange_volume':'Exness broker tick volume proxy, not NQ exchange volume.',
        'historical_holiday_calendar':'No verified historical broker early-close calendar. Test earlier fixed daily closes explicitly, not an invented calendar.',
        'pyramiding':'Original signal timing and position ownership are kept one-position; pyramiding requires a separate multi-position research design.',
        'overnight_weekend_holding':'Both source ideas mandate daily flat. Missed-quote carries are audited, not made a deliberate holding strategy.',
        'next_level_exit':'No objective next-level map is specified by either source; do not invent one.'}}
