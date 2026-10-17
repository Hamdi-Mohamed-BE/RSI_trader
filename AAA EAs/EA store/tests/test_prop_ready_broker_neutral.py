"""Offline regressions for the separate, broker-neutral Prop Ready distribution.

Only pure PowerShell declaration ASTs are evaluated. No account probe, process
inventory, compiler, terminal or installer is invoked except the manifest-only
ValidateOnly path, which has side-effect commands replaced by failing stubs.
"""

import hashlib
import json
import os
import re
import subprocess

import pytest

from app.catalog import PACKAGE_ROOT


LIVE = PACKAGE_ROOT / "_00 Live profiles"
GENERIC = LIVE / "Packages" / "PropReady"
FTMO = LIVE / "Packages" / "FTMO"
HELPERS = GENERIC / "Account-Helpers.ps1"
INSTALLER = GENERIC / "Install-Portfolio.ps1"
WRAPPER = LIVE / "Start-LiveProfile.ps1"
SHARED = PACKAGE_ROOT / "_Auto Deploy" / "Install-BMTradingPortfolio.ps1"
WINDOWS = pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell pure-helper fixtures")

PROP_READY = {
    "xau-rsi-vwap", "xau-orb-london-ny-overlap-m30", "us100-h1-orb-13utc",
    "usdjpy-london-open-momentum", "us100-month-end-flow", "nasdaq-5m-candle-momentum",
    "us100-orb-new-york-m30", "us100-selective-orb-v3", "xau-orb-new-york-m30",
}
ORBS = {slug for slug in PROP_READY if "-orb-" in slug}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def powershell(script):
    result = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True, capture_output=True, timeout=60, cwd=LIVE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def imports(path, names):
    """Extract declarations, never dot-source an installer's top-level code."""
    return f"""
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile({quote(path)},[ref]$tokens,[ref]$errors)
if($errors.Count){{throw 'PowerShell parse failure'}}
foreach($name in @({','.join(quote(name) for name in names)})){{
 $found=@($ast.FindAll({{param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]}},$true) | Where-Object Name -eq $name)
 if($found.Count -ne 1){{throw ('Missing or ambiguous pure helper: '+$name)}}
 . ([scriptblock]::Create($found[0].Extent.Text))
}}
"""


def fixture_probe():
    return """
function New-FixtureProbe {
 return [pscustomobject]@{
  ok=$true;snapshot_utc=1800000000;positions=0;orders=0
  terminal=[pscustomobject]@{connected=$true;trade_allowed=$false;path='C:\\Fixtures\\MT5';data_path='C:\\Fixtures\\Data'}
  account=[pscustomobject]@{login=12345678;server='Exness-MT5Trial16';currency='USD';margin_mode=2;
   balance=5000.0;equity=5000.0;company='Exness demo fixture';leverage=500;trade_allowed=$true;trade_expert=$true}
 }
}
"""


def rejection_script(expressions, action="Assert-PropReadyAccount $p"):
    script = imports(HELPERS, ["Assert-PropReadyAccount"]) + fixture_probe()
    script += "$out=@()\n"
    for label, expression in expressions:
        script += f"""
$p=New-FixtureProbe
{expression}
$blocked=$false;$message=''
try{{{action}}}catch{{$blocked=$true;$message=$_.Exception.Message}}
$out+=[pscustomobject]@{{case={quote(label)};blocked=$blocked;message=$message}}
"""
    return script + "$out | ConvertTo-Json -Depth 6 -Compress\n"


@WINDOWS
def test_demo_and_live_hedging_accounts_are_not_restricted_to_ftmo_usd_10k_or_leverage():
    script = imports(HELPERS, ["Assert-PropReadyAccount"]) + fixture_probe()
    script += """
$out=@()
foreach($currency in @('USD','EUR','GBP','JPY','USC')){
 foreach($balance in @(100.0,5000.0,10000.0,50000.0,250000.0)){
  foreach($leverage in @(20,100,500,2000)){
   $p=New-FixtureProbe;$p.account.currency=$currency;$p.account.balance=$balance;$p.account.equity=$balance
   $p.account.leverage=$leverage
   Assert-PropReadyAccount $p
   $out+=[pscustomobject]@{currency=$currency;balance=$balance;leverage=$leverage}
  }
 }
}
$out | ConvertTo-Json -Depth 5 -Compress
"""
    rows = json.loads(powershell(script))
    assert len(rows) == 100
    assert any(row == {"currency": "USD", "balance": 5000, "leverage": 500} for row in rows)


