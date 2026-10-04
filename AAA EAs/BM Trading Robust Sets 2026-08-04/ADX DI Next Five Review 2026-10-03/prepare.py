"""Mechanical private-copy instrumentation; original sources never changed."""
from pathlib import Path
import os,sys,re,json,hashlib
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(B.parent/'EA store'))
from app.catalog import get_product
SPECS={'weakness':('xau-weakness','XAUUSD','M30',30),'sell':('sell-nasdaq-15min','USTEC','M15',15),
       'squeeze':('xau-squeeze-momentum-standard','XAUUSD','H1',16385),
       'trio':('3-way-gold','XAUUSD','M15',15),'orb':('orb-volume-profile','XAUUSD','M5',5)}
def read(p):
    v=p.read_bytes();return (v.decode('utf-16') if v[:2] in (b'\xff\xfe',b'\xfe\xff') else v.decode('utf-8-sig')).replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def includes(s,path):
    def replace(m):
        p=(path.parent/m[1].replace('\\','/')).resolve()
        assert p.is_file(),p
        return '#include "'+(p.name if p.parent==path.parent else p.as_posix())+'"'
    return re.sub(r'#include\s+"([^"]+)"',replace,s)
def lifecycle(s):
    s,n=re.subn(r'(int OnInit\(\)\s*\{)',r'\1\n if(!StudyInit())return INIT_FAILED;',s,count=1);assert n==1
    if 'void OnDeinit(' in s:s=re.sub(r'(void OnDeinit\([^)]*\)\s*\{)',r'\1\n StudyClose();',s,count=1)
    else:s+='\nvoid OnDeinit(const int reason){StudyClose();}\n'
    return s
def main():
    bots={}
    for key,(slug,symbol,period,tf) in SPECS.items():
        product=get_product(slug);src=B/product.expert_source;src=src.with_suffix('.mq5');sett=B/product.set_source
        assert src.is_file() and src.with_suffix('.ex5').is_file() and sett.is_file()
        folder=R/'EA'/key;folder.mkdir(parents=True,exist_ok=True)
        for p in src.parent.glob('*.mqh'):
            s=includes(read(p),p)
            if key=='weakness' and p.name=='AAA_Final_Common.mqh':
                s=once(s,'#include <Trade/Trade.mqh>','#include <Trade/Trade.mqh>\n#include "../StudyFilter.mqh"')
                pos=s.index('bool AAA_SendPending(');end=s.index('\n}\n',pos)+3;a=s[:pos];tail=s[pos:end]
                tail=once(tail,'   AAA_Trade.SetExpertMagicNumber((ulong)magic);','   if(!StudyAllow(direction))return false;\n   AAA_Trade.SetExpertMagicNumber((ulong)magic);')
                s=a+tail+s[end:]
            if key=='weakness' and p.name=='AAA_Final_Strategy_Engine.mqh':s=lifecycle(s)
            (folder/p.name).write_text(s,encoding='utf-8')
        s=includes(read(src),src)
        if key!='weakness':
            s=once(s,'#include <Trade/Trade.mqh>','#include <Trade/Trade.mqh>\n#include "../StudyFilter.mqh"');s=lifecycle(s)
            if key=='sell':
                pos=s.index('bool PlaceSellStop(');end=s.index('void EvaluateSetup()',pos)
                part=once(s[pos:end],'   trade.SetExpertMagicNumber((ulong)InpMagic);','   if(!StudyAllow(-1))return false;\n   trade.SetExpertMagicNumber((ulong)InpMagic);');s=s[:pos]+part+s[end:]
            elif key=='squeeze':s=once(s,'   if(lots<=0.0) return;\n   Trade.SetExpertMagicNumber((ulong)InpMagic);','   if(lots<=0.0) return;\n   if(!StudyAllow(1))return;\n   Trade.SetExpertMagicNumber((ulong)InpMagic);')
            elif key=='trio':s=once(s,' trade.SetExpertMagicNumber(S[s].magic);bool ok=false;',' if(m<2&&!StudyAllow(side,TF(s),m+1))return false;\n trade.SetExpertMagicNumber(S[s].magic);bool ok=false;')
            else:
                pos=s.index('bool EnterTrade(');end=s.index('void EvaluateClosedSignalBar',pos)
                part=once(s[pos:end],'   trade.SetExpertMagicNumber((ulong)InpMagic);','   if(!StudyAllow(direction))return false;\n   trade.SetExpertMagicNumber((ulong)InpMagic);');s=s[:pos]+part+s[end:]
        (folder/'Research.mq5').write_text(s,encoding='utf-8')
        inputs={k.strip():v.split('||')[0].strip() for line in read(sett).splitlines() if '=' in line and not line.startswith(';') for k,v in [line.split('=',1)]}
        inputs['InpRiskPercent']='1.0'
        if key!='sell':inputs['InpAdaptivePortfolioControls']='false'
        if key=='trio':inputs['InpResearchLedger']='true'
        bots[key]=dict(label=product.label,slug=slug,source=str(src),original=str(src.with_suffix('.ex5')),setting=str(sett),symbol=symbol,period=period,tf=tf,gate=1,inputs=inputs,original_sha=sha(src.with_suffix('.ex5')),source_sha=sha(src),set_sha=sha(sett),helpers={str(p):sha(p) for p in src.parent.glob('*.mqh')})
    out=R/'bots.json'
    if out.exists():assert json.loads(out.read_text())==bots,'Frozen inputs changed'
    else:out.write_text(json.dumps(bots,indent=2),encoding='utf-8')
    print('Prepared five private copies; production untouched.')
if __name__=='__main__':main()
