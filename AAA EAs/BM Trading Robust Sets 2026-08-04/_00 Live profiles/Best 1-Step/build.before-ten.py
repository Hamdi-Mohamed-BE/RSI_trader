"""Build the Best 1-Step profile (owner 2026-11-11: "nasdaq 5m and overnight bias orb and gold band wave and EMA3 are must have ... best portfolio for 1 step ...
create guard and no guard bat files"). Evidence: ../../Best 1-Step Search 2026-11-11/ (FINAL.json, REPORT.md).

2026-11-17 roster (owner) = 9 EAs: Nasdaq 5M, USDJPY London, 3 Way Gold breakout, EMA3, US100 Selective ORB V3, XAU RSI VWAP, ORB VP Volume Confirmed,
Overnight Bias ORB, UK100 Monday dip (Sell Nasdaq removed 2026-11-11; Gold Band Wave + XAU Squeeze removed 2026-11-17). Original 2026-11-11 roster = Core 9 + P4 = 11 EAs: Nasdaq 5M (REPLACE, DI OFF default as tested), USDJPY London (DI ON as tested), 3 Way Gold breakout only, Sell Nasdaq 15min, EMA3,
ORB VP Volume Confirmed, XAU Squeeze, US100 Selective ORB V3 (0.5R), XAU RSI VWAP, Overnight Bias ORB, Gold Band Wave. This is the 'ref:Core9+P4' row of the search
(GUARD 0.5%), chosen over the rule's forced pick (11 EAs at 0.75% incl. Vault Break) because it is better on validation, OOS and MC; see REPORT.md.

  * Best 1-Step - FTMO 1-Step guard.bat -> 1-Step/  ftmo 1_step guard (10% EOD-trailing, 3% daily, best day <= 50%), own state key B1O, default risk 0.5%
  * Best 1-Step - no guard.bat          -> ../Packages/Best1Step  no guard, the already compiled Core 9 / P4 no-guard EX5s (no recompile)

Guarded wrappers: exactly the Core 9 build (../Core 9/build.py: FTMO-AnyBroker wrappers, Sell Nasdaq held stop, ORB VP VC) plus the P4 research wrappers
(../P4/build.py: Overnight Bias ORB live broker clock, Gold Band Wave restart-safe exit). Offline: MetaEditor compile only, no MT5 terminal.

python build.py            full build (compiles 11 guarded wrappers)
python build.py installer  regenerate the installer + helpers only
Run from AAA EAs/EA store:  uv run python "<this>" """
import importlib.util, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; LIVE = HERE.parent; ROOT = LIVE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


C9 = load('core9_build', LIVE / 'Core 9/build.py'); P4 = load('p4_build', LIVE / 'P4/build.py')
BL = C9.BL; read, write, sub1, sha, compile_ea, set_values = C9.read, C9.write, C9.sub1, C9.sha, C9.compile_ea, C9.set_values
ANY, F1S, EDGE = C9.ANY, C9.F1S, C9.EDGE; NOGUARD = LIVE / 'Packages/Best1Step'; CORE9_NG = LIVE / 'Packages/Core9'; P4_NG = LIVE / 'Packages/P4'
VERSION = 'BEST1STEP-20261117'; TAG = 'B1O'; SCRIPT = 'Install-Best1Step-1Step.ps1'
RESEARCH = ['overnight-bias-orb', 'uk100-monday-dip']
DROPPED = ['xau-squeeze-momentum-standard', 'gold-band-wave']   # owner 2026-11-17: "keep EMA3 and RSI VWAP, remove Gold Band Wave and XAU Squeeze Momentum"
SLUGS = [x for x in C9.SLUGS if x not in DROPPED] + RESEARCH
assert len(SLUGS) == 9 and len(set(SLUGS)) == 9   # 2026-11-11: Sell Nasdaq removed, UK100 Monday dip added; 2026-11-17: Gold Band Wave + XAU Squeeze removed (owner)
WORD = 'nine'
# 2026-11-17 owner: "build the no opposite trade rule into the EAs and add to profile along side with weekend hold".
# Calyx No Opposite (../Calyx No Opposite): input InpCalyxNoOpposite (default false = the tested order path); the installers ask ON/OFF.
CNO = LIVE / 'Calyx No Opposite'
CNO_PS = (
    "# >>> Calyx No Opposite (owner 2026-11-17) >>>\n"
    "function Read-CalyxNoOpposite([string]$Current, [bool]$NoPrompt) {\n"
    "    if ($Current) { if ($Current -notin @('ON','OFF')) { throw 'No-opposite rule must be ON or OFF.' }; return $Current }\n"
    "    if ($NoPrompt) { return 'OFF' }\n"
    "    Write-Host ''\n"
    "    Write-Host 'NO OPPOSITE TRADES (hedging rule)' -ForegroundColor Cyan\n"
    "    Write-Host '  ON  = an EA never opens a trade or places a pending order against an open position on the same symbol (any EA,'\n"
    "    Write-Host '        manual too), and deletes its own pending orders that face one. Use it at FundingPips: a buy and a sell on one'\n"
    "    Write-Host '        symbol at the same time is forbidden hedging there, with no exceptions. Simulation: about 7% fewer trades, ~4% less R.'\n"
    "    Write-Host '  OFF (default) = the tested behaviour; FTMO and The5ers have not restricted it.'\n"
    "    $answer = (Read-Host 'No opposite trades on the same symbol? ON or OFF [OFF]').Trim().ToUpperInvariant()\n"
    "    if (-not $answer) { $answer = 'OFF' }\n"
    "    if ($answer -notin @('ON','OFF')) { throw 'Answer ON or OFF.' }\n"
    "    Write-Host ('No-opposite rule: {0}' -f $answer)\n"
    "    return $answer\n"
    "}\n"
    "# <<< Calyx No Opposite <<<\n")