@WINDOWS
def test_account_preflight_keeps_non_broker_safety_checks():
    cases = [
        ("disconnected", "$p.terminal.connected=$false"),
        ("probe-failed", "$p.ok=$false"),
        ("netting", "$p.account.margin_mode=0"),
        ("exchange-netting", "$p.account.margin_mode=1"),
        ("algo-already-on", "$p.terminal.trade_allowed=$true"),
        ("open-position", "$p.positions=1"),
        ("pending-order", "$p.orders=1"),
        ("account-no-trade", "$p.account.trade_allowed=$false"),
        ("account-no-eas", "$p.account.trade_expert=$false"),
        ("invalid-login", "$p.account.login=0"),
        ("missing-server", "$p.account.server=''"),
        ("unsafe-server", '$p.account.server="fixture`n<bad>"'),
        ("empty-currency", "$p.account.currency=''"),
        ("bad-currency", "$p.account.currency='EUR/USD'"),
        ("zero-balance", "$p.account.balance=0"),
        ("negative-equity", "$p.account.equity=-1"),
        ("nan-balance", "$p.account.balance=[double]::NaN"),
        ("infinite-equity", "$p.account.equity=[double]::PositiveInfinity"),
        ("invalid-snapshot", "$p.snapshot_utc=0"),
    ]
    rows = json.loads(powershell(rejection_script(cases)))
    assert len(rows) == len(cases)
    assert all(row["blocked"] and row["message"] for row in rows), rows


@WINDOWS
def test_saved_reference_is_account_bound_and_does_not_reset_on_reruns():
    script = imports(HELPERS, ["Get-PropReadyReference"]) + fixture_probe()
    script += """
$p=New-FixtureProbe
$first=Get-PropReadyReference $p
$p.account.balance=5700;$p.account.equity=5600;$p.snapshot_utc+=86400
$next=Get-PropReadyReference $p $first
[pscustomobject]@{first=$first;next=$next;same_object=[object]::ReferenceEquals($first,$next)} | ConvertTo-Json -Depth 6 -Compress
"""
    result = json.loads(powershell(script))
    assert result["first"] == result["next"]
    assert result["same_object"] is True
    assert result["first"] == {
        "version": 1, "login": "12345678", "server": "Exness-MT5Trial16", "currency": "USD",
        "reference_balance": 5000, "start_utc": 1800000000,
    }


@WINDOWS
def test_saved_reference_rejects_corruption_future_time_and_account_mismatch():
    changes = [
        ("wrong-version", "$reference.version=2"),
        ("wrong-login", "$reference.login='998877'"),
        ("wrong-server", "$reference.server='Another-Broker'"),
        ("wrong-currency", "$reference.currency='EUR'"),
        ("zero-balance", "$reference.reference_balance=0"),
        ("negative-balance", "$reference.reference_balance=-1"),
        ("nan-balance", "$reference.reference_balance=[double]::NaN"),
        ("infinite-balance", "$reference.reference_balance=[double]::PositiveInfinity"),
        ("invalid-start", "$reference.start_utc=0"),
        ("future-start", "$reference.start_utc=$p.snapshot_utc+1"),
    ]
    script = imports(HELPERS, ["Get-PropReadyReference"]) + fixture_probe() + "$out=@()\n"
    for label, expression in changes:
        script += f"""
$p=New-FixtureProbe;$reference=Get-PropReadyReference $p
{expression}
$blocked=$false
try{{$null=Get-PropReadyReference $p $reference}}catch{{$blocked=$true}}
$out+=[pscustomobject]@{{case={quote(label)};blocked=$blocked}}
"""
    rows = json.loads(powershell(script + "$out | ConvertTo-Json -Compress"))
    assert len(rows) == len(changes)
    assert all(row["blocked"] for row in rows), rows


