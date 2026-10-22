"""One folder per portfolio, and the FTMO any-broker test build. Offline only; never probes an MT5 account."""
import hashlib
import json
import os
import subprocess

import pytest
from app.catalog import PACKAGE_ROOT

LIVE = PACKAGE_ROOT / '_00 Live profiles'
FTMO = LIVE / 'Packages/FTMO'
ANY = LIVE / 'Packages/FTMO-AnyBroker'
NEUTRAL = LIVE / 'Packages/PropReady'
UNARMED = {'FTMOExpectedLogin': '0', 'FTMOExpectedServer': '', 'FTMOExpectedSymbol': '', 'FTMOExpectedCurrency': '',
           'FTMOReferenceBalance': '0', 'FTMOStartUtcTime': '0', 'FTMOPhase': '3'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_set(path):
    return dict(line.split('=', 1) for line in path.read_text(encoding='utf-8-sig').splitlines() if '=' in line)


FOLDERS = sorted(p.parent for p in LIVE.glob('*/PORTFOLIO.json'))


def test_every_named_launcher_has_its_own_folder_with_a_manifest():
    profiles = load(LIVE / 'Profiles.json')['profiles']
    assert {LIVE / p['folder'] for p in profiles} == set(FOLDERS)
    for p in profiles:
        assert (LIVE / p['folder'] / p['file']).is_file()
        listed = {(lp['slug'], lp['file']) for lp in load(LIVE / p['folder'] / 'PORTFOLIO.json')['launchers']}
        assert (p['slug'], p['file']) in listed


@pytest.mark.parametrize('folder', FOLDERS, ids=lambda p: p.name)
def test_folder_copies_are_exactly_what_the_launcher_installs(folder):
    manifest = load(folder / 'PORTFOLIO.json')
    for build in manifest['builds']:
        base = folder if build['build'] == folder.name else folder / build['build']
        expected = {'EAs': set(), 'Sets': set()}
        for m in build['members']:
            for key in ('expert', 'settings'):
                copy = base / m[key]
                source = (PACKAGE_ROOT / m['source_' + key]).resolve()
                assert sha(copy) == m[key + '_sha256'] == sha(source), (m['label'], key)
                expected[m[key].split('/', 1)[0]].add(m[key].split('/', 1)[1])
        for kind, names in expected.items():
            assert {p.name for p in (base / kind).iterdir()} == names, 'stray or missing copy in ' + str(base / kind)


def test_full_portfolio_folder_lists_all_37_installer_items():
    build = load(LIVE / 'Full EA portfolio - Recommended Adaptive/PORTFOLIO.json')['builds'][0]
    assert len(build['members']) == 37 and len({m['label'] for m in build['members']}) == 37


def test_any_broker_build_keeps_every_ftmo_strategy_input_and_only_unarms_the_account_binding():
    ftmo, any_broker = load(FTMO / 'PACKAGE.json'), load(ANY / 'PACKAGE.json')
    assert [e['slug'] for e in any_broker['entries']] == [e['slug'] for e in ftmo['entries']]
    assert len(any_broker['entries']) == 17 and not any_broker['news_enabled']
    assert any_broker['risk_cap_fraction'] == .005 and any_broker['currency_mode'] == 'ACCOUNT_CURRENCY'
    assert any_broker['source_version'] == ftmo['version'] and any_broker['source_guard_sha'] == ftmo['guard_sha']
    for a, f in zip(any_broker['entries'], ftmo['entries']):
        built, original = read_set(ANY / 'package' / a['settings']), read_set(FTMO / 'package' / f['settings'])
        assert {k: v for k, v in built.items() if k not in UNARMED} == {k: v for k, v in original.items() if k not in UNARMED}
        assert {k: built[k] for k in UNARMED} == UNARMED
        assert sha(ANY / 'package' / a['expert']) == a['expert_sha'] and sha(ANY / 'package' / a['settings']) == a['settings_sha']
    for name, digest in any_broker['files'].items():
        assert sha(ANY / 'package' / name) == digest, name


def test_any_broker_build_uses_the_broker_neutral_guard_and_leaves_ftmo_and_prop_ready_untouched():
    any_broker, neutral, ftmo = load(ANY / 'PACKAGE.json'), load(NEUTRAL / 'PACKAGE.json'), load(FTMO / 'PACKAGE.json')
    assert sha(ANY / 'CalyxFTMOGuard.mqh') == sha(NEUTRAL / 'CalyxFTMOGuard.mqh') == any_broker['guard_sha'] == neutral['guard_sha']
    guard = (ANY / 'CalyxFTMOGuard.mqh').read_text(encoding='utf-8-sig')
    assert 'ACCOUNT_COMPANY' not in guard and '10000.0' not in guard
    assert sha(FTMO / 'CalyxFTMOGuard.mqh') == ftmo['guard_sha']
    for name, digest in ftmo['files'].items():
        assert sha(FTMO / 'package' / name) == digest, name
    for name, digest in neutral['files'].items():
        assert sha(NEUTRAL / 'package' / name) == digest, name
    # Same strategy sources as Prop Ready for the shared nine.
    shared = {p.name for p in (NEUTRAL / 'package').iterdir() if p.suffix in ('.mq5', '.mqh', '.set')}
    for name in shared & {p.name for p in (ANY / 'package').iterdir()}:
        assert sha(NEUTRAL / 'package' / name) == sha(ANY / 'package' / name), name


def test_any_broker_installer_is_the_neutral_installer_with_the_17_roster():
    text = (ANY / 'Install-Portfolio.ps1').read_text(encoding='utf-8-sig')
    assert 'entries.Count -ne 17' in text and "'Calyx-FTMO17-AnyBroker'" in text
    assert all("'" + e['slug'] + "'" in text for e in load(FTMO / 'PACKAGE.json')['entries'])
    assert 'Assert-PropReadyAccount' in text and "-notmatch '(?i)FTMO'" not in text
    assert 'Start-Process' in text and "Set-IniValue $commonIni 'Experts' 'Enabled' '0'" in text  # Algo Trading stays OFF


@pytest.mark.skipif(os.name != 'nt', reason='Windows launcher validation')
def test_any_broker_bat_validate_only_is_offline():
    bat = LIVE / 'FTMO guarded - Current 14' / 'FTMO guarded - Current 14 - ANY BROKER TEST.bat'
    before = {p: sha(p) for p in ANY.rglob('*') if p.is_file()}
    result = subprocess.run(['cmd.exe', '/c', str(bat), '-ValidateOnly'], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS: 17 integrity-checked guarded EAs (any-broker test build)' in result.stdout
    assert 'Finding MT5' not in result.stdout and 'Broker:' not in result.stdout
    assert before == {p: sha(p) for p in ANY.rglob('*') if p.is_file()}
