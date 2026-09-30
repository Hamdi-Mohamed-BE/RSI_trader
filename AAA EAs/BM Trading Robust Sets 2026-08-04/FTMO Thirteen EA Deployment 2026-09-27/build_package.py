"""Build isolated, account-locked copies. Never touches installed terminals or source EAs."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
TESTER=BASE/"_Backtests/MT5-DMC-20260811"
OUT=ROOT/"package"

def read(path):
    raw=path.read_bytes()
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe",b"\xfe\xff")) else "utf-8-sig").replace("\r\n", "\n")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def replace_body(text,name,body):
    m=re.search(r"double\s+"+name+r"\s*\([^)]*\)\s*\{",text)
    assert m,name
    start=m.end();i=start;depth=1
    while depth:
        if text[i]=="{":depth+=1
        if text[i]=="}":depth-=1
        i+=1
    return text[:start]+"\n"+body+"\n"+text[i-1:]

def build(compile_eas=True, only_slugs=None):
    frozen=json.loads((BASE/"FTMO Fourteen EA Study 2026-09-27/FROZEN.json").read_text(encoding="utf-8-sig"))
    entries=[e for e in frozen["entries"] if e["slug"]!="news-pulse-xau"]
    assert len(entries)==13
    # 2026-09-30 (user request): 3 Way Gold appended as entry 14, market-entry build (the guard admits no pending
    # orders). The first 13 entries, their sources, settings and binaries are unchanged.
    extra=json.loads((BASE/"3 Way Gold Deployment 2026-09-30/FTMO_ENTRY.json").read_text(encoding="utf-8"))
    for e in extra:
        for key in ("expert","settings"):e[key]=str(BASE/e[key])
    entries+=extra
    assert len(entries)==14 and entries[-1]["slug"]=="3-way-gold"
    # Explicit management replacement; preserve the original experiment's frozen inputs/results.
    override_path=BASE/"Nasdaq 5M DI ATR Deployment 2026-09-28/SELECTION.json"
    override=json.loads(override_path.read_text(encoding="utf-8"))
    for e in entries:
        if e["slug"]=="nasdaq-5m-candle-momentum":
            for key in ("expert","expert_sha","settings","settings_sha","inputs"):
                e[key]=override[key]
            for key in ("expert","settings"):
                e[key]=str(BASE/e[key])
    # Explicit comment-only build replacement; never rewrite historical FROZEN.json.
    comment_release=json.loads((BASE/"ORB Comment Labels 2026-09-28/RELEASE.json").read_text())
    assert comment_release["comment_only"] is True
    assert sha(BASE/comment_release["helper"])==comment_release["helper_sha"]
    for e in entries:
        if e["slug"] not in ("xau-orb-london-ny-overlap-m30","us100-h1-orb-13utc"):continue
        matching=[b for b in comment_release["builds"] if (BASE/b["expert"]).resolve()==Path(e["expert"]).resolve()]
        assert len(matching)==1,e["slug"]
        b=matching[0]
        assert b["logic_unchanged"] and e["expert_sha"]==b["expert_before_sha"]
        assert sha(BASE/b["source"])==b["source_sha"]
        e["expert_sha"]=b["expert_sha"]
    OUT.mkdir(exist_ok=True)
    cache={};evidence={}
    trade_path=TESTER/"MQL5/Include/Trade/Trade.mqh"
    trade=read(trade_path)
    assert trade.count("::OrderSend(request,result)")==1
    assert trade.count("::OrderSendAsync(request,result)")==1
    trade=trade.replace("::OrderSend(request,result)","FTMOOrderSend(request,result)")
    trade=trade.replace("::OrderSendAsync(request,result)","FTMOOrderSend(request,result)")
    trade=re.sub(r'#include\s+"([^"]+)"',lambda m:'#include <Trade/'+m[1]+'>',trade)
    (OUT/"FTMO_Trade.mqh").write_text(trade,encoding="utf-8")
    shutil.copyfile(ROOT/"CalyxFTMOGuard.mqh",OUT/"CalyxFTMOGuard.mqh")

    def copy_graph(path):
        path=path.resolve()
        assert path.is_relative_to(BASE.resolve()),path
        if path in cache:return cache[path]
        name="src_"+hashlib.sha256(str(path.relative_to(BASE)).encode()).hexdigest()[:12]+".mqh"
        cache[path]=name
        text=read(path);evidence[str(path.relative_to(BASE))]=sha(path)
        # The shared risk hook makes 0.5% inputs mean fixed $50, retaining strategy leverage caps.
        if path.name=="CalyxAdaptivePortfolio.mqh":
            text=replace_body(text,"CalyxAdaptiveRiskMultiplier",
                "   double equity=AccountInfoDouble(ACCOUNT_EQUITY);\n   return equity>0 ? 10000.0/equity : 0.0;")
        text=re.sub(r'#include\s+[<"]Trade[\\/]Trade\.mqh[>"]','#include "FTMO_Trade.mqh"',text)
        def inc(m):
            rel=m[1]
            if rel=="FTMO_Trade.mqh":return m[0]
            return '#include "'+copy_graph(path.parent/rel.replace("\\","/"))+'"'
        text=re.sub(r'#include\s+"([^"]+)"',inc,text)
        # All raw global submissions also go through the admission guard (CTrade handled above).
        text=re.sub(r'(?<![\w.])OrderSend(?:Async)?\s*\(', 'FTMOOrderSend(', text)
        (OUT/name).write_text(text,encoding="utf-8")
        return name

    manifest=dict(version="FTMO14-20260930-3WAYGOLD-MARKET",news_enabled=False,risk_usd=50,
                  comment_release=comment_release["version"],
                  portfolio_forecast_status="Prior fixed-target simulations do not apply to the changed Nasdaq management",
                  reference_balance=10000,entries=[],source_hashes=evidence,
                  guard_sha=sha(ROOT/"CalyxFTMOGuard.mqh"))
    for e in entries:
        source=Path(e["expert"]).with_suffix(".mq5")
        assert source.is_file(),source
        # The experiment's binaries/settings must not change silently.
        assert sha(Path(e["expert"]))==e["expert_sha"],e["slug"]+" binary changed"
        assert sha(Path(e["settings"]))==e["settings_sha"],e["slug"]+" settings changed"
        inc=copy_graph(source)
        all_sources="\n".join(read(OUT/p) for p in cache.values())
        has_timer="void OnTimer(" in all_sources or "void  OnTimer(" in all_sources
        # Determine callback presence from this source's own transitive includes.
        def expanded(name,seen=None):
            seen=set() if seen is None else seen
            if name in seen:return ""
            seen.add(name);t=read(OUT/name)
            return t+"\n"+"\n".join(expanded(n,seen) for n in re.findall(r'#include "(src_[^"]+)"',t))
        code=expanded(inc)
        assert "CalyxAdaptiveRiskMultiplier(" in code,e["slug"]+" risk hook missing"
        timer=bool(re.search(r"void\s+OnTimer\s*\(",code))
        assert re.search(r"int\s+OnInit\s*\(",code)
        assert re.search(r"void\s+OnTick\s*\(",code)
        wrapper=('#property strict\n#include "CalyxFTMOGuard.mqh"\n'
                 '#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n'
                 '#define OnTimer FTMO_StrategyTimer\n#include "'+inc+'"\n'
                 '#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
                 'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\n'
                 'void OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
        if timer:wrapper+='void OnTimer(){ if(FTMOPulse())FTMO_StrategyTimer(); }\n'
        name="FTMO13-"+e["slug"]
        mq5=OUT/(name+".mq5");mq5.write_text(wrapper,encoding="utf-8")
        inputs=dict(e["inputs"]);inputs["InpRiskPercent"]="0.5"
        inputs["InpAdaptivePortfolioControls"]="false"
        if "InpTesterOnly" in inputs:inputs["InpTesterOnly"]="false"
        if "InpFixedRiskMoney" in inputs:inputs["InpFixedRiskMoney"]="50"
        # Runtime account locks deliberately invalid until launcher binds the chosen account.
        inputs.update(FTMOExpectedLogin="0",FTMOExpectedServer="",FTMOExpectedSymbol="",FTMOPhase="1")
        setname=name+".set"
        (OUT/setname).write_text("\n".join(f"{k}={v}" for k,v in inputs.items())+"\n",encoding="utf-8")
        if compile_eas and (only_slugs is None or e["slug"] in only_slugs):
            log=OUT/(name+".log")
            p=subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{mq5}" /log:"{log}"',
                             timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
            assert log.exists(),f"No compiler log: {name}"
            report=read(log)
            if "0 errors, 0 warnings" not in report:
                raise RuntimeError(name+"\n"+"\n".join(x for x in report.splitlines() if "error" in x.lower() or "warning" in x.lower()))
            assert mq5.with_suffix(".ex5").exists(),name
        artifact=dict(slug=e["slug"],label=e["label"],symbol=e["symbol"],timeframe=e["timeframe"],
                      expert=name+".ex5",settings=setname,inputs=inputs)
        if mq5.with_suffix(".ex5").exists():artifact["expert_sha"]=sha(mq5.with_suffix(".ex5"))
        artifact["settings_sha"]=sha(OUT/setname)
        manifest["entries"].append(artifact)
        print("BUILT "+e["slug"],flush=True)
    manifest["files"]={p.name:sha(p) for p in OUT.iterdir() if p.suffix in (".mq5",".mqh",".ex5",".set")}
    (ROOT/"PACKAGE.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
if __name__=="__main__":
    only={"xau-orb-london-ny-overlap-m30","us100-h1-orb-13utc"} if "--only-orb" in sys.argv else None
    if "--only-3wg" in sys.argv:only={"3-way-gold"}
    build("--source-only" not in sys.argv,only)