@WINDOWS
def test_confirmation_rejects_account_or_terminal_swaps_but_allows_new_timestamp():
    changes = [
        ("login", "$confirmation.account.login=998877"),
        ("server", "$confirmation.account.server='OtherServer'"),
        ("currency", "$confirmation.account.currency='EUR'"),
        ("balance", "$confirmation.account.balance+=1"),
        ("equity", "$confirmation.account.equity-=1"),
        ("data-path", "$confirmation.terminal.data_path='C:\\Different\\Data'"),
        ("terminal-path", "$confirmation.terminal.path='C:\\Different\\MT5'"),
        ("position-created", "$confirmation.positions=1"),
        ("algo-enabled", "$confirmation.terminal.trade_allowed=$true"),
    ]
    script = imports(HELPERS, ["Assert-PropReadyAccount", "Assert-PropReadyConfirmation"]) + fixture_probe()
    script += "$out=@()\n"
    for label, expression in changes:
        script += f"""
$original=New-FixtureProbe;$confirmation=New-FixtureProbe
{expression}
$blocked=$false
try{{Assert-PropReadyConfirmation $original $confirmation}}catch{{$blocked=$true}}
$out+=[pscustomobject]@{{case={quote(label)};blocked=$blocked}}
"""
    script += """
$original=New-FixtureProbe;$confirmation=New-FixtureProbe;$confirmation.snapshot_utc+=15
Assert-PropReadyConfirmation $original $confirmation
$out+=[pscustomobject]@{case='new-snapshot';blocked=$false}
$out | ConvertTo-Json -Compress
"""
    rows = json.loads(powershell(script))
    assert all(row["blocked"] for row in rows[:-1]), rows
    assert rows[-1] == {"case": "new-snapshot", "blocked": False}


@WINDOWS
def test_shared_symbol_aliases_accept_broker_prefixes_suffixes_and_cash_names_not_futures():
    script = imports(SHARED, ["Normalize-Symbol", "Find-BrokerSymbol"])
    script += """
$fixtures=@(
 @{name='USTECm';aliases=@('USTEC','US100','NAS100')},
 @{name='US100.cash';aliases=@('USTEC','US100','NAS100')},
 @{name='m.NAS100';aliases=@('USTEC','US100','NAS100')},
 @{name='XAUUSD.a';aliases=@('XAUUSD','GOLD')},
 @{name='pro.GOLD';aliases=@('XAUUSD','GOLD')},
 @{name='USDJPYm';aliases=@('USDJPY')}
)
$out=@()
foreach($fixture in $fixtures){
 $symbols=@(
  [pscustomobject]@{name=$fixture.name;path='CFD Cash';trade_mode=4;visible=$false},
  [pscustomobject]@{name=$fixture.aliases[0];path='Futures';trade_mode=4;visible=$true},
  [pscustomobject]@{name='UNRELATED';path='CFD Cash';trade_mode=4;visible=$true}
 )
 $match=Find-BrokerSymbol $symbols $fixture.aliases
 $out+=[pscustomobject]@{expected=$fixture.name;actual=$match.name}
}
$out | ConvertTo-Json -Compress
"""
    rows = json.loads(powershell(script))
    assert len(rows) == 6
    assert all(row["expected"] == row["actual"] for row in rows)


