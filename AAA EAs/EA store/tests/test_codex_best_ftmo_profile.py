"""Offline checks for the named, broker-neutral Codex_Best_FTMO launcher.

Builder functions and PowerShell helpers are extracted through their ASTs. The
only full script execution is ValidateOnly with account/process/write commands
replaced by failing stubs. These fixtures never inspect or alter a live MT5.
"""

import ast
import hashlib
import json
import os
import re
import subprocess

import pytest

from app.catalog import PACKAGE_ROOT


LIVE = PACKAGE_ROOT / "_00 Live profiles"
GENERIC = LIVE / "Packages" / "PropReady"
INSTALLER = GENERIC / "Install-Portfolio.ps1"
HELPERS = GENERIC / "Account-Helpers.ps1"
WRAPPER = LIVE / "Start-LiveProfile.ps1"
SHARED = PACKAGE_ROOT / "_Auto Deploy" / "Install-BMTradingPortfolio.ps1"
BUILDER = PACKAGE_ROOT.parent / "EA store" / "tools" / "build_live_profiles.py"
WINDOWS = pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell offline fixtures")

SLUG = "codex-best-ftmo"
NINE = {
    "nasdaq-5m-candle-momentum", "usdjpy-london-open-momentum", "us100-month-end-flow",
    "xau-rsi-vwap", "us100-h1-orb-13utc", "us100-orb-new-york-m30",
    "us100-selective-orb-v3", "xau-orb-new-york-m30", "xau-orb-london-ny-overlap-m30",
}
EXISTING_PROFILES = {
    "ftmo": (17, "FTMO guarded - Current 14.bat"),
    "ftmo-any-broker": (17, "FTMO guarded - Current 14 - ANY BROKER TEST.bat"),
    "current14-orb05": (17, "Current 14 + ORB 0.5R.bat"),
    "orbs-only": (5, "ORB-only - 50pct+ PF1.15+.bat"),
    "prop-ready": (9, "Prop ready.bat"),
    "full-eas": (37, "Full EA portfolio - Recommended Adaptive.bat"),
}


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
    return f"""
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile({quote(path)},[ref]$tokens,[ref]$errors)
if($errors.Count){{throw 'PowerShell parse failure'}}
foreach($name in @({','.join(quote(name) for name in names)})){{
 $found=@($ast.FindAll({{param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]}},$true) | Where-Object Name -eq $name)
 if($found.Count -ne 1){{throw ('Missing/ambiguous helper: '+$name)}}
 . ([scriptblock]::Create($found[0].Extent.Text))
}}
"""


def declarations_only_named_profiles():
    """Do not import a builder or run its compile/copy/write operations."""
    tree = ast.parse(BUILDER.read_text(encoding="utf-8-sig"), filename=str(BUILDER))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "named_profiles"]
    folders = [node for node in tree.body if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FOLDERS" for t in node.targets)]
    assert len(functions) == 1 and len(folders) == 1
    module = ast.Module(body=folders + functions, type_ignores=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(module), str(BUILDER), "exec"), namespace)
    return namespace["named_profiles"]()


def snapshot():
    paths = [p for p in GENERIC.rglob("*") if p.is_file()]
    paths += [WRAPPER, LIVE / "Profiles.json", LIVE / "Prop ready" / "Codex_Best_FTMO.bat"]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def blocked_commands():
    names = (
        "Read-Host", "Get-CimInstance", "Get-WmiObject", "Get-Process", "Start-Process", "Stop-Process",
        "New-Item", "Copy-Item", "Move-Item", "Remove-Item", "Set-Content", "Add-Content", "Out-File",
        "python", "python.exe",
    )
    return "Import-Module Microsoft.PowerShell.Utility,Microsoft.PowerShell.Management\n" + "\n".join(
        f"function global:{name} {{ throw 'Forbidden in offline validation: {name}' }}" for name in names
    ) + "\n"


