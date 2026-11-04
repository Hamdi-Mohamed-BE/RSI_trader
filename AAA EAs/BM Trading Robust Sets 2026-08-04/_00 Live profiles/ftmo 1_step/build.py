"""Build the "ftmo 1_step" profile (owner 2026-11-04: "create new profile call it ftmo 1_step which will obey all the ftmo 1step rules
10% max DD and 3% max DD and consistency day of 50%"). Offline: MetaEditor compile only, no MT5 terminal.

Strategies = the 17 FTMO-guarded EAs of Packages/FTMO-AnyBroker (same wrappers / sources / SETs, integrity-checked, never written).
Guard = the broker-neutral Prop Ready guard of that package with the FTMO 1-Step rules (ftmo.com trading objectives, read 2026-11-03):
  * max loss 10% of the initial capital, END-OF-DAY TRAILING: floor = highest Prague-midnight balance since the install (or the initial
    capital) - 10%; it only rises. Equity at/below the floor latches a breach stop;
  * max daily loss 3% of the initial capital from the midnight balance; equity at/below it latches a breach stop;
  * guard margins: new entries need projected equity >= floor + 2% (FTMO1FloorBufferPercent) and projected daily loss <= 2.5%
    (FTMO1DailyReservePercent; the day also latches there);
  * best-day (consistency) rule: no new entries for the rest of the day once today's P&L (equity - midnight balance) reaches 4.5% of
    the initial capital (FTMO1BestDayCapPercent; < 50% of the 10% target), and in Challenge mode new entries stop at +10% only once
    the best day <= 50% of total profit; otherwise the EAs keep trading until it holds;
  * unchanged: per-entry cap = chosen risk, total 4.5x / per symbol 3x (install choices), 7 entries / 3 losing positions a day,
    80% margin, SL required, no pending orders, account / symbol locks. Admission guard only: no automatic liquidation.
Own state key "F1S" (never shares latches with Prop Ready / any-broker on the same login). Installer generated from Best Prop 9's
interactive installer by asserted substitutions.

python build.py            full build (recompiles 17 wrappers)
python build.py installer  regenerate the installer + helpers only (no compile)
"""
import hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent
ROOT = LIVE.parent                                           # BM Trading Robust Sets 2026-08-04
ANY = LIVE / 'Packages' / 'FTMO-AnyBroker'
BP9 = LIVE / 'Best Prop Portfolio 2026-10-20'
PKG = HERE / 'package'; EAS = HERE / 'EAs'; SETS = HERE / 'Sets'
EDITOR = ROOT / '_Backtests' / 'MT5-DMC-20260811' / 'MetaEditor64.exe'
VERSION = 'FTMO-1STEP-17EA-20261104'
UNARMED = dict(FTMOExpectedLogin='0', FTMOExpectedServer='', FTMOExpectedSymbol='', FTMOExpectedCurrency='', FTMOReferenceBalance='0',
               FTMOStartUtcTime='0')
RULES = dict(FTMO1TargetPercent='10.0', FTMO1MaxLossPercent='10.0', FTMO1DailyLossPercent='3.0', FTMO1FloorBufferPercent='2.0',
             FTMO1DailyReservePercent='2.5', FTMO1BestDayCapPercent='4.5')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    raw = Path(p).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')


def sub1(text, old, new):
    assert text.count(old) == 1, ('expected exactly one occurrence', old[:120], text.count(old))
    return text.replace(old, new)


def set_values(path):
    out = {}
    for line in read(path).splitlines():
        if '=' in line and not line.startswith(';'):
            k, v = line.split('=', 1); out[k.strip()] = v.strip().split('||')[0]
    return out


def check_package(src, n):
    m = json.loads(read(src / 'PACKAGE.json'))
    for name, digest in m['files'].items():
        assert sha(src / 'package' / name) == digest, (src.name, 'package altered', name)
    assert sha(src / 'CalyxFTMOGuard.mqh') == m['guard_sha'] and len(m['entries']) == n
    return m