def test_existing_ftmo_guard_and_binaries_unchanged_and_original_installer_logic_unchanged():
    expected = {
        "CalyxFTMOGuard.mqh": "0378db52f0d3bde690808e007d9fcc6fdc69da2bf16692bd38f6aa2c362dcf5f",
        "PACKAGE.json": "48b5ec012174d0baeaf134b3c3f495b2bcfbf465101400139b84ac99da368b1a",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((FTMO / name).read_bytes()).hexdigest() == digest
    manifest = read_json(FTMO / "PACKAGE.json")
    assert len(manifest["entries"]) == 17
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((FTMO / "package" / name).read_bytes()).hexdigest() == digest
    # Compatibility forwarding is the ONLY allowed edit to the old installer;
    # default FTMO17 execution remains byte-identical after newline normalization.
    old = (FTMO / "Install-Portfolio.ps1").read_text(encoding="utf-8-sig")
    forward = """# Legacy direct PROP_READY9 calls must use the broker-neutral package too.
if($PortfolioVariant -eq 'PROP_READY9'){
    $forward=@{};foreach($key in $PSBoundParameters.Keys){if($key -ne 'PortfolioVariant'){$forward[$key]=$PSBoundParameters[$key]}}
    & (Join-Path $PSScriptRoot '..\\PropReady\\Install-Portfolio.ps1') @forward
    exit $LASTEXITCODE
}
"""
    assert old.count(forward) == 1
    assert hashlib.sha256(old.replace(forward, "", 1).encode()).hexdigest() == (
        "a06e4f8e7b1c769bc8e0198c1a2d50520cff4536059426606a44f71bf03fca9f"
    )


def test_new_package_contains_exact_nine_and_preserves_all_strategy_inputs():
    manifest = read_json(GENERIC / "PACKAGE.json")
    original = {entry["slug"]: entry for entry in read_json(FTMO / "PACKAGE.json")["entries"]}
    assert len(manifest["entries"]) == 9
    assert {entry["slug"] for entry in manifest["entries"]} == PROP_READY
    assert manifest["news_enabled"] is False
    assert manifest["hedging_required"] is True
    assert manifest["currency_mode"] == "ACCOUNT_CURRENCY"
    assert manifest["risk_cap_fraction"] == 0.005
    assert hashlib.sha256((GENERIC / "CalyxFTMOGuard.mqh").read_bytes()).hexdigest() == manifest["guard_sha"]
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((GENERIC / "package" / name).read_bytes()).hexdigest() == digest
    for entry in manifest["entries"]:
        inputs = entry["inputs"]
        before = original[entry["slug"]]["inputs"]
        assert {k: v for k, v in inputs.items() if not k.startswith("FTMO")} == {
            k: v for k, v in before.items() if not k.startswith("FTMO")
        }, entry["slug"]
        assert inputs["FTMOExpectedLogin"] == "0"
        assert inputs["FTMOExpectedServer"] == ""
        assert inputs["FTMOExpectedSymbol"] == ""
        assert inputs["FTMOExpectedCurrency"] == ""
        assert inputs["FTMOReferenceBalance"] == "0"
        assert inputs["FTMOStartUtcTime"] == "0"
        assert inputs["FTMOPhase"] == "3"
        assert inputs["InpAdaptivePortfolioControls"] == "false"
        assert float(inputs["InpRiskPercent"]) == 0.5
        if entry["slug"] in ORBS:
            assert float(inputs["InpRewardRisk"]) == 0.5


@WINDOWS
@pytest.mark.parametrize("mode,value", [("FIXED_USD", 50), ("PERCENT", 0.5), ("FIXED_USD", 20), ("PERCENT", 0.3)])
def test_new_presets_change_only_requested_allocation_and_independent_di(mode, value):
    script = imports(SHARED, ["Read-SetInputs"])
    script += imports(HELPERS, ["Get-PropReadyPresetInputs"])
    script += f"""
$Package={quote(GENERIC / 'package')};$RiskMode={quote(mode)};[double]$RiskValue={value}
$manifest=Get-Content -Raw -LiteralPath {quote(GENERIC / 'PACKAGE.json')} | ConvertFrom-Json
$out=@()
foreach($NasdaqDIFilter in @('ON','OFF')){{foreach($UsdJpyDIFilter in @('ON','OFF')){{
 foreach($entry in $manifest.entries){{
  $out+=[pscustomobject]@{{slug=$entry.slug;nasdaq=$NasdaqDIFilter;jpy=$UsdJpyDIFilter;
   before=(Read-SetInputs (Join-Path $Package $entry.settings));inputs=(Get-PropReadyPresetInputs $entry)}}
 }}
}}}}
$out | ConvertTo-Json -Depth 10 -Compress
"""
    rows = json.loads(powershell(script))
    assert len(rows) == 36
    for row in rows:
        expected = row["before"].copy()
        expected["FTMOAllocationMode"] = "0" if mode == "FIXED_USD" else "1"
        expected["FTMOAllocationValue"] = row["inputs"]["FTMOAllocationValue"]
        if row["slug"] == "nasdaq-5m-candle-momentum":
            expected["InpRequireDIAgreement"] = str(row["nasdaq"] == "ON").lower()
        if row["slug"] == "usdjpy-london-open-momentum":
            expected["InpRequireDIAgreement"] = str(row["jpy"] == "ON").lower()
            assert row["inputs"]["InpUseADXFilter"] == "true"
            assert float(row["inputs"]["InpADXMinimum"]) == 20
        assert row["inputs"] == expected
        assert float(row["inputs"]["FTMOAllocationValue"]) == value


def test_wrapper_routes_only_prop_ready_to_new_package_and_defaults_to_continuous_funded_mode():
    source = WRAPPER.read_text(encoding="utf-8-sig")
    prop = re.search(r"'prop-ready'\s*\{(.*?)\n\s*\}\s*\n\s*'ftmo'", source, re.S)
    assert prop
    assert "Packages\\PropReady\\Install-Portfolio.ps1" in prop.group(1)
    assert "$PSBoundParameters.ContainsKey('Phase')" in prop.group(1)
    assert "else{'Funded'}" in prop.group(1)
    assert "PortfolioVariant" not in prop.group(1)
    assert "Packages\\FTMO\\Install-Portfolio.ps1" in source
    installer = INSTALLER.read_text(encoding="utf-8-sig")
    assert "[string]$Phase='Funded'" in installer
    profile = next(p for p in read_json(LIVE / "Profiles.json")["profiles"] if p["slug"] == "prop-ready")
    assert profile["eas"] == 9 and profile["file"] == "Prop ready.bat"
    assert "FTMO USD 10K" not in profile["warning"]


def mql_function_body(source, name):
    match = re.search(r"\b" + re.escape(name) + r"\([^{};]*\)\s*\{", source)
    assert match, name
    start = match.end()
    depth = 1
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index]
    pytest.fail("Unterminated MQL function: " + name)