NG_WRAP = {'nasdaq-5m-candle-momentum': 'current14', '3-way-gold': 'edge10',   # Nasdaq: Current14 source = the verified REPLACE build (Packages/Edge10 Sources reverted to pre-REPLACE, found 2026-11-17)
           'orb-volume-profile-volume-confirmed': 'edge10',
           'usdjpy-london-open-momentum': 'current14', 'ema3': 'current14', 'us100-selective-orb-v3': 'current14', 'xau-rsi-vwap': 'current14'}
NG_SRC = {'edge10': (LIVE / 'Packages/Edge10/Sources', 'Calyx Edge10 - '), 'current14': (BL.CURRENT / 'Sources', 'Calyx Current14 ORB05 - ')}
DIRECT_SEND = r'(?<![.\w:])OrderSend\('


def cno_check():
    m = json.loads(read(CNO / 'CNO.json'))
    assert sha(CNO / 'CNO_Trade.mqh') == m['cno_trade_sha256'] and sha(CNO / 'CalyxNoOpposite.mqh') == m['cno_include_sha256'], 'Calyx No Opposite files changed: rerun make_trade.py and the native tests'


def cno_text(t):
    # no-guard wrappers: CTrade and direct OrderSend go through CalyxNoOppOrderSend (= ::OrderSend while InpCalyxNoOpposite=false)
    t = t.replace('#include <Trade/Trade.mqh>', '#include "CNO_Trade.mqh"')
    return re.sub(DIRECT_SEND, 'CalyxNoOppOrderSend(', t)


def cno_copy(path, target, cache):
    path = path.resolve()
    if path in cache: return cache[path]
    cache[path] = path.name; t = cno_text(read(path))
    for inc in re.findall(r'#include\s+"([^"]+)"', t):
        if inc in ('CNO_Trade.mqh', 'CalyxNoOpposite.mqh') or inc.startswith('../'): continue
        cno_copy(path.parent / inc.replace(chr(92), '/'), target, cache)
    write(target / path.name, t); return path.name


def cno_wrapper(text):
    text = sub1(text, '#include "../RiskSupport.mqh"\n', '#include "../../RiskSupport.mqh"\n#include "CalyxNoOpposite.mqh"   // Best 1-Step 2026-11-17: no-opposite rule\n')
    return sub1(text, 'UR_Heartbeat(InpMagic);UR_StrategyTick();}', 'UR_Heartbeat(InpMagic);CNO_Tick();UR_StrategyTick();}')
# UK100 Monday dip = FTSE Three Setup Raw 2026-10-27 S2, unchanged rules (Monday London day, close < SMA20, RSI < 40, long, 2.5 ATR stop, 2R, 24 h), one per Monday.
FTSE_SRC = ROOT / 'FTSE Three Setup Raw 2026-10-27/EA/FTSE Three Setup Research EA.mq5'
FTSE_INPUTS = dict(json.loads(read(ROOT / 'FTSE Three Setup Raw 2026-10-27/run-config.json'))['common_inputs'])
FTSE_INPUTS.update(InpSetup1='false', InpSetup2='true', InpSetup3='false', InpRiskPercent='0.5')
UK = dict(label='UK100 Monday Dip', symbol='UK100', timeframe='H1', period=60)
UK_ALIASES = ['UK100', 'UK100CASH', 'FTSE100', 'FTSE', 'UKX', 'UK100CFD', 'GBR100']