def guard_text():
    g = read(ANY / 'CalyxFTMOGuard.mqh')
    assert sha(ANY / 'CalyxFTMOGuard.mqh') == json.loads(read(ANY / 'PACKAGE.json'))['guard_sha'], 'any-broker guard altered'
    g = sub1(g, '#define CALYX_PROP_READY_GUARD\n', '#define CALYX_PROP_READY_GUARD\n'
             '// ftmo 1_step 2026-11-04: derived from the broker-neutral Prop Ready guard for the FTMO 1-Step rules: 10% max loss trailing\n'
             '// the highest end-of-day balance, 3% max daily loss from the midnight balance, best day <= 50% of total profit.\n')
    g = sub1(g, 'input int    FTMOPhase=3; // 1=10% target, 2=5% target, 3=no challenge target stop\n',
             'input int    FTMOPhase=1; // 1=FTMO 1-Step challenge (target + best-day rule), 3=funded / continuous (no target stop)\n'
             'input double FTMO1TargetPercent=10.0;      // 1-Step profit target, % of the initial capital\n'
             'input double FTMO1MaxLossPercent=10.0;     // firm max loss, % of the initial capital below the highest end-of-day balance\n'
             'input double FTMO1DailyLossPercent=3.0;    // firm max daily loss, % of the initial capital from the midnight balance\n'
             'input double FTMO1FloorBufferPercent=2.0;  // guard: new entries need projected equity >= trailing floor + this\n'
             'input double FTMO1DailyReservePercent=2.5; // guard: projected daily loss <= this; the day latches here\n'
             'input double FTMO1BestDayCapPercent=4.5;   // guard: no new entries today once today P&L >= this (0 = off)\n')
    g = sub1(g, 'double FTMODailyReserve(){return FTMOReferenceBalance*0.03;}\n'
                'double FTMOEquityBuffer(){return FTMOReferenceBalance*0.92;}\n'
                'double FTMOHardFloor(){return FTMOReferenceBalance*0.90;}\n'
                'double FTMODailyHardLoss(){return FTMOReferenceBalance*0.05;}\n',
             'double FTMODailyReserve(){return FTMOReferenceBalance*FTMO1DailyReservePercent/100.0;}\n'
             '// Highest Prague-midnight balance since this install (FTMOLedger stores it); never below the initial capital.\n'
             'double FTMO1HighWater(){string k=FTMOKey("HWM_"+IntegerToString(FTMOStartUtcTime));\n'
             '   return MathMax(FTMOReferenceBalance,GlobalVariableCheck(k)?GlobalVariableGet(k):0.0);}\n'
             'double FTMOHardFloor(){return FTMO1HighWater()-FTMOReferenceBalance*FTMO1MaxLossPercent/100.0;}\n'
             'double FTMOEquityBuffer(){return FTMOHardFloor()+FTMOReferenceBalance*FTMO1FloorBufferPercent/100.0;}\n'
             'double FTMODailyHardLoss(){return FTMOReferenceBalance*FTMO1DailyLossPercent/100.0;}\n'
             'double ftmo1_best_day=0; // best single-day net since the install (FTMOLedger)\n')
    g = sub1(g, '      && FTMOCapMultipleValid(FTMOTotalRiskMultiple) && FTMOCapMultipleValid(FTMOSymbolRiskMultiple);',
             '      && FTMOCapMultipleValid(FTMOTotalRiskMultiple) && FTMOCapMultipleValid(FTMOSymbolRiskMultiple)\n'
             '      && FTMO1TargetPercent>0 && FTMO1MaxLossPercent>0 && FTMO1DailyLossPercent>0 && FTMO1FloorBufferPercent>=0\n'
             '      && FTMO1DailyReservePercent>0 && FTMO1DailyReservePercent<FTMO1DailyLossPercent && FTMO1BestDayCapPercent>=0;')
    g = sub1(g, 'return "PR9"+IntegerToString(FTMOExpectedLogin)', 'return "F1S"+IntegerToString(FTMOExpectedLogin)')
    # ledger: end-of-day high-water mark and best day from the deployed trade deals (balance operations already fail closed)
    g = sub1(g, '   double delta=0;\n   bool install_day=today==start_day;\n',
             '   double delta=0,cum=0,day_net=0,best=0,hwm=FTMOReferenceBalance;int cur=-1;\n   bool install_day=today==start_day;\n')
    g = sub1(g, '      if(!deployed)continue;\n',
             '      if(!deployed)continue;\n'
             '      int dday=FTMODay(when);\n'
             '      if(dday!=cur){if(cur>=0){hwm=MathMax(hwm,FTMOReferenceBalance+cum);best=MathMax(best,day_net);}cur=dday;day_net=0;}\n'
             '      cum+=net;day_net+=net;\n')
    g = sub1(g, '   anchor=install_day?FTMOReferenceBalance:AccountInfoDouble(ACCOUNT_BALANCE)-delta;\n',
             '   if(cur>=0){best=MathMax(best,day_net);if(cur<today)hwm=MathMax(hwm,FTMOReferenceBalance+cum);}\n'
             '   GlobalVariableSet(FTMOKey("HWM_"+IntegerToString(FTMOStartUtcTime)),hwm);ftmo1_best_day=best;\n'
             '   anchor=install_day?FTMOReferenceBalance:AccountInfoDouble(ACCOUNT_BALANCE)-delta;\n')
    g = sub1(g, '   double target=FTMOReferenceBalance*(FTMOPhase==1?1.10:1.05);\n'
                '   if(FTMOPhase<3 && ftmo_days>=4 && balance>=target)return FTMOReject(result,"phase target reached; await review/new account");\n',
             '   double target=FTMOReferenceBalance*(1.0+FTMO1TargetPercent/100.0);\n'
             '   if(FTMOPhase==1 && balance>=target && ftmo1_best_day<=0.5*(balance-FTMOReferenceBalance)+0.005)\n'
             '      return FTMOReject(result,"1-Step target and best-day rule met; await review/new account");\n'
             '   if(FTMO1BestDayCapPercent>0 && equity-anchor>=FTMOReferenceBalance*FTMO1BestDayCapPercent/100.0)return FTMOReject(result,"best-day cap reached today");\n')
    assert g.count('Prop ready') >= 6
    g = g.replace('Prop ready', 'FTMO 1-Step')                # journal / reject messages only
    for unchanged in ('ftmo_entries>=7 || losses>=3', 'FTMOLotsDown(', 'FTMOTotalRiskMultiple/100.0', 'equity<=FTMOHardFloor() || equity<=anchor-FTMODailyHardLoss()',
                      'projected<FTMOEquityBuffer() || anchor-projected>FTMODailyReserve()'):
        assert unchanged in g, unchanged
    return g