def test_generic_guard_has_no_firm_usd_10k_lock_and_requires_explicit_account_bindings():
    guard = (GENERIC / "CalyxFTMOGuard.mqh").read_text(encoding="utf-8-sig")
    account = mql_function_body(guard, "FTMOAccountOK")
    assert '"USD"' not in account and "10000" not in account and '"FTMO"' not in account
    assert "StringFind" not in account and "ACCOUNT_LEVERAGE" not in account
    for check in (
        "FTMOExpectedLogin>0", "StringLen(FTMOExpectedServer)>0", "StringLen(FTMOExpectedCurrency)>0",
        "FTMOReferenceBalance>0", "MathIsValidNumber(FTMOReferenceBalance)", "FTMOStartUtcTime>0",
        "AccountInfoInteger(ACCOUNT_LOGIN)==FTMOExpectedLogin",
        "AccountInfoString(ACCOUNT_SERVER)==FTMOExpectedServer",
        "AccountInfoString(ACCOUNT_CURRENCY)==FTMOExpectedCurrency",
        "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", "_Symbol==FTMOExpectedSymbol",
    ):
        assert check in account
    assert "input long   FTMOExpectedLogin=0;" in guard
    assert "input string FTMOExpectedCurrency=\"\";" in guard
    assert "input double FTMOReferenceBalance=0.0;" in guard
    assert "input long FTMOStartUtcTime=0;" in guard
    assert "input int    FTMOPhase=3;" in guard
    installer = INSTALLER.read_text(encoding="utf-8-sig")
    for binding in (
        "$inputs['FTMOExpectedLogin']=$login", "$inputs['FTMOExpectedServer']=$server",
        "$inputs['FTMOExpectedCurrency']=$currency", "$inputs['FTMOExpectedSymbol']=$resolved[$entry.symbol]",
        "$inputs['FTMOReferenceBalance']=$initial.ToString", "$inputs['FTMOStartUtcTime']=[string]$reference.start_utc",
        "$inputs['FTMOPhase']=[string]$phaseNumber",
    ):
        assert binding in installer


