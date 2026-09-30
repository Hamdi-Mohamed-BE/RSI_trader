"""Install-CalyxBot.ps1 against FAKE MT5 data folders only (never a real terminal)."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.store import config

INSTALLER = config.INSTALLER_TEMPLATE_ROOT / "Install-CalyxBot.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(sys.platform != "win32" or POWERSHELL is None, reason="Windows PowerShell required")

KEY = "CLX-TESTA-TESTB-TESTC-TESTD"


def utf16(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-16"))


def package(tmp: Path) -> Path:
    pkg = tmp / "Calyx Test Bot"
    pkg.mkdir()
    shutil.copyfile(INSTALLER, pkg / "Install-CalyxBot.ps1")
    (pkg / "Calyx Test EA.ex5").write_bytes(b"EX5-DUMMY")
    utf16(pkg / "Test Bot - Calyx.set", f"InpCalyxLicenseKey={KEY}\r\nInpCalyxProduct=test-bot\r\nInpMagic=4242\r\nInpRiskPercent=1\r\n")
    return pkg


def fake_terminal(root: Path, name: str, origin: str | None, ini: str | None = None) -> Path:
    folder = root / name
    (folder / "MQL5" / "Experts").mkdir(parents=True)
    if origin is not None:
        utf16(folder / "origin.txt", origin)
    if ini is not None:
        utf16(folder / "config" / "common.ini", ini)
    return folder


def run(pkg: Path, *args: str) -> subprocess.CompletedProcess:
    command = [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
               str(pkg / "Install-CalyxBot.ps1"), "-BotName", "Test Bot", "-DefaultSymbol", "XAUUSD",
               "-PeriodMinutes", "5", "-AllowUrl", "https://calyx.duckdns.org", *args]
    return subprocess.run(command, capture_output=True, text=True, timeout=120)


INI = "[Common]\r\nNewsEnable=1\r\n[Experts]\r\nAllowDllImport=0\r\nEnabled=0\r\nWebRequest=0\r\nWebRequestUrl=http://127.0.0.1:8799\r\n[Trades]\r\nLotsMode=0\r\n"


def test_validate_only_lists_terminals_refuses_ava_and_changes_nothing(tmp_path):
    pkg = package(tmp_path)
    root = tmp_path / "Terminal"
    good = fake_terminal(root, "0A1B2C3D4E5F60718293A4B5C6D7E8F9", r"C:\Program Files\Calyx Fake Broker MT5", INI)
    fake_terminal(root, "1111AAAA2222BBBB3333CCCC4444DDDD", r"C:\Program Files\AvaTrade MT5 Terminal", INI)
    fake_terminal(root, "2222AAAA2222BBBB3333CCCC4444DDDD", r"C:\MT5\Strategy Tester Copy", INI)
    (root / "Common").mkdir()
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    result = run(pkg, "-TerminalRoot", str(root), "-Symbol", "XAUUSD.r", "-Yes", "-ValidateOnly")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALIDATE ONLY" in result.stdout
    assert result.stdout.count("skipped (Ava/test/tester)") == 2
    assert str(good) in result.stdout and "Calyx Fake Broker MT5" in result.stdout
    assert "CLX-TESTA-****" in result.stdout and KEY not in result.stdout
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == before


def test_install_into_fake_folder_copies_files_profile_and_allow_list(tmp_path):
    pkg = package(tmp_path)
    root = tmp_path / "Terminal"
    data = fake_terminal(root, "0A1B2C3D4E5F60718293A4B5C6D7E8F9", r"C:\Program Files\Calyx Fake Broker MT5", INI)
    result = run(pkg, "-TargetDataFolder", str(data), "-Symbol", "XAUUSD.r", "-Yes")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (data / "MQL5" / "Experts" / "Calyx" / "Calyx Test EA.ex5").read_bytes() == b"EX5-DUMMY"
    assert (data / "MQL5" / "Presets" / "Test Bot - Calyx.set").is_file()
    assert (data / "MQL5" / "Profiles" / "Tester" / "Test Bot - Calyx.set").is_file()
    chart = (data / "MQL5" / "Profiles" / "Charts" / "Calyx - Test Bot" / "chart01.chr").read_bytes().decode("utf-16")
    assert "symbol=XAUUSD.r" in chart and "period_type=0" in chart and "period_size=5" in chart
    assert "path=Experts\\Calyx\\Calyx Test EA.ex5" in chart and "name=Calyx Test EA" in chart
    assert f"InpCalyxLicenseKey={KEY}" in chart and "InpMagic=4242" in chart
    assert "<expert>" in chart and "expertmode=0" in chart  # attached, Algo Trading NOT allowed automatically
    ini = (data / "config" / "common.ini").read_bytes()
    assert ini.startswith(b"\xff\xfe")
    text = ini.decode("utf-16")
    if "WebRequest  -> NOT edited" in result.stdout:
        pytest.fail("fake terminal was treated as running: " + result.stdout)
    assert "WebRequest=1" in text and "WebRequestUrl=http://127.0.0.1:8799;https://calyx.duckdns.org" in text
    assert "Enabled=0" in text  # the Algo Trading switch is never touched
    assert "[Trades]" in text and "LotsMode=0" in text
    assert list((data / "config").glob("common.ini.calyx-backup-*"))
    assert "Allow Algo Trading" in result.stdout and "never" in result.stdout
    # idempotent second run: URL is not duplicated
    again = run(pkg, "-TargetDataFolder", str(data), "-Symbol", "XAUUSD.r", "-Yes")
    assert again.returncode == 0
    assert (data / "config" / "common.ini").read_bytes().decode("utf-16").count("calyx.duckdns.org") == 1


def test_unknown_terminal_location_gets_manual_webrequest_steps(tmp_path):
    pkg = package(tmp_path)
    data = fake_terminal(tmp_path / "Terminal", "0A1B2C3D4E5F60718293A4B5C6D7E8F9", None, INI)
    result = run(pkg, "-TargetDataFolder", str(data), "-Symbol", "GOLD", "-Yes")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WebRequest  -> NOT edited" in result.stdout and "Allow WebRequest for listed URL" in result.stdout
    assert (data / "config" / "common.ini").read_bytes().decode("utf-16") == INI


def test_refuses_ava_target_bad_symbol_and_missing_files(tmp_path):
    pkg = package(tmp_path)
    ava = fake_terminal(tmp_path / "Terminal", "1111AAAA2222BBBB3333CCCC4444DDDD", r"C:\Program Files\AvaTrade MT5 Terminal")
    refused = run(pkg, "-TargetDataFolder", str(ava), "-Yes", "-ValidateOnly")
    assert refused.returncode == 1 and "Refusing" in refused.stdout
    good = fake_terminal(tmp_path / "Terminal", "0A1B2C3D4E5F60718293A4B5C6D7E8F9", r"C:\Program Files\Calyx Fake Broker MT5")
    assert run(pkg, "-TargetDataFolder", str(good), "-Symbol", "XAU USD;rm", "-Yes").returncode == 1
    not_mt5 = tmp_path / "empty"
    not_mt5.mkdir()
    assert "not an MT5 data folder" in run(pkg, "-TargetDataFolder", str(not_mt5), "-Yes").stdout
    (pkg / "Calyx Test EA.ex5").unlink()
    assert run(pkg, "-TargetDataFolder", str(good), "-Yes", "-ValidateOnly").returncode == 1
