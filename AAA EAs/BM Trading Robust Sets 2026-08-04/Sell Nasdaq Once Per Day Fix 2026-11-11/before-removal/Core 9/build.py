"""Build the Core 9 profile (owner 2026-11-05): Nasdaq 5M, USDJPY London, 3 Way Gold breakout only, Sell Nasdaq 15min, EMA3, ORB VP Volume Confirmed, XAU Squeeze,
US100 Selective ORB V3 (0.5R), XAU RSI VWAP, exactly the stream tested in Merged E10 FTMO17 2026-11-05 (merged.py build_c9). Offline: MetaEditor compile only, no MT5 terminal.

Three launchers:
  * Core 9 - FTMO 1-Step guard.bat -> 1-Step/  the ftmo 1_step guard (10% EOD-trailing, 3% daily, best day <= 50%), own state key C9O, installer generated from ftmo 1_step's
  * Core 9 - FTMO 2-Step guard.bat -> 2-Step/  the broker-neutral Prop Ready guard (FTMO 2-step limits), own state key C9T, installer generated from Best Prop 15's
  * Core 9 - no guard.bat          -> ../Packages/Core9  no guard, the already tested Current 14 / Edge 10 wrappers (no recompile), installer as Mixed 22

Guarded builds: seven EAs are the FTMO-AnyBroker wrappers and SETs (integrity-checked, never written); Sell Nasdaq and ORB VP Volume Confirmed get new wrappers from their production
sources with the Edge 10 SETs, built the way the FTMO package was (guarded CTrade shim).

SELL NASDAQ HOLDS ITS STOP IN THE EA (guarded builds only). The production EA places a sell stop and these guards refuse every pending order, and any pending order on the account also
blocks all other EAs. So the guarded source sells at market on the first tick with bid <= the level, at the same stop and target. Production source and no-guard EX5 keep the real sell stop.
A restart while armed loses that day's trade (the day stays marked as attempted). parity/ holds the same change without the guard for parity.py to compare against production.

python build.py            full build (recompiles 18 wrappers + 1 parity EA)
python build.py installer  regenerate the installers + helpers only (no compile)
Run from AAA EAs/EA store:  uv run python "<this>" """
import hashlib, json, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent; LIVE = HERE.parent; ROOT = LIVE.parent
sys.path.insert(0, str(ROOT.parent / 'EA store'))
from tools import build_live_profiles as BL  # noqa: E402

ANY = LIVE / 'Packages/FTMO-AnyBroker'; F1S = LIVE / 'ftmo 1_step'; BP15 = LIVE / 'Best Prop 15 Portfolio 2026-10-29'; EDGE = LIVE / 'Packages/Edge10'; NOGUARD = LIVE / 'Packages/Core9'; PARITY = HERE / 'parity'
EDITOR = ROOT / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'
VERSION = 'CORE9-20261105'
FROM_ANY = ['nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum', '3-way-gold', 'ema3', 'xau-squeeze-momentum-standard', 'us100-selective-orb-v3', 'xau-rsi-vwap']
FROM_EDGE = {'sell-nasdaq-15min': ('Sell Nasdaq 15min', 'USTEC', 'M15'), 'orb-volume-profile-volume-confirmed': ('ORB Volume Profile Volume Confirmed', 'XAUUSD', 'M5')}
FROM_CURRENT = ['nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum', 'ema3', 'xau-squeeze-momentum-standard', 'us100-selective-orb-v3', 'xau-rsi-vwap']   # no guard
FROM_EDGE_NOGUARD = ['3-way-gold', 'sell-nasdaq-15min', 'orb-volume-profile-volume-confirmed']
SLUGS = FROM_ANY + list(FROM_EDGE)
UNARMED = dict(FTMOExpectedLogin='0', FTMOExpectedServer='', FTMOExpectedSymbol='', FTMOExpectedCurrency='', FTMOReferenceBalance='0', FTMOStartUtcTime='0')
RULES_1STEP = dict(FTMO1TargetPercent='10.0', FTMO1MaxLossPercent='10.0', FTMO1DailyLossPercent='3.0', FTMO1FloorBufferPercent='2.0', FTMO1DailyReservePercent='2.5', FTMO1BestDayCapPercent='4.5')
VARIANTS = {'1-Step': dict(tag='C9O', ruleset='FTMO_1STEP', script='Install-Core9-1Step.ps1'), '2-Step': dict(tag='C9T', ruleset='FTMO_2STEP', script='Install-Core9-2Step.ps1')}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    raw = Path(p).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')