def test_generic_guard_scales_risk_from_frozen_baseline_and_lots_always_round_down():
    guard = (GENERIC / "CalyxFTMOGuard.mqh").read_text(encoding="utf-8-sig")
    factors = {
        "FTMORiskCap": "0.005", "FTMOTotalRiskCap": "0.0225", "FTMOSymbolRiskCap": "0.015",
        "FTMODailyReserve": "0.03", "FTMOEquityBuffer": "0.92", "FTMOHardFloor": "0.90",
        "FTMODailyHardLoss": "0.05",
    }
    for name, factor in factors.items():
        assert f"return FTMOReferenceBalance*{factor};" in mql_function_body(guard, name)
    allocation = mql_function_body(guard, "FTMOAllocationBudget")
    assert "AccountInfoDouble(ACCOUNT_EQUITY)*FTMOAllocationValue/100.0" in allocation
    assert "MathMin(FTMORiskCap(),requested)" in allocation
    assert "MathFloor(desired/step+1e-9)*step" in mql_function_body(guard, "FTMOLotsDown")
    admit = mql_function_body(guard, "FTMOAdmit")
    assert "FTMOLotsDown(MathMin(r.volume,MathMin(FTMOAllocationBudget()/unit" in admit
    assert 'return FTMOReject(result,"minimum lot exceeds budget")' in admit
    assert "if(FTMOPhase<3 &&" in admit
    assert "FTMOStartUtcTime" not in mql_function_body(guard, "FTMOIdentity")
    assert "FTMOReferenceBalance" not in mql_function_body(guard, "FTMOIdentity")


def test_guard_loss_caps_do_not_disable_strategy_trade_management():
    guard = (GENERIC / "CalyxFTMOGuard.mqh").read_text(encoding="utf-8-sig")
    pulse = mql_function_body(guard, "FTMOPulse")
    assert pulse.count("return false;") == 1
    assert "if(!FTMOAccountOK())return false;" in pulse
    assert 'GlobalVariableSet(FTMOKey("BREACHED"),1)' in pulse
    assert "return true;" in pulse
    send = mql_function_body(guard, "FTMOOrderSend")
    assert "if(entry && !FTMOAdmit(r,result))" in send
    assert "bool closing=(r.action==TRADE_ACTION_DEAL && r.position>0);" in send
    assert "bool protection=r.action==TRADE_ACTION_SLTP;" in send
    assert "bool entry=!closing && !protection && !removing;" in send
    assert "bool sent=OrderSend(r,result);" in send


def test_broker_filling_helper_runs_before_ctrade_early_return_and_for_closing_deals():
    guard = (GENERIC / "CalyxFTMOGuard.mqh").read_text(encoding="utf-8-sig")
    filling = mql_function_body(guard, "FTMOMarketFilling")
    assert "SYMBOL_TRADE_EXEMODE" in filling and "SYMBOL_FILLING_MODE" in filling
    assert "ORDER_FILLING_FOK" in filling and "ORDER_FILLING_IOC" in filling
    assert "ORDER_FILLING_RETURN && execution!=SYMBOL_TRADE_EXECUTION_MARKET" in filling
    assert "if(ioc){filling=ORDER_FILLING_IOC;return true;}" in filling
    send = mql_function_body(guard, "FTMOOrderSend")
    assert "if(r.action==TRADE_ACTION_DEAL && !FTMOMarketFilling(r.symbol,r.type_filling))" in send
    trade = (GENERIC / "package" / "FTMO_Trade.mqh").read_text(encoding="utf-8-sig")
    body = mql_function_body(trade, "CTrade::FillingCheck")
    helper = body.index("if(!FTMOMarketFilling(symbol,mode))return false;")
    assert helper < body.index("SYMBOL_TRADE_EXEMODE")
    assert "m_type_filling=mode;" in body[helper:]
    assert "m_request.action" not in body[:helper]
    builder = (PACKAGE_ROOT.parent / "EA store" / "tools" / "build_prop_ready.py").read_text(encoding="utf-8-sig")
    assert "if(!FTMOMarketFilling(symbol,mode))return false;" in builder
    assert "m_request.action==TRADE_ACTION_DEAL" not in builder


def distribution_snapshot():
    paths = [p for folder in (FTMO, GENERIC) for p in folder.rglob("*") if p.is_file()]
    paths += [WRAPPER, SHARED, LIVE / "Profiles.json", LIVE / "Prop ready.bat"]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@WINDOWS