def compile_ea(path):
    log = path.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    text = read(log)
    assert '0 errors, 0 warnings' in text, text[-3000:]
    ex5 = path.with_suffix('.ex5'); assert ex5.is_file() and ex5.stat().st_mtime >= started - 2
    print('COMPILED', path.stem, flush=True)


def installer_text(slugs):
    s = read(BP9 / 'Install-BestProp.ps1')
    roster = ',\n        '.join(', '.join(f"'{x}'" for x in slugs[i:i + 4]) for i in range(0, len(slugs), 4))
    rep = [
        ("# Best Prop Portfolio 2026-10-20: the Prop Ready nine EAs at 1% (USD 100 on 10k) with the rebuilt 1% guard.",
         "# ftmo 1_step 2026-11-04: the 17 FTMO-guarded EAs with the FTMO 1-Step guard (10% EOD-trailing max loss, 3% daily, best day <= 50%).\n"
         "# GENERATED by build.py from Best Prop Portfolio 2026-10-20/Install-BestProp.ps1; do not edit by hand."),
        ("[double]$RiskValue=1.0,", "[double]$RiskValue=0.5,"),
        ("[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',", "[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',"),
        ("[ValidateSet('Challenge','Verification','Funded')][string]$Phase='Challenge',", "[ValidateSet('Challenge','Funded')][string]$Phase='Challenge',"),
        ("if($manifest.entries.Count -ne 9 -or", "if($manifest.entries.Count -ne 17 -or"),
        ("$manifest.risk_cap_fraction -ne 0.01 -or $manifest.total_risk_fraction -ne 0.045 -or $manifest.symbol_risk_fraction -ne 0.03 -or",
         "$manifest.risk_cap_fraction -ne 0.005 -or $manifest.total_risk_fraction -ne 0.0225 -or $manifest.symbol_risk_fraction -ne 0.015 -or\n"
         "       $manifest.ruleset -ne 'FTMO_1STEP' -or"),
        ("    $expected=@('nasdaq-5m-candle-momentum','usdjpy-london-open-momentum','us100-month-end-flow','xau-rsi-vwap',\n"
         "        'us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30')",
         f"    $expected=@({roster})"),
        ("throw 'Best Prop roster changed.'", "throw 'FTMO 1-Step roster changed.'"),
        ("           $inputs['InpRiskPercent'] -ne '1.0' -or $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Distributed settings must be unarmed with InpRiskPercent=1.0.'}",
         "           $inputs['InpRiskPercent'] -ne '0.5' -or $inputs['InpAdaptivePortfolioControls'] -ne 'false' -or $inputs['FTMO1MaxLossPercent'] -ne '10.0' -or\n"
         "           $inputs['FTMO1DailyLossPercent'] -ne '3.0'){throw 'Distributed settings must be unarmed, InpRiskPercent=0.5 and the FTMO 1-Step rules.'}"),
        ("Write-Host 'BEST PROP PORTFOLIO - nine EAs, 1% risk per trade (capped at 1% of the starting balance).'",
         "Write-Host 'FTMO 1-STEP - 17 guarded EAs; FTMO 1-Step rules: +10% target, 3% daily loss, 10% max loss trailing the highest end-of-day balance, best day <= 50%.'"),
        ("        $answer=(Read-Host 'Phase: 1 = Challenge (stop at +10%), 2 = Verification (stop at +5%), 3 = Funded (no target) [1]').Trim()\n"
         "        if(-not $answer){$answer='1'}\n"
         "        $Phase=@{'1'='Challenge';'2'='Verification';'3'='Funded'}[$answer]\n"
         "        if(-not $Phase){throw 'Phase must be 1, 2 or 3.'}",
         "        $answer=(Read-Host 'Phase: 1 = 1-Step Challenge (stops at +10% once the best-day rule is met), 2 = Funded / continuous (no target) [1]').Trim()\n"
         "        if(-not $answer){$answer='1'}\n"
         "        $Phase=@{'1'='Challenge';'2'='Funded'}[$answer]\n"
         "        if(-not $Phase){throw 'Phase must be 1 or 2.'}"),
        ("""    if(-not $PSBoundParameters.ContainsKey('RiskValue')){
        $answer=(Read-Host 'Risk per trade, % of current equity, e.g. 0.5 / 1.0 / 2.0 (max 2) [1.0]').Trim()
        if($answer){$RiskValue=[double]::Parse($answer,[Globalization.CultureInfo]::InvariantCulture)}
    }""",
         """    if(-not $PSBoundParameters.ContainsKey('RiskMode')){
        $answer=(Read-Host 'Risk type: 1 = % of current equity, 2 = fixed amount per trade in the account currency [1]').Trim()
        if(-not $answer){$answer='1'}
        $RiskMode=@{'1'='PERCENT';'2'='FIXED_USD'}[$answer]
        if(-not $RiskMode){throw 'Risk type must be 1 or 2.'}
    }
    if(-not $PSBoundParameters.ContainsKey('RiskValue')){
        $prompt=if($RiskMode -eq 'PERCENT'){'Risk per trade, % of current equity: 0.5 (tested best) / 0.75 / 1.0 (max 2) [0.5]'}else{'Risk per trade, fixed amount in the account currency, e.g. 500 (max 2% of the starting balance) [500]'}
        $answer=(Read-Host $prompt).Trim()
        $RiskValue=if($answer){[double]::Parse($answer.Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture)}elseif($RiskMode -eq 'PERCENT'){0.5}else{500.0}
    }"""),
        ("""        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF [OFF]').Trim().ToUpperInvariant()
        if(-not $answer){$answer='OFF'}
        if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'}
        $NasdaqDIFilter=$answer
    }
}""",
         """        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF [ON]').Trim().ToUpperInvariant()
        if(-not $answer){$answer='ON'}
        if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'}
        $NasdaqDIFilter=$answer
    }
    if(-not $PSBoundParameters.ContainsKey('UsdJpyDIFilter')){
        $answer=(Read-Host 'USDJPY London DI filter ON or OFF (its ADX20 filter stays on) [ON]').Trim().ToUpperInvariant()
        if(-not $answer){$answer='ON'}
        if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'}
        $UsdJpyDIFilter=$answer
    }
}"""),
        ("Write-Host 'BEST PROP PORTFOLIO: nine EAs / five ORBs at 0.5R / broker-neutral MT5 hedging profile.'",
         "Write-Host 'FTMO 1-STEP: 17 EAs / five ORBs at 0.5R / any MT5 hedging account (built for FTMO 1-Step).'"),
        ("Write-Host 'PASS: 9 integrity-checked guarded EAs (1% cap, 4.5% total, 3% per symbol); ORBs 0.5R; Nasdaq DI default OFF. No account accessed.'",
         "Write-Host 'PASS: 17 integrity-checked guarded EAs (FTMO 1-Step rules; default 0.5% risk, 4.5x total, 3x per symbol); ORBs 0.5R; Nasdaq DI default ON. No account accessed.'"),
        ('("MQL5\\Files\\Calyx-BestProp9-$login-$serverHash.json")', '("MQL5\\Files\\Calyx-FTMO1Step-$login-$serverHash.json")'),
        ("if([double]$probe.account.equity -lt $initial*0.92){throw 'Equity is below 92% of the starting balance; stop for review.'}",
         "if([double]$probe.account.equity -lt $initial*0.92){throw 'Equity is below 92% of the starting balance; stop for review.'}\n"
         "if([double]$probe.account.equity -lt [double]$probe.account.balance-0.005){throw 'Account must be flat (equity = balance) to start an FTMO 1-Step baseline.'}"),
        ("$phaseNumber=@{Challenge=1;Verification=2;Funded=3}[$Phase]", "$phaseNumber=@{Challenge=1;Funded=3}[$Phase]"),
        ("$ProfileName='Calyx-BestProp9-'+$login", "$ProfileName='Calyx-FTMO1Step-'+$login"),
        ("    $inputs['FTMOTotalRiskMultiple']=Get-CalyxCapMultiple $TotalRiskCap;$inputs['FTMOSymbolRiskMultiple']=Get-CalyxCapMultiple $SymbolRiskCap\n",
         "    $inputs['FTMOTotalRiskMultiple']=Get-CalyxCapMultiple $TotalRiskCap;$inputs['FTMOSymbolRiskMultiple']=Get-CalyxCapMultiple $SymbolRiskCap\n"
         + ''.join(f"    $inputs['{k}']='{v}'\n" for k, v in RULES.items())),
        ("Write-Host \"Limits: total open risk $(Get-CalyxCapText $TotalRiskCap ($initial*$capPercent/100)); per symbol $(Get-CalyxCapText $SymbolRiskCap ($initial*$capPercent/100)); $($initial*0.03) daily reserved loss; $($initial*0.92) equity entry buffer.\"",
         "Write-Host \"FTMO 1-Step rules: target $($initial*1.10) (+10%); daily loss $($initial*0.03) (3%) from each midnight balance; max loss 10% below the highest end-of-day balance (floor starts at $($initial*0.90) and only rises); best day <= 50% of total profit.\"\n"
         "Write-Host \"Guard: total open risk $(Get-CalyxCapText $TotalRiskCap ($initial*$capPercent/100)); per symbol $(Get-CalyxCapText $SymbolRiskCap ($initial*$capPercent/100)); new entries stop $($initial*0.02) above the trailing floor (starts at $($initial*0.92)) and at a $($initial*0.025) daily loss (2.5%); no new entries after a $($initial*0.045) (4.5%) day; Challenge stops at +10% once the best-day rule holds.\"\n"
         "Write-Host 'Admission guard only: it never closes trades. A gap or a run of open losers can still breach FTMO limits.' -ForegroundColor Yellow"),
        ('$expected="BEST PROP $login $currency $Phase"', '$expected="FTMO 1STEP $login $currency $Phase"'),
        ("'Best Prop installed profile'", "'FTMO 1-Step installed profile'"),
        ("'.best-prop-backup-'", "'.ftmo1step-backup-'"),
        ('"Portfolio: Best Prop Portfolio 2026-10-20 (nine EAs, 1%)', '"Portfolio: ftmo 1_step (17 EAs, FTMO 1-Step guard)'),
        ('Review all nine charts and inputs', 'Review all 17 charts and inputs'),
    ]
    for a, b in rep:
        s = sub1(s, a, b)
    return s.replace('\n', '\r\n')


