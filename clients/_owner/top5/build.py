"""Owner-only builder. Customer folder contains five EX5s, one BAT, one HTML only."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,re,hashlib,shutil,subprocess,argparse,time
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
BASE=REPO/'AAA EAs/BM Trading Robust Sets 2026-08-04'
EVIDENCE=BASE/'Recent EA Shortlist 2026-09-30'
TESTER=BASE/'_Backtests/MT5-DMC-20260811'
CLIENT=REPO/'clients/top 5'
SLUGS=['gold-overnight-value-area','xau-rsi-vwap','nasdaq-overnight','nasdaq-5m-candle-momentum','orb-volume-profile']
def read(p):
    raw=p.read_bytes();return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(text,name,replacement):
    m=re.search(r'double\s+'+name+r'\s*\([^)]*\)\s*\{',text);assert m,name
    i=m.end();start=i;depth=1
    while depth:
        if text[i]=='{':depth+=1
        if text[i]=='}':depth-=1
        i+=1
    return text[:start]+'\n'+replacement+'\n'+text[i-1:]
def build(days=30,bound_login=0,bound_server='',test_expiry=None,only_slug=None):
    assert 1<=days<=3660
    assert not any(c in bound_server for c in '\r\n"\\')
    now=datetime.now(timezone.utc).replace(microsecond=0)
    terms_path=ROOT/'licence.json'
    if test_expiry:
        terms={'id':'TOP5-EXPIRY-TEST','issued_utc':now.isoformat(),'expires_utc':test_expiry,'bound_login':0,'bound_server':''}
    elif terms_path.exists():
        terms=json.loads(terms_path.read_text())
        if bound_login:
            assert bound_server,'Supply exact server with account binding'
            terms['bound_login']=bound_login;terms['bound_server']=bound_server
            terms_path.write_text(json.dumps(terms,indent=2))
    else:
        terms={'id':'CALYX-TOP5-20260930-01','issued_utc':now.isoformat(),'expires_utc':(now+timedelta(days=days)).isoformat(),'bound_login':bound_login,'bound_server':bound_server}
        ROOT.mkdir(parents=True,exist_ok=True);terms_path.write_text(json.dumps(terms,indent=2))
    out=ROOT/('build-expiry-test' if test_expiry else 'build');out.mkdir(parents=True,exist_ok=True)
    CLIENT.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'ClientGuard.mqh',out/'ClientGuard.mqh')
    trade=read(TESTER/'MQL5/Include/Trade/Trade.mqh')
    assert trade.count('::OrderSend(request,result)')==1 and trade.count('::OrderSendAsync(request,result)')==1
    trade=trade.replace('::OrderSend(request,result)','ClientOrderSend(request,result)').replace('::OrderSendAsync(request,result)','ClientOrderSend(request,result)')
    trade=re.sub(r'#include\s+"([^"]+)"',lambda m:'#include <Trade/'+m[1]+'>',trade)
    (out/'ClientTrade.mqh').write_text(trade,encoding='utf-8')
    rows={r['slug']:r for r in json.loads((EVIDENCE/'selection.json').read_text())}
    artifacts=[];hashes={}
    for ix,slug in enumerate(SLUGS):
        if only_slug and slug!=only_slug:
            assert test_expiry,'Partial production builds are not allowed'
            continue
        row=rows[slug];source=Path(row['expert']).with_suffix('.mq5')
        assert sha(Path(row['expert']))==row['ex5_sha256'] and sha(source)==row['source_sha256']
        cache={}
        def copy_graph(path):
            path=path.resolve();assert path.is_relative_to(BASE)
            if path in cache:return cache[path]
            name='src_'+hashlib.sha256(str(path).encode()).hexdigest()[:12]+'.mqh'
            cache[path]=name;hashes[str(path.relative_to(REPO))]=sha(path)
            text=read(path)
            if path==source.resolve():
                if slug=='gold-overnight-value-area':
                    old='double desired=(InpRiskMode==1?InpFixedRiskMoney:equity*InpRiskPercent/100)*multiplier;'
                    assert old in text;text=text.replace(old,'double desired=ClientRiskCash();')
                    text=text.replace('MathCeil(desired/MathAbs(unit)/lotstep-1e-10)','MathFloor(desired/MathAbs(unit)/lotstep+1e-10)')
                    target='double margin=0;if(!OrderCalcMargin'
                    assert target in text;text=text.replace(target,'if(lots* MathAbs(unit)>desired+0.001){rejected++;return;}\n '+target)
                elif slug=='xau-rsi-vwap':text=body(text,'RiskVolume','return ClientSizedVolume(ORDER_TYPE_BUY,entry,stop);')
                elif slug=='nasdaq-overnight':text=body(text,'LotsForRisk','return ClientSizedVolume(ORDER_TYPE_BUY,entry,stop);')
                elif slug=='nasdaq-5m-candle-momentum':text=body(text,'LotsForRisk','return ClientSizedVolume(type,entry,stop);')
                else:text=body(text,'LotsForRisk','return ClientSizedVolume(order_type,entry,stop);')
            text=re.sub(r'#include\s+[<"]Trade[\\/]Trade\.mqh[>"]','#include "ClientTrade.mqh"',text)
            def inc(m):return m[0] if m[1]=='ClientTrade.mqh' else '#include "'+copy_graph(path.parent/m[1].replace('\\','/'))+'"'
            text=re.sub(r'#include\s+"([^"]+)"',inc,text)
            text=re.sub(r'(?<![\w.])OrderSend(?:Async)?\s*\(','ClientOrderSend(',text)
            (out/name).write_text(text,encoding='utf-8');return name
        inc=copy_graph(source)
        code=read(source);has_timer=bool(re.search(r'void\s+OnTimer\s*\(',code))
        issued=int(datetime.fromisoformat(terms['issued_utc']).timestamp());expires=int(datetime.fromisoformat(terms['expires_utc']).timestamp())
        wrapper=f'''#property strict
#define CLIENT_ID "{terms['id']}"
#define CLIENT_ISSUED ((datetime){issued})
#define CLIENT_EXPIRES ((datetime){expires})
#define CLIENT_BOUND_LOGIN ((long){terms['bound_login']})
#define CLIENT_BOUND_SERVER "{terms['bound_server']}"
#define CLIENT_TEST_EXPIRY {'true' if test_expiry else 'false'}
#include "ClientGuard.mqh"
#define OnInit ClientStrategyInit
#define OnTick ClientStrategyTick
#define OnTimer ClientStrategyTimer
#include "{inc}"
#undef OnInit
#undef OnTick
#undef OnTimer
long ClientMagic(){{return (long)InpMagic;}}
int OnInit(){{int r=ClientInit();if(r!=INIT_SUCCEEDED)return r;r=ClientStrategyInit();if(r==INIT_SUCCEEDED)EventSetTimer(1);return r;}}
void OnTick(){{ClientPulse();ClientStrategyTick();}}
void OnTimer(){{ClientPulse();{'ClientStrategyTimer();' if has_timer else ''}}}
'''
        name='Calyx Top5 '+str(ix+1)+' '+row['label'];mq=out/(name+'.mq5');mq.write_text(wrapper,encoding='utf-8')
        log=out/(name+'.log')
        began=time.time()
        subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{mq}" /log:"{log}"',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        assert log.exists();report=read(log)
        assert re.search(r'\b0 errors, 0 warnings\b',report),report[-3000:]
        ex=mq.with_suffix('.ex5');assert ex.exists() and ex.stat().st_mtime>=began-2
        inputs=row['inputs']|{'ClientRiskMode':'0','ClientRiskValue':'50','ClientExpectedLogin':'0','ClientExpectedServer':'','ClientExpectedSymbol':''}
        # Stable dedicated client magic, never the owner's production identity.
        original_magic=inputs['InpMagic'];inputs['InpMagic']=str(93095001+ix)
        artifacts.append({'slug':slug,'label':row['label'],'expert':ex.name,'ex5_sha256':sha(ex),'symbol':row['symbol'],
          'period':row['period'],'inputs':inputs,'original_magic':original_magic,'source_sha256':row['source_sha256']})
        print('Compiled '+slug,flush=True)
    manifest={'licence':terms,'entries':artifacts,'source_hashes':hashes,'guard_sha256':sha(ROOT/'ClientGuard.mqh'),
      'risk_policy':'USD hedging only; fixed USD or current BALANCE percentage; round DOWN, skip below minimum; costs and gaps excluded from planned risk',
      'expiry_policy':'earlier of UTC and broker clock deadline; backward clock blocks entries; keep managing own positions; tester bypass unless test build'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    if not test_expiry:
        # Publish only after ALL five compile cleanly; failed compilation leaves delivery untouched.
        for entry in artifacts:shutil.copy2(out/entry['expert'],CLIENT/entry['expert'])
        (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--days',type=int,default=30);ap.add_argument('--login',type=int,default=0);ap.add_argument('--server',default='');ap.add_argument('--test-expiry');ap.add_argument('--renew-days',type=int)
    a=ap.parse_args()
    if a.renew_days:
        assert 1<=a.renew_days<=3660
        p=ROOT/'licence.json';d=json.loads(p.read_text());d['expires_utc']=(datetime.now(timezone.utc)+timedelta(days=a.renew_days)).replace(microsecond=0).isoformat()
        if a.login:d['bound_login']=a.login;d['bound_server']=a.server
        p.write_text(json.dumps(d,indent=2))
    build(a.days,a.login,a.server,a.test_expiry)