def ftse_text(noguard):
    # Asserted edits; the tester path is unchanged: (1) live broker clock instead of the UTC-server input, (2) unused InpAdaptivePortfolioControls for the
    # installers' preset checks, (3) no guard only: the risk budget comes from RiskSupport.mqh (installer % of equity or fixed USD).
    t = read(FTSE_SRC)
    t = sub1(t, 'datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}',
             'int SrvOffSec(){if((bool)MQLInfoInteger(MQL_TESTER))return InpServerUtcOffsetHours*3600;datetime s=TimeTradeServer(),u=TimeGMT();if(s<=0||u<=0)return InpServerUtcOffsetHours*3600;return (int)MathRound((double)(s-u)/1800.0)*1800;}\n'
             'datetime Utc(datetime server){return server-(datetime)SrvOffSec();}   // Best 1-Step build: live = broker clock')
    t = sub1(t, 'input int    InpServerUtcOffsetHours=0;  // Exness server = UTC\n',
             'input int    InpServerUtcOffsetHours=0;  // tester only; live uses the broker clock\ninput bool   InpAdaptivePortfolioControls=false;   // Best 1-Step build: unused, kept for the installer preset checks\n')
    if noguard: t = sub1(t, 'double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;', 'double goal=UR_RiskBudget();   // Best 1-Step no guard: installer budget')
    return t


def ftse_include(target, shim, noguard):
    t = ftse_text(noguard)
    if shim:
        t = sub1(t, '#include <Trade/Trade.mqh>', '#include "FTMO_Trade.mqh"'); t = re.sub(r'\bOrderSend\(', 'FTMOOrderSend(', t)
    name = 'src_b1_uk100-monday-dip.mqh'; write(target / name, t); return name


def guard_text():
    g = read(F1S / 'CalyxFTMOGuard.mqh'); assert sha(F1S / 'CalyxFTMOGuard.mqh') == json.loads(read(F1S / 'PACKAGE.json'))['guard_sha'], 'ftmo 1_step guard altered'
    g = sub1(g, 'return "F1S"+IntegerToString(FTMOExpectedLogin)', 'return "' + TAG + '"+IntegerToString(FTMOExpectedLogin)')
    g = sub1(g, '#define CALYX_PROP_READY_GUARD\n', '#define CALYX_PROP_READY_GUARD\n#include "CalyxNoOpposite.mqh"   // Best 1-Step 2026-11-17: no-opposite rule (InpCalyxNoOpposite), checked inside the guard lock\n')
    return sub1(g, '   if(entry && !FTMOAdmit(r,result)){FileClose(lock);return false;}',
                '   if(entry && InpCalyxNoOpposite && CNO_OppositeOpen(r.symbol,CNO_Dir(r.type))){FileClose(lock);return FTMOReject(result,"no-opposite rule: opposite position open on "+r.symbol);}\n'
                '   if(entry && !FTMOAdmit(r,result)){FileClose(lock);return false;}')