def write(p, text):
    Path(p).parent.mkdir(parents=True, exist_ok=True); Path(p).write_text(text, encoding='utf-8')


def sub1(text, old, new):
    assert text.count(old) == 1, ('expected exactly one occurrence', old[:120], text.count(old))
    return text.replace(old, new)


def set_values(path):
    out = {}
    for line in read(path).splitlines():
        if '=' in line and not line.startswith(';'):
            k, v = line.split('=', 1); out[k.strip()] = v.strip().split('||')[0]
    return out


def virtual_stop(text):
    """Sell Nasdaq: the EA holds the stop, see the module docstring. Every edit is asserted against the production text."""
    text = sub1(text, 'bool HasPendingOrder()\n{\n', """// Core 9 guarded build: these guards refuse pending orders, so the sell stop is held here and sold at market on the first tick with bid <= the level.
double g_vstop_entry=0.0,g_vstop_stop=0.0,g_vstop_target=0.0,g_vstop_lots=0.0;
datetime g_vstop_expiry=0;
string VStopKey(){return "C9VS_"+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"_"+IntegerToString(InpMagic);}

bool HasPendingOrder()
{
   if(g_vstop_entry>0.0) return true;
""")
    text = sub1(text, 'bool AttemptedToday(const MqlDateTime &now_ny)\n{\n', """bool AttemptedToday(const MqlDateTime &now_ny)
{
   if(GlobalVariableCheck(VStopKey()) && (long)GlobalVariableGet(VStopKey())==now_ny.year*10000+now_ny.mon*100+now_ny.day) return true;
""")
    text = sub1(text, 'void DeletePendingOrders()\n{\n', 'void DeletePendingOrders()\n{\n   g_vstop_entry=0.0;\n')
    text = sub1(text, """   bool ok=trade.SellStop(lots,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expiry,"Sell Nasdaq dynamic exit research");
   if(!ok) Print("Sell stop failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   return ok;
}
""", """   g_vstop_entry=entry; g_vstop_stop=stop; g_vstop_target=target; g_vstop_lots=lots; g_vstop_expiry=expiry;
   GlobalVariableSet(VStopKey(),now_ny.year*10000+now_ny.mon*100+now_ny.day);
   return true;
}

void CheckVirtualStop()
{
   if(g_vstop_entry<=0.0) return;
   if(TimeCurrent()>=g_vstop_expiry) { g_vstop_entry=0.0; return; }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.bid<=0.0 || tick.bid>g_vstop_entry) return;
   g_vstop_entry=0.0;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   if(!trade.Sell(g_vstop_lots,_Symbol,tick.bid,g_vstop_stop,g_vstop_target,"Sell Nasdaq dynamic exit research"))
      Print("Sell at the held stop failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}
""")
    return sub1(text, 'void OnTick()\n{\n   ManageTimeAndInvalidation();\n', 'void OnTick()\n{\n   ManageTimeAndInvalidation();\n   CheckVirtualStop();\n')


def compile_ea(path):
    log = path.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    text = read(log); assert '0 errors, 0 warnings' in text, text[-3000:]
    ex5 = path.with_suffix('.ex5'); assert ex5.is_file() and ex5.stat().st_mtime >= started - 2
    print('COMPILED', path.stem, flush=True)


def graph_copy(path, target, cache, shim, transform=None):
    """Copy an EA's include graph flat into target. shim=True swaps CTrade and OrderSend for the guarded versions, as the FTMO package build does."""
    path = path.resolve()
    if path in cache: return cache[path]
    name = 'src_core9_' + hashlib.sha256(str(path.relative_to(ROOT)).encode()).hexdigest()[:12] + '.mqh'; cache[path] = name
    text = read(path)
    if transform: text = transform(text)
    if shim:
        text = text.replace('#include <Trade/Trade.mqh>', '#include "FTMO_Trade.mqh"'); text = re.sub(r'\bOrderSend\(', 'FTMOOrderSend(', text)
    text = re.sub(r'#include\s+"([^"]+)"', lambda m: '#include "FTMO_Trade.mqh"' if m[1] == 'FTMO_Trade.mqh' else '#include "' + graph_copy(path.parent / m[1].replace(chr(92), '/'), target, cache, shim) + '"', text)
    write(target / name, text); return name


