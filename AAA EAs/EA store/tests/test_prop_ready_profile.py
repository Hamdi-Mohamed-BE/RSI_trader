"""Offline-only regression checks for the selected nine-EA Prop ready launcher.

Pure helpers are extracted from PowerShell's AST, never by executing an installer.
The only complete launcher invocation is its independently checked ValidateOnly
early-return path, with account/process/write commands replaced by failing stubs.
"""

import hashlib
import importlib
import json
import os
import re
import subprocess

import pytest

from app.catalog import PACKAGE_ROOT


LIVE = PACKAGE_ROOT / "_00 Live profiles"
FTMO = LIVE / "Packages" / "FTMO"
INSTALLER = FTMO / "Install-Portfolio.ps1"
SELECTOR = FTMO / "Profile-Selection.ps1"
SHARED = PACKAGE_ROOT / "_Auto Deploy" / "Install-BMTradingPortfolio.ps1"
WRAPPER = LIVE / "Start-LiveProfile.ps1"

PROP_READY = (
    "xau-rsi-vwap",
    "xau-orb-london-ny-overlap-m30",
    "us100-h1-orb-13utc",
    "usdjpy-london-open-momentum",
    "us100-month-end-flow",
    "nasdaq-5m-candle-momentum",
    "us100-orb-new-york-m30",
    "us100-selective-orb-v3",
    "xau-orb-new-york-m30",
)
ORBS = {
    "xau-orb-london-ny-overlap-m30",
    "us100-h1-orb-13utc",
    "us100-orb-new-york-m30",
    "us100-selective-orb-v3",
    "xau-orb-new-york-m30",
}
ORIGINAL_FTMO = (
    "xau-rsi-vwap",
    "gold-overnight-value-area",
    "xau-squeeze-momentum-standard",
    "dmc-fresh-reaction-us100",
    "ema3",
    "xau-trend-progression",
    "xau-orb-london-ny-overlap-m30",
    "nasdaq-overnight",
    "us100-h1-orb-13utc",
    "usdjpy-london-open-momentum",
    "us100-month-end-flow",
    "dmc-current-xau",
    "nasdaq-5m-candle-momentum",
    "3-way-gold",
    "us100-orb-new-york-m30",
    "us100-selective-orb-v3",
    "xau-orb-new-york-m30",
)

WINDOWS = pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell pure-helper tests")


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def powershell(script):
    result = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=LIVE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def import_helpers(path, names):
    """Import declaration text only, excluding the installer's top-level body."""
    return f"""
function Import-PropReadyTestHelpers($path,$names) {{
 $tokens=$null;$errors=$null
 $ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
 if($errors.Count){{throw 'PowerShell parse failure'}}
 foreach($name in $names){{
  $found=@($ast.FindAll({{param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]}},$true) | Where-Object Name -eq $name)
  if($found.Count -ne 1){{throw ('Missing or ambiguous pure helper: '+$name)}}
  . ([scriptblock]::Create($found[0].Extent.Text))
  Set-Item ('Function:global:'+$name) (Get-Item ('Function:'+$name)).ScriptBlock
 }}
}}
Import-PropReadyTestHelpers {quote(path)} @({','.join(quote(name) for name in names)})
"""


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def snapshot_distribution():
    paths = [path for path in FTMO.rglob("*") if path.is_file()]
    paths += [SHARED, WRAPPER, LIVE / "Profiles.json", LIVE / "Prop ready.bat"]
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def blocked_offline_commands():
    names = (
        "Read-Host", "Get-CimInstance", "Get-WmiObject", "Get-Process",
        "Start-Process", "Stop-Process", "New-Item", "Copy-Item", "Move-Item",
        "Remove-Item", "Set-Content", "Add-Content", "Out-File", "python", "python.exe",
    )
    return "\n".join(f"function global:{name} {{ throw 'Forbidden in offline validation: {name}' }}" for name in names)


def test_prop_ready_is_named_local_profile_with_explicit_safe_defaults():
    profiles = read_json(LIVE / "Profiles.json")["profiles"]
    selected = [profile for profile in profiles if profile["slug"] == "prop-ready"]
    assert len(selected) == 1
    profile = selected[0]
    assert profile["file"] == "Prop ready.bat"
    assert profile["eas"] == 9
    assert profile["default_mode"] == "FIXED_USD"
    assert profile["default_usd"] == 50
    assert profile["default_percent"] == 0.5
    assert profile["default_news_percent"] == 0
    assert profile["di_parameters"] == ["NasdaqDIFilter", "UsdJpyDIFilter"]
    assert profile["website_catalog"] is False
    bat = (LIVE / profile["file"]).read_text(encoding="utf-8-sig")
    assert '%~dp0Start-LiveProfile.ps1' in bat
    assert '-Portfolio "prop-ready"' in bat
    assert "%*" in bat
    assert "Copy-Item" not in bat and "terminal64.exe" not in bat.lower()