def build_guarded(anyb, edge):
    root = HERE / '1-Step'; pkg = root / 'package'
    for d in (pkg, root / 'EAs', root / 'Sets'):
        if d.exists(): shutil.rmtree(d)                  # this profile's own generated folders only
        d.mkdir(parents=True)
    guard = guard_text(); write(root / 'CalyxFTMOGuard.mqh', guard); write(pkg / 'CalyxFTMOGuard.mqh', guard)
    cno_check(); shutil.copy2(CNO / 'CalyxNoOpposite.mqh', root / 'CalyxNoOpposite.mqh'); shutil.copy2(CNO / 'CalyxNoOpposite.mqh', pkg / 'CalyxNoOpposite.mqh')
    for f in (ANY / 'package').iterdir():
        if f.suffix == '.mqh' and f.name != 'CalyxFTMOGuard.mqh': shutil.copy2(f, pkg / f.name)
    entries = []; magics = {}; cache = {}
    for slug in SLUGS:
        stem = f'{TAG}-{slug}'
        if slug in C9.FROM_ANY:
            e = next(x for x in anyb['entries'] if x['slug'] == slug); label, symbol, timeframe = e['label'], e['symbol'], e['timeframe']
            write(pkg / f'{stem}.mq5', read(ANY / 'package' / (Path(e['expert']).stem + '.mq5'))); values = set_values(ANY / 'package' / e['settings']); source = ('FTMO-AnyBroker', e['expert'], e['settings'])
        elif slug in C9.FROM_EDGE:
            e = next(x for x in edge['entries'] if x['key'] == slug); label, symbol, timeframe = C9.FROM_EDGE[slug]; assert e['canonical'] == symbol
            include = C9.graph_copy(Path(e['production_source']), pkg, cache, True, C9.virtual_stop if slug == 'sell-nasdaq-15min' else None)
            code = ('#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#define OnTimer FTMO_StrategyTimer\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
                    'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\nvoid OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
            if re.search(r'void\s+OnTimer\s*\(', C9.expansion(pkg, include)): code += 'void OnTimer(){ if(FTMOPulse())FTMO_StrategyTimer(); }\n'
            write(pkg / f'{stem}.mq5', code); values = {k: str(v) for k, v in e['inputs'].items()}; source = ('Edge10', e['production_source'], e['settings'])
            if slug == 'sell-nasdaq-15min': assert 'trade.SellStop(' not in read(pkg / include)
        elif slug == 'uk100-monday-dip':
            label, symbol, timeframe = UK['label'], UK['symbol'], UK['timeframe']; include = ftse_include(pkg, True, False)
            code = ('#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n'
                    'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\nvoid OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
            write(pkg / f'{stem}.mq5', code); values = dict(FTSE_INPUTS, InpAdaptivePortfolioControls='false'); source = ('research (FTSE S2, Best 1-Step edits)', str(FTSE_SRC), 'FTSE run-config S2')
        else:
            r = P4.RESEARCH[slug]; label, symbol, timeframe = r['label'], r['symbol'], r['timeframe']; include = P4.flat_include(slug, pkg, True, False)
            code = ('#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n'
                    'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\nvoid OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
            write(pkg / f'{stem}.mq5', code); values = dict(r['inputs'], InpAdaptivePortfolioControls='false'); source = ('research (P4 edits)', str(r['source']), 'p7.py NEW inputs')
        compile_ea(pkg / f'{stem}.mq5')
        assert values['InpRiskPercent'] == '0.5' and values.get('InpAdaptivePortfolioControls') == 'false', slug
        if slug == 'us100-selective-orb-v3': assert values['InpRewardRisk'] == '0.5'
        if slug == '3-way-gold':
            assert values['InpMarketEntries'] == 'true'; values.update(InpEnableMomentum='false', InpEnableBreakout='true', InpEnableTurnOfMonth='false')
        if slug == 'nasdaq-5m-candle-momentum': values['InpRequireDIAgreement'] = 'false'          # tested DI OFF (pool stream); the installer asks
        if slug == 'usdjpy-london-open-momentum': assert values['InpRequireDIAgreement'] == 'true'    # tested DI ON (Core 9 stream)
        values.update(FTMOAllocationMode='1', FTMOAllocationValue='0.5', FTMOPhase='1', **C9.UNARMED); values.update(C9.RULES_1STEP); values['InpCalyxNoOpposite'] = 'false'
        magic = values.get('InpMagic') or values.get('InpMagicBase'); assert magic and magic not in magics, ('magic clash', slug, magic); magics[magic] = slug
        write(pkg / f'{stem}.set', '\n'.join(f'{k}={v}' for k, v in values.items()) + '\n')
        shutil.copy2(pkg / f'{stem}.ex5', root / 'EAs' / f'{stem}.ex5'); shutil.copy2(pkg / f'{stem}.set', root / 'Sets' / f'{stem}.set')
        entries.append(dict(slug=slug, label=label, symbol=symbol, timeframe=timeframe, expert=f'{stem}.ex5', settings=f'{stem}.set', magic=magic, source_package=source[0], source_expert=source[1], source_settings=source[2], expert_sha=sha(pkg / f'{stem}.ex5'), settings_sha=sha(pkg / f'{stem}.set')))
    files = {p.name: sha(p) for p in pkg.iterdir() if p.is_file() and p.suffix != '.log'}
    out = dict(version=f'{VERSION}-1-Step', ruleset='FTMO_1STEP', entries=entries, news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True, reference_mode='FRESH_BASELINE_EVERY_RUN', default_phase='Challenge',
               risk_cap_fraction=0.005, total_risk_fraction=0.0225, symbol_risk_fraction=0.015, strategy_risk_percent='0.5 (installer: 1.5x the chosen risk, max 5)', nasdaq_di_default='OFF', usdjpy_di_default='ON',
               sell_nasdaq='stop held in the EA, sold at market (these guards refuse pending orders)', research_eas='overnight-bias-orb: research source with the asserted P4 edits (../P4/build.py); uk100-monday-dip: FTSE S2 raw EA with the asserted edits in this build.py',
               guard_sha=sha(root / 'CalyxFTMOGuard.mqh'), guard_state_prefix=TAG, source_package=dict(name=ANY.name, version=anyb['version'], guard_sha=anyb['guard_sha']), files=files)
    write(root / 'PACKAGE.json', json.dumps(out, indent=2) + '\n'); print('Built 1-Step', len(entries), 'EAs', flush=True)


ROSTER = ',\n        '.join(', '.join(f"'{x}'" for x in SLUGS[i:i + 4]) for i in range(0, len(SLUGS), 4))


def installer():
    s = C9.installer_1step().replace('\r\n', '\n')
    s, n = re.subn(r"\$expected=@\('[^)]*\)", lambda m: '$expected=@(' + ROSTER + ')', s, count=1); assert n == 1
    for a, b in [("[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',", "[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',"),
                 ("# Core 9 2026-11-05: nine EAs with the FTMO 1-Step guard", "# Best 1-Step 2026-11-17: Core 9 without Sell Nasdaq / XAU Squeeze + Overnight Bias ORB + UK100 Monday dip, nine EAs (Gold Band Wave + XAU Squeeze removed 2026-11-17) with the FTMO 1-Step guard"),
                 ("# GENERATED by Core 9/build.py from ftmo 1_step/Install-FTMO1Step.ps1; do not edit by hand.", "# GENERATED by Best 1-Step/build.py (via Core 9/build.py) from ftmo 1_step/Install-FTMO1Step.ps1; do not edit by hand."),
                 ("if($manifest.entries.Count -ne 9 -or", f"if($manifest.entries.Count -ne {len(SLUGS)} -or"),
                 ("        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF [ON]').Trim().ToUpperInvariant()\n        if(-not $answer){$answer='ON'}\n",
                  "        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF (tested OFF) [OFF]').Trim().ToUpperInvariant()\n        if(-not $answer){$answer='OFF'}\n"),
                 ("3 Way Gold breakout only", "3 Way Gold breakout only / Overnight Bias ORB + UK100 Monday dip"),
                 ("USDJPY=@('USDJPY')}", "USDJPY=@('USDJPY');UK100=@(" + ','.join("'" + a + "'" for a in UK_ALIASES) + ")}"),
                 ("Nasdaq DI default ON.", "Nasdaq DI default OFF.")]:
        s = sub1(s, a, b)
    for a, b in [('Calyx-Core9-1Step-', 'Calyx-Best1Step-'), ('CORE9 1STEP', 'BEST1STEP'), ('.core9-1step-backup-', '.best1step-backup-'), ('CORE 9', 'BEST 1-STEP'), ('Core 9', 'Best 1-Step'),
                 ('nine guarded EAs', WORD + ' guarded EAs'), ('nine EAs', WORD + ' EAs'), ('all nine charts', 'all ' + WORD + ' charts'), ('PASS: 9 integrity', f'PASS: {len(SLUGS)} integrity')]:
        assert a in s, a; s = s.replace(a, b)
    for bad in ('Core9', 'CORE9', 'core9') + (('nine',) if WORD != 'nine' else ()): assert bad not in s, bad
    # 2026-11-11 owner: ask for each EA (Select-CalyxEntries in Calyx-InstallChoices.ps1 / Calyx-SelectEAs.ps1)
    s = sub1(s, "[ValidateSet('','ON','OFF')][string]$WeekendFlat='',", "[string[]]$SkipEAs=@(),\n    [ValidateSet('','ON','OFF')][string]$WeekendFlat='',")
    s = sub1(s, "$WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat ([bool]$ValidateOnly)   # Calyx Weekend Flat (2026-11-11)\n",
             "$WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat ([bool]$ValidateOnly)   # Calyx Weekend Flat (2026-11-11)\n"
             "$selectedEntries=@(Select-CalyxEntries @($manifest.entries) $SkipEAs ([bool]($ValidateOnly -or -not $Interactive)) 'slug' 'label' 'symbol')   # owner 2026-11-11: one by one\n")
    s = sub1(s, "[ValidateSet('','ON','OFF')][string]$WeekendFlat='',", "[ValidateSet('','ON','OFF')][string]$WeekendFlat='',\n    [ValidateSet('','ON','OFF')][string]$NoOpposite='',")
    s = sub1(s, "$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion ([bool]$ValidateOnly)\n", CNO_PS + "$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion ([bool]$ValidateOnly)\n")
    s = sub1(s, "$WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat ([bool]$ValidateOnly)   # Calyx Weekend Flat (2026-11-11)\n",
             "$WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat ([bool]$ValidateOnly)   # Calyx Weekend Flat (2026-11-11)\n$NoOpposite=Read-CalyxNoOpposite $NoOpposite ([bool]$ValidateOnly)   # Calyx No Opposite (2026-11-17)\n")
    s = sub1(s, "$inputs['FTMOTotalRiskMultiple']=Get-CalyxCapMultiple $TotalRiskCap;$inputs['FTMOSymbolRiskMultiple']=Get-CalyxCapMultiple $SymbolRiskCap",
             "$inputs['FTMOTotalRiskMultiple']=Get-CalyxCapMultiple $TotalRiskCap;$inputs['FTMOSymbolRiskMultiple']=Get-CalyxCapMultiple $SymbolRiskCap;$inputs['InpCalyxNoOpposite']=if($NoOpposite -eq 'ON'){'true'}else{'false'}")
    s = sub1(s, "Nasdaq DI: $NasdaqDIFilter; USDJPY DI: $UsdJpyDIFilter`r`n", "Nasdaq DI: $NasdaqDIFilter; USDJPY DI: $UsdJpyDIFilter`r`nNo-opposite rule: $NoOpposite`r`n")
    s = sub1(s, "foreach($symbol in $aliasMap.Keys){", "foreach($symbol in @($aliasMap.Keys | Where-Object { $_ -in @($selectedEntries | ForEach-Object { [string]$_.symbol }) })){")
    s = sub1(s, "$portfolio=@()\nforeach($entry in $manifest.entries){", "$portfolio=@()\nforeach($entry in $selectedEntries){")
    return s.replace('\n', '\r\n')


def write_installers():
    root = HERE / '1-Step'; root.mkdir(exist_ok=True)
    (root / SCRIPT).write_bytes(installer().encode('utf-8'))
    h = sub1(read(F1S / 'Account-Helpers.ps1'), "throw 'FTMO 1-Step requires a hedging MT5 account", "throw 'Best 1-Step requires a hedging MT5 account")
    (root / 'Account-Helpers.ps1').write_bytes(h.replace('\n', '\r\n').encode('utf-8')); shutil.copy2(F1S / 'probe_account.py', root / 'probe_account.py')
    print('installer + helpers written', flush=True)


def build_noguard():
    """2026-11-17: every wrapper is recompiled from its package source with the Calyx No Opposite shim (InpCalyxNoOpposite, default false = the old
    order path). Inputs / sets = the Core 9 no-guard entries (minus its DI-ON Nasdaq) + the P4 no-guard Nasdaq (DI OFF) and Overnight Bias ORB, as before."""
    c9 = json.loads(read(CORE9_NG / 'Package.json')); p4 = json.loads(read(P4_NG / 'Package.json'))
    for pk in (CORE9_NG, P4_NG):
        for rel, digest in json.loads(read(pk / 'Checksums.json')).items(): assert BL.sha(pk / rel) == digest, ('package altered', pk.name, rel)
    assert BL.sha(CORE9_NG / 'RiskSupport.mqh') == BL.sha(P4_NG / 'RiskSupport.mqh')
    if NOGUARD.exists(): shutil.rmtree(NOGUARD)          # generated package only
    (NOGUARD / 'Experts').mkdir(parents=True); (NOGUARD / 'Sets').mkdir(); entries = []
    pick = [(CORE9_NG, e) for e in c9['entries'] if e['key'] != 'nasdaq-5m-candle-momentum' and e['key'] not in DROPPED] + [(P4_NG, e) for e in p4['entries'] if e['key'] in ('nasdaq-5m-candle-momentum', 'overnight-bias-orb')]
    cno_check(); caches = {}; shutil.copy2(BL.CURRENT / 'RiskSupport.mqh', NOGUARD / 'RiskSupport.mqh')   # the wrappers include ../../RiskSupport.mqh
    flat = ('#property strict\n#include "../RiskSupport.mqh"\n#define OnInit UR_StrategyInit\n#define OnTick UR_StrategyTick\n#include "{inc}"\n#undef OnInit\n#undef OnTick\n'
            'int OnInit(){{if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}}\n'
            'void OnTick(){{if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTick();}}\n')

    def compile_wrapper(slug, family, text):
        folder = NOGUARD / 'Sources' / family; folder.mkdir(parents=True, exist_ok=True)
        for n in ('CalyxNoOpposite.mqh', 'CNO_Trade.mqh'): shutil.copy2(CNO / n, folder / n)
        name = 'Calyx Best1Step - ' + slug; write(folder / (name + '.mq5'), cno_wrapper(text))
        closure = C9.expansion(folder, name + '.mq5')   # wrapper + strategy files (src_*), without the shim files
        assert '<Trade/Trade.mqh>' not in closure and '#include "CNO_Trade.mqh"' in closure and 'CNO_Tick();UR_StrategyTick();' in closure, slug
        assert not re.search(DIRECT_SEND, closure), slug   # every direct OrderSend of the strategy goes through the rule
        BL.compile_ea(folder / (name + '.mq5')); shutil.copy2(folder / (name + '.ex5'), NOGUARD / 'Experts' / (name + '.ex5')); return 'Experts/' + name + '.ex5'

    for root, e in pick:
        slug = e['key']
        if slug == 'nasdaq-5m-candle-momentum': assert 'InpCarryMode' in read(BL.CURRENT / 'Sources/src_7d5ce7953b20.mqh'), 'Nasdaq source must be the REPLACE build'
        if slug in NG_WRAP:
            family = NG_WRAP[slug]; src, prefix = NG_SRC[family]; folder = NOGUARD / 'Sources' / family; folder.mkdir(parents=True, exist_ok=True)
            wrapper = src / (prefix + slug + '.mq5'); body = read(wrapper)
            for inc in re.findall(r'#include\s+"([^"]+)"', body):
                if not inc.startswith('../'): cno_copy(src / inc, folder, caches.setdefault(family, {}))
            expert = compile_wrapper(slug, family, body); source = str(wrapper)
        else:   # overnight-bias-orb: the P4 research source with its asserted edits
            folder = NOGUARD / 'Sources' / 'p4'; folder.mkdir(parents=True, exist_ok=True); inc = P4.flat_include(slug, folder, False, True)
            write(folder / inc, cno_text(read(folder / inc))); expert = compile_wrapper(slug, 'p4', flat.format(inc=inc)); source = 'P4 research source (P4/build.py flat_include)'
        inputs = dict(e['inputs'], InpCalyxNoOpposite='false')
        BL.write(NOGUARD / e['settings'], read(root / e['settings']).rstrip('\r\n') + '\nInpCalyxNoOpposite=false\n')
        entries.append(dict(e, expert=expert, inputs=inputs, from_package=root.name, wrapper_source=source, tested_expert=e['expert'], tested_expert_sha256=BL.sha(root / e['expert'])))
    # UK100 Monday dip: no-guard wrapper (RiskSupport sizing), the FTSE S2 inputs
    folder = NOGUARD / 'Sources' / 'b1'; folder.mkdir(parents=True, exist_ok=True); include = ftse_include(folder, False, True)
    write(folder / include, cno_text(read(folder / include))); name = 'Calyx Best1Step - uk100-monday-dip'
    compile_wrapper('uk100-monday-dip', 'b1', flat.format(inc=include))
    shutil.copy2(BL.CURRENT / 'RiskSupport.mqh', NOGUARD / 'RiskSupport.mqh')
    ukin = dict(FTSE_INPUTS, InpAdaptivePortfolioControls='false', InpPortfolioRiskMode='0', InpPortfolioPercent='0.5', InpPortfolioFixedUSD='50.0', InpPortfolioExpectedLogin='0',
                InpPortfolioExpectedServer='', InpPortfolioExpectedSymbol='', InpPortfolioInstallNonce='')
    BL.write(NOGUARD / 'Sets' / 'uk100-monday-dip.set', '\n'.join(k + '=' + v for k, v in ukin.items()) + '\n')
    ukin['InpCalyxNoOpposite'] = 'false'; BL.write(NOGUARD / 'Sets' / 'uk100-monday-dip.set', '\n'.join(k + '=' + v for k, v in ukin.items()) + '\n')
    entries.append(dict(key='uk100-monday-dip', label=UK['label'], canonical='UK100', period=60, magic=int(ukin['InpMagic']), hourly=False, expert='Experts/' + name + '.ex5',
                        settings='Sets/uk100-monday-dip.set', inputs=ukin, di_input=None, research_source=str(FTSE_SRC), research_sha256=BL.sha(FTSE_SRC)))
    entries.sort(key=lambda e: SLUGS.index(e['key']))
    assert [e['key'] for e in entries] == SLUGS and len({e['magic'] for e in entries}) == len(SLUGS)
    assert next(e for e in entries if e['key'] == 'nasdaq-5m-candle-momentum')['inputs']['InpRequireDIAgreement'] == 'false'
    assert next(e for e in entries if e['key'] == 'usdjpy-london-open-momentum')['inputs']['InpRequireDIAgreement'] == 'true'
    for name in ('RiskSupport.mqh', 'Installer-Helpers.ps1', 'Probe-MT5.py'): shutil.copy2(BL.CURRENT / name, NOGUARD / name)
    text = BL.read(BL.CURRENT / 'Install-Portfolio.ps1')
    for old, new, count in [('.Count -ne 17', f'.Count -ne {len(SLUGS)}', 3), ('return $ready -eq 17', f'return $ready -eq {len(SLUGS)}', 1), ('17-chart', f'{len(SLUGS)}-chart', 1), ("'CALYX - CURRENT14 + ORB05 PORTFOLIO'", "'CALYX - BEST 1-STEP PORTFOLIO (NO GUARD)'", 1),
                            ('No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.',
                             'NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades. 3 Way Gold runs its breakout module only.', 1),
                            ("$answer=(Read-Host \"$label DI filter ON or OFF [ON]\").Trim().ToUpperInvariant(); if (-not $answer) { $answer='ON' }",
                             "$tested=if ($parameter -eq 'NasdaqDIFilter') {'OFF'} else {'ON'}; $answer=(Read-Host \"$label DI filter ON or OFF (tested $tested) [$tested]\").Trim().ToUpperInvariant(); if (-not $answer) { $answer=$tested }", 1),
                            ('DI OFF changes the tested preset. USDJPY ADX20 remains enabled.', 'Best 1-Step was tested with Nasdaq DI OFF and USDJPY DI ON (ADX20 kept).', 1),
                            ("XAUUSD = @('XAUUSD', 'GOLD') }", "XAUUSD = @('XAUUSD', 'GOLD'); UK100 = @(" + ', '.join("'" + a + "'" for a in UK_ALIASES) + ") }", 1),
                            ("foreach ($canonical in @('USDJPY', 'USTEC', 'XAUUSD')) {", "foreach ($canonical in @('USDJPY', 'USTEC', 'XAUUSD', 'UK100')) {", 1),
                            ('CalyxCurrent14ORB05Setup', 'CalyxBest1StepSetup', None)]:
        found = text.count(old); assert found and (count is None or found == count), (old, found)
        text = text.replace(old, new)
    sel = (LIVE / 'Calyx-SelectEAs.ps1').read_text(encoding='utf-8').replace('\r\n', '\n').rstrip('\n')
    for old, new in [("    [ValidateSet('', 'ON', 'OFF')][string]$WeekendFlat = '',", "    [string[]]$SkipEAs = @(),\n    [ValidateSet('', 'ON', 'OFF')][string]$WeekendFlat = '',"),
                     ("function Read-CalyxNasdaqVersion", sel + "\n\nfunction Read-CalyxNasdaqVersion"),
                     ("    $WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat $false   # Calyx Weekend Flat (2026-11-11)\n",
                      "    $WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat $false   # Calyx Weekend Flat (2026-11-11)\n"
                      "    $package.entries=@(Select-CalyxEntries @($package.entries) $SkipEAs $false 'key' 'label' 'canonical')   # owner 2026-11-11: one by one\n"),
                     ("foreach ($canonical in @('USDJPY', 'USTEC', 'XAUUSD', 'UK100')) {", "foreach ($canonical in @(@('USDJPY', 'USTEC', 'XAUUSD', 'UK100') | Where-Object { $_ -in @($Package.entries | ForEach-Object { [string]$_.canonical }) })) {"),
                     (f"return $ready -eq {len(SLUGS)}", "return $ready -eq @($Items).Count"),
                     ("    [ValidateSet('', 'ON', 'OFF')][string]$WeekendFlat = '',\n", "    [ValidateSet('', 'ON', 'OFF')][string]$WeekendFlat = '',\n    [ValidateSet('', 'ON', 'OFF')][string]$NoOpposite = '',\n"),
                     ("function Read-CalyxNasdaqVersion", CNO_PS + "\nfunction Read-CalyxNasdaqVersion"),
                     ("    $WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat $false   # Calyx Weekend Flat (2026-11-11)\n",
                      "    $WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat $false   # Calyx Weekend Flat (2026-11-11)\n    $script:NoOpposite=Read-CalyxNoOpposite $NoOpposite $false   # Calyx No Opposite (2026-11-17)\n"),
                     ("    $inputs['InpPortfolioInstallNonce'] = [string]$InstallNonce\n",
                      "    $inputs['InpPortfolioInstallNonce'] = [string]$InstallNonce\n    $inputs['InpCalyxNoOpposite'] = if ($script:NoOpposite -eq 'ON') { 'true' } else { 'false' }   # Calyx No Opposite (2026-11-17)\n")]:
        assert text.count(old) == 1, (old[:60], text.count(old)); text = text.replace(old, new)
    BL.write(NOGUARD / 'Install-Portfolio.ps1', text)
    BL.save(NOGUARD / 'Package.json', dict(version=f'{VERSION}-NOGUARD', profile='Calyx BEST1STEP NOGUARD', entries=entries, orb_keys=['us100-selective-orb-v3'], default_percent=0.5, required_margin_mode=2, news=False, ftmo_guard=False,
                                           shared_daily_stop=False, adaptive_governor=False, selection='Owner 2026-11-11: Core 9 + P4 (Best 1-Step Search 2026-11-11, in-sample, selection-biased); Sell Nasdaq removed; UK100 Monday dip added (Best 1-Step UK100 Monday 2026-11-11). Owner 2026-11-17: Gold Band Wave and XAU Squeeze removed (last-year review, Multi Firm Funded 2026-11-17).', compatibility=c9['compatibility'],
                                           no_live_installation=True, sources=dict(core9=c9['version'], p4=p4['version'])))
    paths = [NOGUARD / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')] + sorted((NOGUARD / 'Experts').glob('*.ex5')) + sorted((NOGUARD / 'Sets').glob('*.set'))
    BL.save(NOGUARD / 'Checksums.json', {str(p.relative_to(NOGUARD)).replace(chr(92), '/'): BL.sha(p) for p in paths}); print('Built no guard,', len(entries), 'EAs (all wrappers recompiled with the Calyx No Opposite shim)', flush=True)


def main():
    anyb = json.loads(read(ANY / 'PACKAGE.json')); edge = json.loads(read(EDGE / 'Package.json'))
    for name, digest in anyb['files'].items(): assert sha(ANY / 'package' / name) == digest, ('package altered', name)
    sources = (ANY, F1S, EDGE, BL.CURRENT, CORE9_NG, P4_NG, LIVE / 'Core 9', LIVE / 'P4', P4.VIDEO_SRC.parent, P4.GBW_SRC.parent, FTSE_SRC.parent)
    before = {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()}
    build_noguard(); build_guarded(anyb, edge); write_installers()
    assert {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()} == before, 'source packages must stay unchanged'
    print('DONE', VERSION, 'no MT5 terminal touched', flush=True)


if __name__ == '__main__':
    write_installers() if sys.argv[1:] == ['installer'] else main()