def helpers_text():
    return sub1(read(BP9 / 'Account-Helpers.ps1'), "throw 'Best Prop 9 requires a hedging MT5 account", "throw 'FTMO 1-Step requires a hedging MT5 account").replace('\n', '\r\n')


def write_installer(slugs):
    (HERE / 'Install-FTMO1Step.ps1').write_bytes(installer_text(slugs).encode('utf-8'))
    (HERE / 'Account-Helpers.ps1').write_bytes(helpers_text().encode('utf-8'))
    shutil.copy2(BP9 / 'probe_account.py', HERE / 'probe_account.py')


def main():
    anyb = check_package(ANY, 17)
    before = {str(p): sha(p) for src in (ANY, BP9) for p in src.rglob('*') if p.is_file()}
    for d in (PKG, EAS, SETS):
        if d.exists(): shutil.rmtree(d)                          # only this profile's own generated folders
        d.mkdir(parents=True)
    guard = guard_text()
    (HERE / 'CalyxFTMOGuard.mqh').write_text(guard, encoding='utf-8'); (PKG / 'CalyxFTMOGuard.mqh').write_text(guard, encoding='utf-8')
    for f in (ANY / 'package').iterdir():                        # strategy sources + trade shim
        if f.suffix == '.mqh' and f.name != 'CalyxFTMOGuard.mqh': shutil.copy2(f, PKG / f.name)
    entries = []; magics = {}
    for e in anyb['entries']:
        slug = e['slug']; stem = 'F1S-' + slug
        (PKG / (stem + '.mq5')).write_text(read(ANY / 'package' / (Path(e['expert']).stem + '.mq5')), encoding='utf-8')
        compile_ea(PKG / (stem + '.mq5'))
        values = set_values(ANY / 'package' / e['settings'])
        assert values['InpRiskPercent'] == '0.5' and values.get('InpAdaptivePortfolioControls') == 'false', slug
        if '-orb-' in slug: assert values['InpRewardRisk'] == '0.5'
        if slug == '3-way-gold': assert values['InpMarketEntries'] == 'true'
        values.update(FTMOAllocationMode='1', FTMOAllocationValue='0.5', FTMOPhase='1', **UNARMED, **RULES)
        magic = values.get('InpMagic') or values.get('InpMagicBase'); assert magic and magic not in magics, ('magic clash', slug, magic)
        magics[magic] = slug
        (PKG / (stem + '.set')).write_text('\n'.join(f'{k}={v}' for k, v in values.items()) + '\n', encoding='utf-8')
        shutil.copy2(PKG / (stem + '.ex5'), EAS / (stem + '.ex5')); shutil.copy2(PKG / (stem + '.set'), SETS / (stem + '.set'))
        entries.append(dict(slug=slug, label=e['label'], symbol=e['symbol'], timeframe=e['timeframe'], expert=stem + '.ex5', settings=stem + '.set',
                            magic=magic, source_package=ANY.name, source_expert=e['expert'], source_settings=e['settings'],
                            expert_sha=sha(PKG / (stem + '.ex5')), settings_sha=sha(PKG / (stem + '.set'))))
    files = {p.name: sha(p) for p in PKG.iterdir() if p.is_file() and p.suffix != '.log'}
    out = dict(version=VERSION, ruleset='FTMO_1STEP', entries=entries, news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True,
               reference_mode='FRESH_BASELINE_EVERY_RUN', default_phase='Challenge', default_allocation='0.5% of current equity',
               risk_cap_fraction=0.005, total_risk_fraction=0.0225, symbol_risk_fraction=0.015, firm_rules=dict(target=0.10, max_loss=0.10,
               max_loss_type='end-of-day trailing', daily_loss=0.03, best_day_share=0.50), guard_rules=dict(floor_buffer=0.02, daily_reserve=0.025,
               best_day_cap=0.045), strategy_risk_percent='0.5 (installer: 1.5x the chosen risk, max 5)', nasdaq_di_default='ON', usdjpy_di_default='ON',
               guard_sha=sha(HERE / 'CalyxFTMOGuard.mqh'), guard_state_prefix='F1S', source_package=dict(name=ANY.name, version=anyb['version'],
               guard_sha=anyb['guard_sha']), files=files)
    (HERE / 'PACKAGE.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    write_installer([e['slug'] for e in entries])
    assert {str(p): sha(p) for src in (ANY, BP9) for p in src.rglob('*') if p.is_file()} == before, 'source packages must stay unchanged'
    print(f'Built {len(entries)} EAs ({VERSION}); sources unchanged; no MT5 terminal touched.')


if __name__ == '__main__':
    if sys.argv[1:] == ['installer']:
        write_installer([e['slug'] for e in json.loads(read(HERE / 'PACKAGE.json'))['entries']]); print('installer + helpers regenerated')
    else:
        main()