def test_original_package_and_saved_ftmo_profile_remain_the_original_seventeen():
    manifest = read_json(FTMO / "PACKAGE.json")
    assert tuple(entry["slug"] for entry in manifest["entries"]) == ORIGINAL_FTMO
    assert manifest["news_enabled"] is False
    assert manifest["risk_usd"] == 50
    profile = next(profile for profile in read_json(LIVE / "Profiles.json")["profiles"] if profile["slug"] == "ftmo")
    assert profile["eas"] == 17
    assert profile["file"] == "FTMO guarded - Current 14.bat"
    for name, expected_hash in manifest["files"].items():
        assert hashlib.sha256((FTMO / "package" / name).read_bytes()).hexdigest() == expected_hash


def test_pure_generator_metadata_matches_the_saved_profiles_without_running_builder(monkeypatch):
    before = snapshot_distribution()

    def forbidden(*args, **kwargs):
        pytest.fail("Metadata import must not compile, launch a process, copy, or write files")

    # Importing this ordinary module must not execute its guarded main(). Its
    # named_profiles() function is metadata only, not the package builder.
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        import shutil
        from pathlib import Path

        guard.setattr(shutil, "copy2", forbidden)
        guard.setattr(shutil, "copytree", forbidden)
        guard.setattr(Path, "write_text", forbidden)
        guard.setattr(Path, "write_bytes", forbidden)
        guard.setattr(Path, "mkdir", forbidden)
        generator = importlib.import_module("tools.build_live_profiles")
        assert generator.named_profiles() == read_json(LIVE / "Profiles.json")["profiles"]
    assert snapshot_distribution() == before


@WINDOWS
def test_pure_selector_keeps_manifest_order_and_never_mutates_full_roster():
    script = import_helpers(SELECTOR, ["Get-FTMOProfileEntries"])
    script += f"""
$manifest=Get-Content -Raw -LiteralPath {quote(FTMO / 'PACKAGE.json')} | ConvertFrom-Json
$before=$manifest | ConvertTo-Json -Depth 15 -Compress
$default=@(Get-FTMOProfileEntries $manifest)
$original=@(Get-FTMOProfileEntries $manifest 'FTMO17')
$selected=@(Get-FTMOProfileEntries $manifest 'PROP_READY9')
$after=$manifest | ConvertTo-Json -Depth 15 -Compress
[pscustomobject]@{{default=@($default.slug);original=@($original.slug);selected=@($selected.slug);unchanged=($before -ceq $after)}} | ConvertTo-Json -Depth 5 -Compress
"""
    result = json.loads(powershell(script))
    assert tuple(result["default"]) == ORIGINAL_FTMO
    assert tuple(result["original"]) == ORIGINAL_FTMO
    assert tuple(result["selected"]) == PROP_READY
    assert result["unchanged"] is True
    assert not any("news" in slug or "hourly" in slug or "dmc" in slug for slug in result["selected"])
    assert {"ema3", "3-way-gold"}.isdisjoint(result["selected"])


@WINDOWS
def test_pure_selector_refuses_missing_or_duplicate_required_members():
    script = import_helpers(SELECTOR, ["Get-FTMOProfileEntries"])
    script += f"""
$raw=Get-Content -Raw -LiteralPath {quote(FTMO / 'PACKAGE.json')}
$missing=$raw | ConvertFrom-Json
$missing.entries=@($missing.entries | Where-Object slug -ne 'us100-h1-orb-13utc')
$duplicate=$raw | ConvertFrom-Json
$duplicate.entries=@($duplicate.entries[0..15]) + @($duplicate.entries[0])
$rejected=@()
foreach($candidate in @($missing,$duplicate)){{
 $blocked=$false
 try{{$null=Get-FTMOProfileEntries $candidate 'PROP_READY9'}}catch{{$blocked=$true}}
 $rejected+=@($blocked)
}}
$rejected | ConvertTo-Json -Compress
"""
    assert json.loads(powershell(script)) == [True, True]