@pytest.mark.parametrize("arguments", ["", "-RiskMode PERCENT -RiskValue 0.3 -NasdaqDIFilter OFF -UsdJpyDIFilter ON"])
def test_new_validate_only_is_side_effect_free_and_exits_before_account_and_process_access(arguments):
    text = INSTALLER.read_text(encoding="utf-8-sig")
    early = re.search(r"if\s*\(\s*\$ValidateOnly\s*\)\s*\{", text)
    candidates = text.index("$candidates=@(Get-Mt5Candidates")
    assert early and early.start() < candidates
    assert re.search(r"\bexit\s+0\b", text[early.start():candidates])
    assert text.index("$probeText=") > candidates
    assert text.index("Close-TargetTerminal $terminalPath") > candidates
    before = distribution_snapshot()
    blocked = (
        "Read-Host", "Get-CimInstance", "Get-WmiObject", "Get-Process", "Start-Process", "Stop-Process",
        "New-Item", "Copy-Item", "Move-Item", "Remove-Item", "Set-Content", "Add-Content", "Out-File", "python", "python.exe",
    )
    # Import before shadowing Utility exports (e.g. Read-Host / Out-File), so
    # legitimate read-only Get-FileHash is not lost to auto-loading collisions.
    script = "Import-Module Microsoft.PowerShell.Utility,Microsoft.PowerShell.Management\n"
    script += "\n".join(f"function global:{name} {{ throw 'Forbidden in offline validation: {name}' }}" for name in blocked)
    script += f"\n& {quote(WRAPPER)} -Portfolio prop-ready -ValidateOnly -TargetTerminal 'Z:\\NO-ACCOUNT\\terminal64.exe' {arguments}\n"
    output = powershell(script)
    assert "PASS: 9 integrity-checked guarded EAs" in output
    assert "No account accessed" in output
    assert "Forbidden in offline validation" not in output
    assert distribution_snapshot() == before


@WINDOWS
def test_invalid_risk_is_rejected_by_new_installer_and_wrapper_before_any_account_access():
    blocked = (
        "Read-Host", "Get-CimInstance", "Get-WmiObject", "Get-Process", "Start-Process", "Stop-Process",
        "New-Item", "Copy-Item", "Move-Item", "Remove-Item", "Set-Content", "Add-Content", "Out-File", "python", "python.exe",
    )
    script = "Import-Module Microsoft.PowerShell.Utility,Microsoft.PowerShell.Management\n"
    script += "\n".join(f"function global:{name} {{ throw 'Forbidden in offline validation: {name}' }}" for name in blocked)
    script += f"""
$out=@()
foreach($layer in @('wrapper','installer')){{
 foreach($case in @(
  @{{name='negative';mode='FIXED_USD';value=-1.0}},
  @{{name='nan';mode='FIXED_USD';value=[double]::NaN}},
  @{{name='infinite';mode='PERCENT';value=[double]::PositiveInfinity}},
  @{{name='percent-over-limit';mode='PERCENT';value=10.01}}
 )){{
  $arguments=@{{RiskMode=$case.mode;RiskValue=$case.value;ValidateOnly=$true}}
  $path={quote(INSTALLER)}
  if($layer -eq 'wrapper'){{$path={quote(WRAPPER)};$arguments.Portfolio='prop-ready'}}
  $blocked=$false;$errorText=''
  try{{& $path @arguments}}catch{{$blocked=$true;$errorText=$_.Exception.Message}}
  $out+=[pscustomobject]@{{layer=$layer;case=$case.name;blocked=$blocked;error=$errorText}}
 }}
}}
'__REJECTIONS__'+($out | ConvertTo-Json -Depth 6 -Compress)
"""
    before = distribution_snapshot()
    output = powershell(script)
    rows = json.loads(output.split("__REJECTIONS__")[-1].strip())
    assert len(rows) == 8
    for row in rows:
        assert row["blocked"] is True, row
        assert "risk" in row["error"].lower(), row
        assert "Forbidden in offline validation" not in row["error"], row
    assert distribution_snapshot() == before