def test_named_profile_metadata_matches_generator_without_running_builder():
    published = read_json(LIVE / "Profiles.json")
    generated = declarations_only_named_profiles()
    assert published["profiles"] == generated
    assert len({row["slug"] for row in generated}) == len(generated)
    assert {row["slug"] for row in generated} == {*EXISTING_PROFILES, SLUG}
    by_slug = {row["slug"]: row for row in generated}
    for slug, (count, filename) in EXISTING_PROFILES.items():
        assert (by_slug[slug]["eas"], by_slug[slug]["file"]) == (count, filename)
    profile = by_slug[SLUG]
    assert profile["name"] == "Codex_Best_FTMO"
    assert profile["file"] == "Codex_Best_FTMO.bat"
    assert profile["eas"] == 9
    assert profile["default_mode"] == "FIXED_USD"
    assert profile["default_usd"] == 50 and profile["default_percent"] == 0.5
    assert profile["default_news_percent"] == 0
    assert profile["di_parameters"] == ["NasdaqDIFilter", "UsdJpyDIFilter"]
    warning = profile["warning"].lower()
    assert "hedging" in warning and "account currency" in warning
    assert "challenge" in warning and "0.5%" in warning
    assert "ftmo usd 10k" not in warning
    assert profile.get("website_catalog") is False
    assert published["live_account_access"] is False


def test_new_bat_routes_to_named_wrapper_and_preserves_argument_forwarding():
    raw = (LIVE / "Prop ready" / "Codex_Best_FTMO.bat").read_bytes()
    source = raw.decode("ascii")
    assert "-File \"%~dp0..\\Start-LiveProfile.ps1\"" in source
    assert '-Portfolio "codex-best-ftmo" %*' in source
    assert 'set "CALYX_EXIT=%ERRORLEVEL%"' in source
    assert "exit /b %CALYX_EXIT%" in source
    assert "Start-Process" not in source and "terminal64" not in source