@WINDOWS
@pytest.mark.parametrize("mode,value", [("FIXED_USD", 50), ("PERCENT", 0.5), ("FIXED_USD", 35), ("PERCENT", 0.3)])
def test_risk_and_independent_di_choices_change_only_allocation_and_requested_di(mode, value):
    script = import_helpers(SHARED, ["Read-SetInputs"])
    script += import_helpers(SELECTOR, ["Get-FTMOProfileEntries"])
    script += import_helpers(INSTALLER, ["Get-FTMOPresetInputs"])
    script += f"""
$Package={quote(FTMO / 'package')}
$RiskMode={quote(mode)};[double]$RiskValue={value}
$manifest=Get-Content -Raw -LiteralPath {quote(FTMO / 'PACKAGE.json')} | ConvertFrom-Json
$entries=@(Get-FTMOProfileEntries $manifest 'PROP_READY9')
$out=@()
foreach($nasdaq in @('ON','OFF')){{foreach($jpy in @('ON','OFF')){{
 $UsdJpyDIFilter=$jpy
 foreach($entry in $entries){{
  $out+=[pscustomobject]@{{slug=$entry.slug;nasdaq=$nasdaq;jpy=$jpy;original=(Read-SetInputs (Join-Path $Package $entry.settings));inputs=(Get-FTMOPresetInputs $entry $nasdaq)}}
 }}
}}}}
$out | ConvertTo-Json -Depth 9 -Compress
"""
    rows = json.loads(powershell(script))
    assert len(rows) == 9 * 4
    for row in rows:
        inputs = row["inputs"]
        expected = row["original"].copy()
        expected["FTMOAllocationMode"] = "0" if mode == "FIXED_USD" else "1"
        expected["FTMOAllocationValue"] = inputs["FTMOAllocationValue"]
        if row["slug"] == "nasdaq-5m-candle-momentum":
            expected["InpRequireDIAgreement"] = str(row["nasdaq"] == "ON").lower()
        if row["slug"] == "usdjpy-london-open-momentum":
            expected["InpRequireDIAgreement"] = str(row["jpy"] == "ON").lower()
            assert inputs["InpUseADXFilter"] == "true"
            assert float(inputs["InpADXMinimum"]) == 20
        assert inputs == expected, row["slug"]
        assert float(inputs["FTMOAllocationValue"]) == value
        assert float(inputs["InpRiskPercent"]) == 0.5
        assert inputs["InpAdaptivePortfolioControls"] == "false"
        assert inputs["FTMOExpectedLogin"] == "0"
        if row["slug"] in ORBS:
            assert float(inputs["InpRewardRisk"]) == 0.5


def test_existing_guard_still_caps_and_never_upsizes_the_original_request():
    manifest = read_json(FTMO / "PACKAGE.json")
    guard_path = FTMO / "CalyxFTMOGuard.mqh"
    assert hashlib.sha256(guard_path.read_bytes()).hexdigest() == manifest["guard_sha"]
    guard = guard_path.read_text(encoding="utf-8-sig")
    assert "MathMin(50.0,requested)" in guard
    assert "FTMOAllocationBudget()/unit" in guard
    assert "MathMin(r.volume" in guard
    assert "MathFloor(desired/step" in guard


def assert_validate_only_precedes_terminal_access():
    text = INSTALLER.read_text(encoding="utf-8-sig")
    early = re.search(r"if\s*\(\s*\$ValidateOnly\s*\)\s*\{", text)
    candidates = re.search(r"\$candidates\s*=\s*@\(Get-Mt5Candidates", text)
    assert early and candidates
    assert early.start() < candidates.start()
    assert re.search(r"\bexit\s+0\b", text[early.start():candidates.start()])
    assert text.index("$probeText=") > candidates.start()
    assert text.index("$dataRoot=") > candidates.start()
    assert text.index("Close-TargetTerminal $terminalPath") > candidates.start()


@WINDOWS
@pytest.mark.parametrize("arguments", ["", "-RiskMode PERCENT -RiskValue 0.3 -NasdaqDIFilter OFF -UsdJpyDIFilter ON"])
def test_validate_only_never_prompts_probes_enumerates_processes_or_writes_files(arguments):
    assert_validate_only_precedes_terminal_access()
    before = snapshot_distribution()
    script = blocked_offline_commands()
    script += f"\n& {quote(WRAPPER)} -Portfolio prop-ready -ValidateOnly -TargetTerminal 'Z:\\NO-MT5-IS-TO-BE-ACCESSED\\terminal64.exe' {arguments}\n"
    output = powershell(script)
    assert "PASS: 9 integrity-checked guarded EAs" in output and "No account accessed" in output
    assert not any(marker in output for marker in ("Finding MT5", "Selected:", "Account:", "Forbidden in offline validation"))
    assert snapshot_distribution() == before