def expansion(folder, name, seen=None):
    seen = set() if seen is None else seen
    if name in seen: return ''
    seen.add(name); body = read(folder / name)
    return body + '\n' + '\n'.join(expansion(folder, c, seen) for c in re.findall(r'#include "(src_[^"]+)"', body))


def guard_text(variant):
    if variant == '1-Step':
        g = read(F1S / 'CalyxFTMOGuard.mqh'); assert sha(F1S / 'CalyxFTMOGuard.mqh') == json.loads(read(F1S / 'PACKAGE.json'))['guard_sha'], 'ftmo 1_step guard altered'
        return sub1(g, 'return "F1S"+IntegerToString(FTMOExpectedLogin)', 'return "C9O"+IntegerToString(FTMOExpectedLogin)')
    g = read(ANY / 'CalyxFTMOGuard.mqh'); assert sha(ANY / 'CalyxFTMOGuard.mqh') == json.loads(read(ANY / 'PACKAGE.json'))['guard_sha'], 'any-broker guard altered'
    return sub1(g, 'return "PR9"+IntegerToString(FTMOExpectedLogin)', 'return "C9T"+IntegerToString(FTMOExpectedLogin)')


def build_guarded(variant, anyb, edge):
    cfg = VARIANTS[variant]; root = HERE / variant; pkg = root / 'package'; tag = cfg['tag']
    for d in (pkg, root / 'EAs', root / 'Sets'):
        if d.exists(): shutil.rmtree(d)                  # this profile's own generated folders only
        d.mkdir(parents=True)
    guard = guard_text(variant); write(root / 'CalyxFTMOGuard.mqh', guard); write(pkg / 'CalyxFTMOGuard.mqh', guard)
    for f in (ANY / 'package').iterdir():
        if f.suffix == '.mqh' and f.name != 'CalyxFTMOGuard.mqh': shutil.copy2(f, pkg / f.name)
    entries = []; magics = {}; cache = {}
    for slug in SLUGS:
        stem = f'{tag}-{slug}'
        if slug in FROM_ANY:
            e = next(x for x in anyb['entries'] if x['slug'] == slug); label, symbol, timeframe = e['label'], e['symbol'], e['timeframe']
            write(pkg / f'{stem}.mq5', read(ANY / 'package' / (Path(e['expert']).stem + '.mq5'))); values = set_values(ANY / 'package' / e['settings']); source = ('FTMO-AnyBroker', e['expert'], e['settings'])
        else:
            e = next(x for x in edge['entries'] if x['key'] == slug); label, symbol, timeframe = FROM_EDGE[slug]; assert e['canonical'] == symbol
            include = graph_copy(Path(e['production_source']), pkg, cache, True, virtual_stop if slug == 'sell-nasdaq-15min' else None)
            code = ('#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#define OnTimer FTMO_StrategyTimer\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
                    'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\nvoid OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
            if re.search(r'void\s+OnTimer\s*\(', expansion(pkg, include)): code += 'void OnTimer(){ if(FTMOPulse())FTMO_StrategyTimer(); }\n'
            write(pkg / f'{stem}.mq5', code); values = {k: str(v) for k, v in e['inputs'].items()}; source = ('Edge10', e['production_source'], e['settings'])
            assert 'SellStop' not in read(pkg / include) or slug != 'sell-nasdaq-15min' or 'trade.SellStop(' not in read(pkg / include)
        compile_ea(pkg / f'{stem}.mq5')
        assert values['InpRiskPercent'] == '0.5' and values.get('InpAdaptivePortfolioControls') == 'false', slug
        if slug == 'us100-selective-orb-v3': assert values['InpRewardRisk'] == '0.5'
        if slug == '3-way-gold':
            assert values['InpMarketEntries'] == 'true'; values.update(InpEnableMomentum='false', InpEnableBreakout='true', InpEnableTurnOfMonth='false')
        values.update(FTMOAllocationMode='1', FTMOAllocationValue='0.5', FTMOPhase='1', **UNARMED)
        if variant == '1-Step': values.update(RULES_1STEP)
        magic = values.get('InpMagic') or values.get('InpMagicBase'); assert magic and magic not in magics, ('magic clash', slug, magic); magics[magic] = slug
        write(pkg / f'{stem}.set', '\n'.join(f'{k}={v}' for k, v in values.items()) + '\n')
        shutil.copy2(pkg / f'{stem}.ex5', root / 'EAs' / f'{stem}.ex5'); shutil.copy2(pkg / f'{stem}.set', root / 'Sets' / f'{stem}.set')
        entries.append(dict(slug=slug, label=label, symbol=symbol, timeframe=timeframe, expert=f'{stem}.ex5', settings=f'{stem}.set', magic=magic, source_package=source[0], source_expert=source[1], source_settings=source[2], expert_sha=sha(pkg / f'{stem}.ex5'), settings_sha=sha(pkg / f'{stem}.set')))
    files = {p.name: sha(p) for p in pkg.iterdir() if p.is_file() and p.suffix != '.log'}
    out = dict(version=f'{VERSION}-{variant}', ruleset=cfg['ruleset'], entries=entries, news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True, reference_mode='FRESH_BASELINE_EVERY_RUN', default_phase='Challenge',
               risk_cap_fraction=0.005, total_risk_fraction=0.0225, symbol_risk_fraction=0.015, strategy_risk_percent='0.5 (installer: 1.5x the chosen risk, max 5)', nasdaq_di_default='ON', usdjpy_di_default='ON',
               sell_nasdaq='stop held in the EA, sold at market (these guards refuse pending orders)', guard_sha=sha(root / 'CalyxFTMOGuard.mqh'), guard_state_prefix=tag, source_package=dict(name=ANY.name, version=anyb['version'], guard_sha=anyb['guard_sha']), files=files)
    write(root / 'PACKAGE.json', json.dumps(out, indent=2) + '\n'); print('Built', variant, len(entries), 'EAs', flush=True)


ROSTER = ',\n        '.join(', '.join(f"'{x}'" for x in SLUGS[i:i + 4]) for i in range(0, len(SLUGS), 4))


def roster_sub(text):
    new, n = re.subn(r"\$expected=@\('[^)]*\)", lambda m: '$expected=@(' + ROSTER + ')', text, count=1); assert n == 1; return new


def depth_sub(text):
    text = sub1(text, "$PackageRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\\..'))", "$PackageRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\\..\\..'))")
    return sub1(text, ". (Join-Path $PSScriptRoot '..\\Calyx-InstallChoices.ps1')", ". (Join-Path $PSScriptRoot '..\\..\\Calyx-InstallChoices.ps1')")


def installer_1step():
    s = read(F1S / 'Install-FTMO1Step.ps1'); s = roster_sub(depth_sub(s))
    for a, b in [("# ftmo 1_step 2026-11-04: the 17 FTMO-guarded EAs with the FTMO 1-Step guard (10% EOD-trailing max loss, 3% daily, best day <= 50%).", "# Core 9 2026-11-05: nine EAs with the FTMO 1-Step guard (10% EOD-trailing max loss, 3% daily, best day <= 50%)."),
                 ("# GENERATED by build.py from Best Prop Portfolio 2026-10-20/Install-BestProp.ps1; do not edit by hand.", "# GENERATED by Core 9/build.py from ftmo 1_step/Install-FTMO1Step.ps1; do not edit by hand."),
                 ("if($manifest.entries.Count -ne 17 -or", "if($manifest.entries.Count -ne 9 -or"), ("throw 'FTMO 1-Step roster changed.'", "throw 'Core 9 roster changed.'"),
                 ("throw 'All five ORBs must retain 0.5R.'", "throw 'US100 Selective ORB V3 must retain 0.5R.'"),
                 ("Write-Host 'FTMO 1-STEP - 17 guarded EAs; FTMO 1-Step rules:", "Write-Host 'CORE 9, FTMO 1-STEP - nine guarded EAs; FTMO 1-Step rules:"),
                 ("Write-Host 'FTMO 1-STEP: 17 EAs / five ORBs at 0.5R / any MT5 hedging account (built for FTMO 1-Step).'", "Write-Host 'CORE 9, FTMO 1-STEP: nine EAs / 3 Way Gold breakout only / any MT5 hedging account (built for FTMO 1-Step).'"),
                 ("Write-Host 'PASS: 17 integrity-checked guarded EAs (FTMO 1-Step rules; default 0.5% risk, 4.5x total, 3x per symbol); ORBs 0.5R; Nasdaq DI default ON. No account accessed.'", "Write-Host 'PASS: 9 integrity-checked guarded EAs (FTMO 1-Step rules; default 0.5% risk, 4.5x total, 3x per symbol); Nasdaq DI default ON. No account accessed.'"),
                 ('("MQL5\\Files\\Calyx-FTMO1Step-$login-$serverHash.json")', '("MQL5\\Files\\Calyx-Core9-1Step-$login-$serverHash.json")'), ("$ProfileName='Calyx-FTMO1Step-'+$login", "$ProfileName='Calyx-Core9-1Step-'+$login"),
                 ('$expected="FTMO 1STEP $login $currency $Phase"', '$expected="CORE9 1STEP $login $currency $Phase"'), ("'FTMO 1-Step installed profile'", "'Core 9 1-Step installed profile'"), ("'.ftmo1step-backup-'", "'.core9-1step-backup-'"),
                 ('"Portfolio: ftmo 1_step (17 EAs, FTMO 1-Step guard)', '"Portfolio: Core 9 (nine EAs, FTMO 1-Step guard)'), ('Review all 17 charts and inputs', 'Review all nine charts and inputs')]:
        s = sub1(s, a, b)
    return s.replace('\n', '\r\n')


def installer_2step():
    s = read(BP15 / 'Install-BestProp15.ps1'); s = roster_sub(depth_sub(s))
    for a, b in [("# Best Prop 15 Portfolio 2026-10-29: Best Prop 9 + EMA3, 3 Way Gold, Gold Overnight and the three DMCs, same guard (cap = chosen risk).", "# Core 9 2026-11-05: nine EAs with the broker-neutral Prop Ready guard (FTMO 2-step limits, cap = chosen risk)."),
                 ("# GENERATED by build.py from Best Prop Portfolio 2026-10-20/Install-BestProp.ps1; do not edit by hand.", "# GENERATED by Core 9/build.py from Best Prop 15 Portfolio 2026-10-29/Install-BestProp15.ps1; do not edit by hand."),
                 ("[double]$RiskValue=1.0,", "[double]$RiskValue=0.75,"), ("[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',", "[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',"),
                 ("if($manifest.entries.Count -ne 15 -or", "if($manifest.entries.Count -ne 9 -or"),
                 ("$manifest.risk_cap_fraction -ne 0.01 -or $manifest.total_risk_fraction -ne 0.045 -or $manifest.symbol_risk_fraction -ne 0.03 -or", "$manifest.risk_cap_fraction -ne 0.005 -or $manifest.total_risk_fraction -ne 0.0225 -or $manifest.symbol_risk_fraction -ne 0.015 -or $manifest.ruleset -ne 'FTMO_2STEP' -or"),
                 ("throw 'Best Prop 15 roster changed.'", "throw 'Core 9 roster changed.'"),
                 ("$inputs['InpRiskPercent'] -ne '1.0' -or $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Distributed settings must be unarmed with InpRiskPercent=1.0.'}", "$inputs['InpRiskPercent'] -ne '0.5' -or $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Distributed settings must be unarmed with InpRiskPercent=0.5.'}"),
                 ("throw 'All five ORBs must retain 0.5R.'", "throw 'US100 Selective ORB V3 must retain 0.5R.'"),
                 ("Write-Host 'BEST PROP 15 PORTFOLIO - fifteen EAs; you choose the risk per trade (max 2% of the starting balance) and the DI filters.'", "Write-Host 'CORE 9, FTMO 2-STEP - nine guarded EAs; you choose the phase, the risk per trade (max 2% of the starting balance), the Nasdaq stop, the DI filters and the open-risk caps.'"),
                 ("'Risk per trade, % of current equity, e.g. 0.25 / 0.5 / 1.0 / 2.0 (max 2) [1.0]'", "'Risk per trade, % of current equity: 0.5 / 0.75 (tested best) / 1.0 (max 2) [0.75]'"),
                 ("'Risk per trade, fixed amount in the account currency, e.g. 500 (max 2% of the starting balance) [100]'", "'Risk per trade, fixed amount in the account currency, e.g. 750 (max 2% of the starting balance) [750]'"),
                 ("elseif($RiskMode -eq 'PERCENT'){1.0}else{100.0}", "elseif($RiskMode -eq 'PERCENT'){0.75}else{750.0}"),
                 ("(Read-Host 'Nasdaq 5M DI filter ON or OFF [OFF]')", "(Read-Host 'Nasdaq 5M DI filter ON or OFF [ON]')"), ("        if(-not $answer){$answer='OFF'}\n", "        if(-not $answer){$answer='ON'}\n"),
                 ("Write-Host 'BEST PROP 15 PORTFOLIO: fifteen EAs / five ORBs at 0.5R / broker-neutral MT5 hedging profile.'", "Write-Host 'CORE 9, FTMO 2-STEP: nine EAs / 3 Way Gold breakout only / broker-neutral MT5 hedging profile.'"),
                 ("Write-Host 'PASS: 15 integrity-checked guarded EAs (1% cap, 4.5% total, 3% per symbol); ORBs 0.5R; Nasdaq DI default OFF. No account accessed.'", "Write-Host 'PASS: 9 integrity-checked guarded EAs (default 0.75% risk, 4.5x total, 3x per symbol); Nasdaq DI default ON. No account accessed.'"),
                 ('("MQL5\\Files\\Calyx-BestProp15-$login-$serverHash.json")', '("MQL5\\Files\\Calyx-Core9-2Step-$login-$serverHash.json")'), ("$ProfileName='Calyx-BestProp15-'+$login", "$ProfileName='Calyx-Core9-2Step-'+$login"),
                 ('$expected="BEST PROP 15 $login $currency $Phase"', '$expected="CORE9 2STEP $login $currency $Phase"'), ("'Best Prop 15 installed profile'", "'Core 9 2-Step installed profile'"), ("'.best-prop15-backup-'", "'.core9-2step-backup-'"),
                 ('"Portfolio: Best Prop 15 Portfolio 2026-10-29 (fifteen EAs)', '"Portfolio: Core 9 (nine EAs, FTMO 2-step guard)'), ('Review all fifteen charts and inputs', 'Review all nine charts and inputs')]:
        s = sub1(s, a, b)
    return s.replace('\n', '\r\n')


def write_installers():
    (HERE / '1-Step' / VARIANTS['1-Step']['script']).write_bytes(installer_1step().encode('utf-8')); (HERE / '2-Step' / VARIANTS['2-Step']['script']).write_bytes(installer_2step().encode('utf-8'))
    h1 = sub1(read(F1S / 'Account-Helpers.ps1'), "throw 'FTMO 1-Step requires a hedging MT5 account", "throw 'Core 9 requires a hedging MT5 account"); h2 = sub1(read(BP15 / 'Account-Helpers.ps1'), "throw 'Best Prop 15 requires a hedging MT5 account", "throw 'Core 9 requires a hedging MT5 account")
    (HERE / '1-Step/Account-Helpers.ps1').write_bytes(h1.replace('\n', '\r\n').encode('utf-8')); (HERE / '2-Step/Account-Helpers.ps1').write_bytes(h2.replace('\n', '\r\n').encode('utf-8'))
    shutil.copy2(F1S / 'probe_account.py', HERE / '1-Step/probe_account.py'); shutil.copy2(BP15 / 'probe_account.py', HERE / '2-Step/probe_account.py')
    print('installers + helpers written', flush=True)


def build_noguard(cur, edge):
    assert BL.sha(BL.CURRENT / 'RiskSupport.mqh') == BL.sha(EDGE / 'RiskSupport.mqh'), 'the two packages size trades differently'
    if NOGUARD.exists(): shutil.rmtree(NOGUARD)          # generated package only
    (NOGUARD / 'Experts').mkdir(parents=True); (NOGUARD / 'Sets').mkdir(); entries = []
    for root, e in [(BL.CURRENT, next(x for x in cur['entries'] if x['key'] == k)) for k in FROM_CURRENT] + [(EDGE, next(x for x in edge['entries'] if x['key'] == k)) for k in FROM_EDGE_NOGUARD]:
        shutil.copy2(root / e['expert'], NOGUARD / e['expert']); shutil.copy2(root / e['settings'], NOGUARD / e['settings'])
        entries.append({k: v for k, v in e.items() if k not in ('source', 'production_source', 'production_sha256')})
    assert sorted(e['key'] for e in entries) == sorted(SLUGS) and len({e['magic'] for e in entries}) == 9
    three = next(e for e in entries if e['key'] == '3-way-gold')['inputs']; assert three['InpMarketEntries'] == 'true' and three['InpEnableBreakout'] == 'true' and three['InpEnableMomentum'] == 'false' and three['InpEnableTurnOfMonth'] == 'false'
    assert next(e for e in entries if e['key'] == 'us100-selective-orb-v3')['inputs']['InpRewardRisk'] == '0.5'
    for name in ('RiskSupport.mqh', 'Installer-Helpers.ps1', 'Probe-MT5.py'): shutil.copy2(BL.CURRENT / name, NOGUARD / name)
    text = BL.read(BL.CURRENT / 'Install-Portfolio.ps1')
    for old, new, count in [('.Count -ne 17', '.Count -ne 9', 3), ('return $ready -eq 17', 'return $ready -eq 9', 1), ('17-chart', '9-chart', 1), ("'CALYX - CURRENT14 + ORB05 PORTFOLIO'", "'CALYX - CORE 9 PORTFOLIO (NO GUARD)'", 1),
                            ('No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.',
                             'NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades. 3 Way Gold runs its breakout module only.', 1),
                            ('CalyxCurrent14ORB05Setup', 'CalyxCore9Setup', None)]:
        found = text.count(old); assert found and (count is None or found == count), (old, found)
        text = text.replace(old, new)
    BL.write(NOGUARD / 'Install-Portfolio.ps1', text)
    BL.save(NOGUARD / 'Package.json', dict(version=f'{VERSION}-NOGUARD', profile='Calyx CORE9 NOGUARD', entries=entries, orb_keys=['us100-selective-orb-v3'], default_percent=0.5, required_margin_mode=2, news=False, ftmo_guard=False, shared_daily_stop=False, adaptive_governor=False,
                                            selection='Owner 2026-11-05: core_pick.py list + XAU RSI VWAP, tested in Merged E10 FTMO17 2026-11-05 (in-sample, selection-biased).', compatibility=cur['compatibility'], no_live_installation=True, sources=dict(current14=cur['version'], edge10=edge['version'])))
    paths = [NOGUARD / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')] + sorted((NOGUARD / 'Experts').glob('*.ex5')) + sorted((NOGUARD / 'Sets').glob('*.set'))
    BL.save(NOGUARD / 'Checksums.json', {str(p.relative_to(NOGUARD)).replace(chr(92), '/'): BL.sha(p) for p in paths}); print('Built no guard, 9 EAs (no recompile)', flush=True)


def build_parity(edge):
    if PARITY.exists():
        for p in PARITY.glob('src_core9_*.mqh'): p.unlink()
    e = next(x for x in edge['entries'] if x['key'] == 'sell-nasdaq-15min'); include = graph_copy(Path(e['production_source']), PARITY, {}, False, virtual_stop)
    write(PARITY / 'Sell Nasdaq Held Stop EA.mq5', '#property strict\n#include "' + include + '"\n'); compile_ea(PARITY / 'Sell Nasdaq Held Stop EA.mq5')


def main():
    anyb = json.loads(read(ANY / 'PACKAGE.json')); edge = json.loads(read(EDGE / 'Package.json')); cur = json.loads(read(BL.CURRENT / 'Package.json'))
    for name, digest in anyb['files'].items(): assert sha(ANY / 'package' / name) == digest, ('package altered', name)
    sources = (ANY, F1S, BP15, EDGE, BL.CURRENT); before = {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()}
    build_noguard(cur, edge); build_parity(edge)
    for v in VARIANTS: build_guarded(v, anyb, edge)
    write_installers()
    assert {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()} == before, 'source packages must stay unchanged'
    print('DONE', VERSION, 'no MT5 terminal touched', flush=True)


if __name__ == '__main__':
    write_installers() if sys.argv[1:] == ['installer'] else main()