def test_reused_nine_ea_distribution_is_byte_identical_not_a_new_strategy_build():
    # Frozen before this launcher change: neither compile nor altered .set files
    # are necessary. The new name is an installer/profile variant only.
    expected = {
        "PACKAGE.json": "8c0283bb4a5f3799932fcdd0f58a7cf263db96b2c9ac9515a607a76510621959",
        "CalyxFTMOGuard.mqh": "2999964d27af94dd548bea34b7756916cd59c245b3537491246cc241bffde813",
        "Account-Helpers.ps1": "09356ae755b94b83fb6b7f665a9ccaaed877409488dc33ad13662f01ab0e3346",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((GENERIC / name).read_bytes()).hexdigest() == digest
    manifest = read_json(GENERIC / "PACKAGE.json")
    assert len(manifest["entries"]) == 9
    assert {entry["slug"] for entry in manifest["entries"]} == NINE
    assert manifest["currency_mode"] == "ACCOUNT_CURRENCY"
    assert manifest["hedging_required"] is True and manifest["news_enabled"] is False
    assert manifest["risk_cap_fraction"] == 0.005
    for filename, digest in manifest["files"].items():
        assert hashlib.sha256((GENERIC / "package" / filename).read_bytes()).hexdigest() == digest
    for entry in manifest["entries"]:
        values = entry["inputs"]
        if "-orb-" in entry["slug"]:
            assert float(values["InpRewardRisk"]) == 0.5
        if entry["slug"] in {"nasdaq-5m-candle-momentum", "usdjpy-london-open-momentum"}:
            assert values["InpRequireDIAgreement"] == "true"
        if entry["slug"] == "usdjpy-london-open-momentum":
            assert values["InpUseADXFilter"] == "true" and float(values["InpADXMinimum"]) == 20


def test_codex_wrapper_uses_broker_neutral_variant_and_prompts_phase_only_for_codex():
    source = WRAPPER.read_text(encoding="utf-8-sig")
    assert "'codex-best-ftmo'" in source.split("param(", 1)[1].split(")\n", 1)[0]
    codex = re.search(r"'codex-best-ftmo'\s*\{(.*?)\n\s*\}\s*\n\s*'", source, re.S)
    assert codex
    body = codex.group(1)
    assert "Packages\\PropReady\\Install-Portfolio.ps1" in body
    assert "$arguments.ProfileVariant='Codex_Best_FTMO'" in body
    assert "$arguments.Phase=$Phase" in body
    assert "Packages\\FTMO" not in body
    assert "$PSBoundParameters.ContainsKey('Phase')" in source
    for phase in ("Challenge", "Verification", "Funded"):
        assert phase in source
    assert "Read-Host" in source and "Read-Host 'Account mode [1]'" in source
    assert "$Phase=switch($phaseChoice){'1'{'Challenge'}'2'{'Verification'}'3'{'Funded'}" in source
    assert "[string]$GoldSymbol" in source and "[string]$NasdaqSymbol" in source and "[string]$UsdJpySymbol" in source
    assert "account currency" in source.lower()
    # Existing Prop ready stays continuous by default, rather than inheriting
    # the newly named profile's Challenge-first launch behavior.
    prop = re.search(r"'prop-ready'\s*\{(.*?)\n\s*\}\s*\n\s*'", source, re.S)
    assert prop and "else{'Funded'}" in prop.group(1)
    assert "PortfolioVariant" not in prop.group(1)


@WINDOWS
@pytest.mark.parametrize("phase", [None, "Challenge", "Verification", "Funded"])
@pytest.mark.parametrize("mode,value", [(None, None), ("PERCENT", 0.5), ("FIXED_USD", 50)])
def test_codex_validate_only_is_read_only_and_does_not_probe_symbols_accounts_or_processes(phase, mode, value):
    arguments = ["-Portfolio codex-best-ftmo", "-ValidateOnly", "-TargetTerminal 'Z:\\NO-ACCOUNT\\terminal64.exe'"]
    if phase:
        arguments.append("-Phase " + phase)
    if mode:
        arguments.append(f"-RiskMode {mode} -RiskValue {value}")
    # Unknown names are intentionally accepted during file-only validation:
    # broker inventory must never be requested before the real preflight.
    arguments.append("-GoldSymbol 'UNPROBED-GOLD' -NasdaqSymbol 'UNPROBED-US100' -UsdJpySymbol 'UNPROBED-JPY'")
    before = snapshot()
    output = powershell(blocked_commands() + f"& {quote(WRAPPER)} {' '.join(arguments)}\n")
    assert "Codex_Best_FTMO" in output
    assert "PASS: 9 integrity-checked guarded EAs" in output and "No account accessed" in output
    assert "Forbidden in offline validation" not in output
    assert snapshot() == before


@WINDOWS
@pytest.mark.parametrize("nasdaq,jpy", [("ON", "ON"), ("OFF", "ON"), ("ON", "OFF"), ("OFF", "OFF")])
def test_codex_di_choices_and_fixed_or_percent_use_existing_pure_preset_helper(nasdaq, jpy):
    script = imports(SHARED, ["Read-SetInputs"]) + imports(HELPERS, ["Get-PropReadyPresetInputs"])
    script += f"""
$Package={quote(GENERIC / 'package')}
$NasdaqDIFilter={quote(nasdaq)};$UsdJpyDIFilter={quote(jpy)}
$manifest=Get-Content -Raw -LiteralPath {quote(GENERIC / 'PACKAGE.json')} | ConvertFrom-Json
$out=@()
foreach($RiskMode in @('FIXED_USD','PERCENT')){{
 [double]$RiskValue=if($RiskMode -eq 'PERCENT'){{0.5}}else{{50}}
 foreach($entry in $manifest.entries){{
  $out+=[pscustomobject]@{{slug=$entry.slug;mode=$RiskMode;value=$RiskValue;
   before=(Read-SetInputs (Join-Path $Package $entry.settings));inputs=(Get-PropReadyPresetInputs $entry)}}
 }}
}}
$out | ConvertTo-Json -Depth 12 -Compress
"""
    rows = json.loads(powershell(script))
    assert len(rows) == 18
    for row in rows:
        expected = row["before"].copy()
        expected["FTMOAllocationMode"] = "1" if row["mode"] == "PERCENT" else "0"
        expected["FTMOAllocationValue"] = "0.5" if row["mode"] == "PERCENT" else "50"
        if row["slug"] == "nasdaq-5m-candle-momentum":
            expected["InpRequireDIAgreement"] = str(nasdaq == "ON").lower()
        if row["slug"] == "usdjpy-london-open-momentum":
            expected["InpRequireDIAgreement"] = str(jpy == "ON").lower()
            assert row["inputs"]["InpUseADXFilter"] == "true"
            assert float(row["inputs"]["InpADXMinimum"]) == 20
        assert row["inputs"] == expected


def symbol_imports():
    return imports(SHARED, ["Normalize-Symbol", "Find-BrokerSymbol"]) + imports(INSTALLER, ["Find-CodexCashSymbol"])


def symbol_fixture():
    return """
function New-FixtureSymbol([string]$Name='US100.cash') {
 return [pscustomobject]@{name=$Name;path='Cash CFD';trade_mode=4;visible=$false;
  volume_min=0.01;volume_step=0.01;volume_max=100.0;trade_contract_size=1.0}
}
"""


@WINDOWS
def test_codex_cash_symbol_exact_alias_and_prompt_fallback_are_fixture_only():
    script = symbol_imports() + symbol_fixture()
    script += """
$out=@()
foreach($name in @('USTECm','US100.cash','m.NAS100','XAUUSD.a','pro.GOLD','USDJPYm')){
 $aliases=if($name -match 'XAU|GOLD'){@('XAUUSD','GOLD')}elseif($name -match 'JPY'){@('USDJPY')}else{@('USTEC','US100','NAS100')}
 $symbols=@((New-FixtureSymbol $name),(New-FixtureSymbol 'IRRELEVANT'))
 $found=Find-CodexCashSymbol $symbols $aliases '' 'fixture'
 $out+=[pscustomobject]@{kind='alias';expected=$name;actual=$found.name}
}
$symbols=@((New-FixtureSymbol 'BrokerTech.cash'))
$found=Find-CodexCashSymbol $symbols @('USTEC','US100','NAS100') 'BrokerTech.cash' 'US100'
$out+=[pscustomobject]@{kind='exact';expected='BrokerTech.cash';actual=$found.name}
$script:prompts=0
function Read-Host { param($Prompt) $script:prompts++;return 'BrokerTech.cash' }
$found=Find-CodexCashSymbol $symbols @('NO-ALIAS') '' 'US100'
$out+=[pscustomobject]@{kind='prompt';expected='BrokerTech.cash';actual=$found.name;prompts=$script:prompts}
'__SYMBOLS__'+($out | ConvertTo-Json -Depth 5 -Compress)
"""
    rows = json.loads(powershell(script).split("__SYMBOLS__")[-1].strip())
    assert len(rows) == 8
    assert all(row["expected"] == row["actual"] for row in rows)
    assert rows[-1]["prompts"] == 1


@WINDOWS
def test_codex_symbols_reject_missing_disabled_duplicate_futures_and_bad_contracts():
    script = symbol_imports() + symbol_fixture() + "$out=@()\n"
    changes = [
        ("missing", "$symbols=@((New-FixtureSymbol 'OTHER'))"),
        ("disabled", "$s.trade_mode=0"),
        ("close-only", "$s.trade_mode=3"),
        ("duplicate", "$symbols=@($s,(New-FixtureSymbol 'US100.cash'))"),
        ("future-path", "$s.path='Index Futures'"),
        ("future-name", "$s.name='US100 Future';$exact='US100 Future'"),
        ("zero-min", "$s.volume_min=0"),
        ("zero-step", "$s.volume_step=0"),
        ("bad-max", "$s.volume_max=0.001"),
        ("zero-contract", "$s.trade_contract_size=0"),
    ]
    for label, change in changes:
        script += f"""
$s=New-FixtureSymbol;$symbols=@($s);$exact='US100.cash'
{change}
$blocked=$false;$errorText=''
try{{$null=Find-CodexCashSymbol $symbols @('USTEC','US100','NAS100') $exact 'US100'}}catch{{$blocked=$true;$errorText=$_.Exception.Message}}
$out+=[pscustomobject]@{{case={quote(label)};blocked=$blocked;error=$errorText}}
"""
    script += """
function Read-Host { param($Prompt) return '' }
$blocked=$false;$errorText=''
try{$null=Find-CodexCashSymbol @((New-FixtureSymbol 'OTHER')) @('NO-ALIAS') '' 'US100'}catch{$blocked=$true;$errorText=$_.Exception.Message}
$out+=[pscustomobject]@{case='blank-prompt-cancels';blocked=$blocked;error=$errorText}
'__REJECTIONS__'+($out | ConvertTo-Json -Depth 5 -Compress)
"""
    rows = json.loads(powershell(script).split("__REJECTIONS__")[-1].strip())
    assert len(rows) == len(changes) + 1
    assert all(row["blocked"] and row["error"] for row in rows), rows


@WINDOWS
def test_codex_symbol_geometry_rejects_every_nonfinite_nonpositive_contract_field():
    script = symbol_imports() + symbol_fixture() + """
$out=@()
foreach($field in @('volume_min','volume_max','volume_step','trade_contract_size')){
 foreach($value in @([double]::NaN,[double]::PositiveInfinity,[double]::NegativeInfinity,0.0,-1.0)){
  $s=New-FixtureSymbol;$s.$field=$value;$blocked=$false;$errorText=''
  try{$null=Find-CodexCashSymbol @($s) @('USTEC','US100','NAS100') 'US100.cash' 'US100'}catch{$blocked=$true;$errorText=$_.Exception.Message}
  $out+=[pscustomobject]@{field=$field;blocked=$blocked;error=$errorText}
 }
}
$out | ConvertTo-Json -Depth 5 -Compress
"""
    rows = json.loads(powershell(script))
    assert len(rows) == 20
    assert all(row["blocked"] and "cash-contract" in row["error"] for row in rows), rows


@WINDOWS
def test_codex_symbol_names_reject_chart_injection_in_explicit_auto_and_prompt_paths():
    script = symbol_imports() + symbol_fixture() + """
$out=@()
foreach($code in @(10,13,0,0x200b,0x2028,0x2029,60,62,61)){
 $unsafe='USTEC'+[char]$code+'m'
 foreach($kind in @('explicit','auto','prompt')){
  $s=New-FixtureSymbol $unsafe;$symbols=@($s);$exact='';$aliases=@('USTEC')
  if($kind -eq 'explicit'){$exact=$unsafe}
  if($kind -eq 'prompt'){
   $script:fixtureAnswer=$unsafe
   function Read-Host { param($Prompt) return $script:fixtureAnswer }
   $aliases=@('NO-ALIAS')
  }
  $blocked=$false;$errorText=''
  try{$null=Find-CodexCashSymbol $symbols $aliases $exact 'US100'}catch{$blocked=$true;$errorText=$_.Exception.Message}
  $out+=[pscustomobject]@{code=$code;kind=$kind;blocked=$blocked;error=$errorText}
 }
}
'__UNSAFE__'+($out | ConvertTo-Json -Depth 5 -Compress)
"""
    rows = json.loads(powershell(script).split("__UNSAFE__")[-1].strip())
    assert len(rows) == 27
    assert all(row["blocked"] and "unsafe" in row["error"].lower() for row in rows), rows


@WINDOWS
def test_codex_only_overrides_cannot_change_legacy_prop_ready_behavior():
    script = blocked_commands() + f"""
$out=@()
foreach($layer in @('wrapper','installer')){{
 $path={quote(INSTALLER)};$arguments=@{{ValidateOnly=$true;GoldSymbol='XAUUSD.fixture'}}
 if($layer -eq 'wrapper'){{$path={quote(WRAPPER)};$arguments.Portfolio='prop-ready'}}
 $blocked=$false;$errorText=''
 try{{& $path @arguments}}catch{{$blocked=$true;$errorText=$_.Exception.Message}}
 $out+=[pscustomobject]@{{layer=$layer;blocked=$blocked;error=$errorText}}
}}
'__LEGACY__'+($out | ConvertTo-Json -Depth 5 -Compress)
"""
    before = snapshot()
    rows = json.loads(powershell(script).split("__LEGACY__")[-1].strip())
    assert len(rows) == 2
    assert all(row["blocked"] and "only" in row["error"].lower() for row in rows), rows
    assert all("Forbidden in offline validation" not in row["error"] for row in rows), rows
    assert snapshot() == before


def test_branding_keeps_account_baseline_and_shared_guard_identity():
    source = INSTALLER.read_text(encoding="utf-8-sig")
    assert "[ValidateSet('PropReady','Codex_Best_FTMO')][string]$ProfileVariant='PropReady'" in source
    assert '$statePath=Join-Path $dataRoot ("MQL5\\Files\\Calyx-PropReady-$login-$serverHash.json")' in source
    assert "$reference=Get-PropReadyReference $probe $oldState" in source
    assert "Get-PropReadyPresetInputs $entry" in source
    assert "$inputs['FTMOExpectedCurrency']=$currency" in source
    assert "$inputs['FTMOExpectedSymbol']=$resolved[$entry.symbol]" in source
    assert "$inputs['FTMOReferenceBalance']=$initial.ToString" in source
    assert "$inputs['FTMOPhase']=[string]$phaseNumber" in source
    assert "Assert-PropReadyConfirmation $probe $confirmation" in source
    assert "Set-IniValue $commonIni 'Experts' 'Enabled' '0'" in source
    assert "No automatic liquidation" in source
    assert "Start-Process -FilePath $terminalPath" in source and "-WindowStyle Hidden" in source
    assert "[string]$NasdaqDIFilter='ON'" in source and "[string]$UsdJpyDIFilter='ON'" in source
    guard = (GENERIC / "CalyxFTMOGuard.mqh").read_text(encoding="utf-8-sig")
    for factor in ("0.005", "0.0225", "0.015", "0.03", "0.92", "0.90", "0.05"):
        assert f"return FTMOReferenceBalance*{factor};" in guard
    assert "MathMin(FTMORiskCap(),requested)" in guard
    assert "MathFloor(desired/step+1e-9)*step" in guard
    assert 'return FTMOReject(result,"minimum lot exceeds budget")' in guard