@WINDOWS
def test_invalid_risk_or_variant_is_rejected_offline_before_any_terminal_probe():
    assert_validate_only_precedes_terminal_access()
    before = snapshot_distribution()
    script = blocked_offline_commands()
    script += f"""
$out=@()
foreach($layer in @('wrapper','installer')){{
 foreach($case in @(
  @{{name='negative';mode='FIXED_USD';value=-1.0}},
  @{{name='nan';mode='FIXED_USD';value=[double]::NaN}},
  @{{name='infinity';mode='PERCENT';value=[double]::PositiveInfinity}},
  @{{name='percent-over-limit';mode='PERCENT';value=10.01}}
 )){{
  $testArguments=@{{RiskMode=$case.mode;RiskValue=$case.value;ValidateOnly=$true}}
  $path={quote(INSTALLER)}
  if($layer -eq 'wrapper'){{$path={quote(WRAPPER)};$testArguments.Portfolio='prop-ready'}}
  else{{$testArguments.PortfolioVariant='PROP_READY9'}}
  $rejected=$false;$errorText=''
  try{{& $path @testArguments}}catch{{$rejected=$true;$errorText=$_.Exception.Message}}
  $out+=[pscustomobject]@{{layer=$layer;case=$case.name;rejected=$rejected;error=$errorText}}
 }}
}}
$rejected=$false;$errorText=''
try{{& {quote(INSTALLER)} -PortfolioVariant 'NOT_A_PORTFOLIO' -ValidateOnly}}catch{{$rejected=$true;$errorText=$_.Exception.Message}}
$out+=[pscustomobject]@{{layer='installer';case='invalid-variant';rejected=$rejected;error=$errorText}}
'__PROP_READY_REJECTIONS__'+($out | ConvertTo-Json -Depth 5 -Compress)
"""
    output = powershell(script)
    rows = json.loads(output.split("__PROP_READY_REJECTIONS__")[-1].strip())
    assert len(rows) == 9
    for row in rows:
        assert row["rejected"] is True, row
        assert "Forbidden in offline validation" not in row["error"], row
        if row["case"] == "invalid-variant":
            assert "PortfolioVariant" in row["error"] and "NOT_A_PORTFOLIO" in row["error"]
        else:
            assert "risk" in row["error"].lower(), row
    assert "Forbidden in offline validation" not in output
    assert snapshot_distribution() == before


@WINDOWS
def test_nine_chart_texts_are_generated_in_memory_with_exact_symbols_periods_inputs_and_binaries():
    before = snapshot_distribution()
    script = import_helpers(SHARED, ["Read-SetInputs", "New-ChartText"])
    script += import_helpers(SELECTOR, ["Get-FTMOProfileEntries"])
    script += import_helpers(INSTALLER, ["Get-EffectiveInputs", "Get-FTMOPresetInputs"])
    script += f"""
$Package={quote(FTMO / 'package')};$ExpertFolderName='OFFLINE-PropReady-FIXTURE'
$RiskMode='PERCENT';[double]$RiskValue=0.3;$UsdJpyDIFilter='ON'
$manifest=Get-Content -Raw -LiteralPath {quote(FTMO / 'PACKAGE.json')} | ConvertFrom-Json
$entries=@(Get-FTMOProfileEntries $manifest 'PROP_READY9')
$aliases=@{{XAUUSD='GOLD.fixture';USTEC='US100.fixture';USDJPY='USDJPY.fixture'}}
$out=@();$index=0
foreach($entry in $entries){{
 $tf=[string]$entry.timeframe
 $minutes=if($tf.StartsWith('H')){{60*[int]$tf.Substring(1)}}else{{[int]$tf.Substring(1)}}
 $inputs=Get-FTMOPresetInputs $entry 'OFF'
 $item=[pscustomobject]@{{Expert=$entry.expert;Period=$minutes;EffectiveInputs=$inputs}}
 $text=New-ChartText $item $aliases[$entry.symbol] (10000+$index) $index
 $out+=[pscustomobject]@{{slug=$entry.slug;expert=$entry.expert;symbol=$aliases[$entry.symbol];minutes=$minutes;inputs=$inputs;text=$text}}
 $index++
}}
$out | ConvertTo-Json -Depth 8 -Compress
"""
    rows = json.loads(powershell(script))
    assert tuple(row["slug"] for row in rows) == PROP_READY
    for index, row in enumerate(rows):
        text = row["text"].replace("\r\n", "\n")
        lines = text.splitlines()
        expected_type = 0 if row["minutes"] < 60 else 1
        expected_size = row["minutes"] if expected_type == 0 else row["minutes"] // 60
        assert f"id={10000 + index}" in lines
        assert f"symbol={row['symbol']}" in lines
        assert f"period_type={expected_type}" in lines
        assert f"period_size={expected_size}" in lines
        assert f"path=Experts\\OFFLINE-PropReady-FIXTURE\\{row['expert']}" in lines
        assert row["expert"].endswith(".ex5")
        for key, value in row["inputs"].items():
            assert f"{key}={value}" in lines
        assert "FTMOAllocationMode=1" in lines
        assert "FTMOExpectedLogin=0" in lines  # Offline strings remain unarmed.
        if row["slug"] == "nasdaq-5m-candle-momentum":
            assert "InpRequireDIAgreement=false" in lines
        if row["slug"] == "usdjpy-london-open-momentum":
            assert "InpRequireDIAgreement=true" in lines
            assert "InpUseADXFilter=true" in lines
        if row["slug"] in ORBS:
            assert "InpRewardRisk=0.5" in lines
    assert snapshot_distribution() == before


def pure_prompt_prefix():
    text = WRAPPER.read_text(encoding="utf-8-sig")
    dispatch = re.search(r"switch\s*\(\s*\$Portfolio\s*\)\s*\{", text)
    assert dispatch, "Cannot safely isolate prompt logic from child installer dispatch"
    prefix = text[:dispatch.start()]
    assert "Install-Portfolio.ps1" not in prefix
    assert "Start-Process" not in prefix and "Get-Mt5Candidates" not in prefix
    return prefix.replace("$PSScriptRoot", "$PropReadyTestRoot")


@WINDOWS
@pytest.mark.parametrize(
    "responses,expected",
    [
        (["", "", "", ""], {"RiskMode": "FIXED_USD", "RiskValue": 50, "NasdaqDIFilter": "ON", "UsdJpyDIFilter": "ON"}),
        (["1", "", "OFF", "ON"], {"RiskMode": "PERCENT", "RiskValue": 0.5, "NasdaqDIFilter": "OFF", "UsdJpyDIFilter": "ON"}),
        (["2", "35", "ON", "OFF"], {"RiskMode": "FIXED_USD", "RiskValue": 35, "NasdaqDIFilter": "ON", "UsdJpyDIFilter": "OFF"}),
        (["1", "0.3", "OFF", "OFF"], {"RiskMode": "PERCENT", "RiskValue": 0.3, "NasdaqDIFilter": "OFF", "UsdJpyDIFilter": "OFF"}),
    ],
)
def test_interactive_risk_and_both_di_prompts_without_child_dispatch(responses, expected):
    prefix = pure_prompt_prefix()
    script = f"""
$PropReadyTestRoot={quote(LIVE)}
$global:PropReadyAnswers=New-Object 'System.Collections.Generic.Queue[string]'
@({','.join(quote(answer) for answer in responses)}) | ForEach-Object {{$global:PropReadyAnswers.Enqueue($_)}}
$global:PropReadyPrompts=@()
function global:Read-Host([string]$Prompt){{
 $global:PropReadyPrompts+=@($Prompt)
 if($global:PropReadyAnswers.Count -eq 0){{throw 'Unexpected extra prompt'}}
 return $global:PropReadyAnswers.Dequeue()
}}
$safe=[scriptblock]::Create({quote(prefix + chr(10) + "'__PROP_READY_RESULT__'+([pscustomobject]@{arguments=$arguments;prompts=$global:PropReadyPrompts;remaining=$global:PropReadyAnswers.Count}|ConvertTo-Json -Depth 6 -Compress)")})
& $safe -Portfolio prop-ready
"""
    result = json.loads(powershell(script).split("__PROP_READY_RESULT__")[-1].strip())
    assert result["arguments"] == expected
    assert result["remaining"] == 0
    assert len(result["prompts"]) == 4
    assert "Risk type" in result["prompts"][0]
    assert "Nasdaq" in result["prompts"][2]
    assert "USDJPY" in result["prompts"][3]
    assert not any("news" in prompt.lower() or "hourly" in prompt.lower() for prompt in result["prompts"])
