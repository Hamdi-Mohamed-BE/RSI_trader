"""Build the broker-neutral TEST copy of the 17-EA FTMO guarded portfolio. Never connect to MT5.

Owner request 2026-10-22: run the FTMO portfolio on any broker for a while. Strategy sources/settings come from the frozen
FTMO package; the admission guard, account binding and installer are the broker-neutral Prop Ready ones (same limits as
fractions of the saved first-install balance: 0.5% per entry, 2.25% total, 1.5% per symbol, 3% daily reserve, 92% entry
buffer, 90% floor). The FTMO and Prop Ready packages are never written.
"""
import copy
import json
import re
import shutil

from tools.build_live_profiles import R, read, sha, save, write, compile_ea

SOURCE = R / 'Packages/FTMO'
NEUTRAL = R / 'Packages/PropReady'
TARGET = R / 'Packages/FTMO-AnyBroker'
VERSION = 'FTMO17-ANY-BROKER-TEST-20261030'


def installer(slugs):
    """The Prop Ready installer with the 17-EA roster, its own names and extended broker-symbol matching."""
    text = read(NEUTRAL / 'Install-Portfolio.ps1')
    roster = "    $expected=@(" + ','.join("'" + s + "'" for s in slugs) + ")\n"
    replacements = [
        ("$isCodexProfile=$ProfileVariant -eq 'Codex_Best_FTMO'\n"
         "$profileDisplay=if($isCodexProfile){'Codex_Best_FTMO'}else{'PROP READY'}\n"
         "$profileFolderPrefix=if($isCodexProfile){'Codex_Best_FTMO'}else{'Calyx-PropReady9'}\n"
         "$profileDeploymentLabel=if($isCodexProfile){'Codex_Best_FTMO'}else{'Prop Ready 9'}\n"
         "$profileValidationLabel=if($isCodexProfile){'Codex_Best_FTMO installed profile'}else{'Prop Ready installed profile'}\n"
         "$profileBackupSuffix=if($isCodexProfile){'.Codex_Best_FTMO-backup-'}else{'.prop-ready-backup-'}\n",
         "# Any-broker test build: extended cash-symbol matching and exact overrides are always available.\n"
         "$isCodexProfile=$true\n"
         "$profileDisplay='FTMO ANY BROKER'\n"
         "$profileFolderPrefix='Calyx-FTMO17-AnyBroker'\n"
         "$profileDeploymentLabel='FTMO guarded 17 any-broker test'\n"
         "$profileValidationLabel='FTMO any-broker installed profile'\n"
         "$profileBackupSuffix='.ftmo-any-broker-backup-'\n"),
        ("if($manifest.entries.Count -ne 9 -or", "if($manifest.entries.Count -ne 17 -or"),
        ("{throw 'Unexpected Prop Ready package policy.'}", "{throw 'Unexpected FTMO any-broker package policy.'}"),
        ("    $expected=@('nasdaq-5m-candle-momentum','usdjpy-london-open-momentum','us100-month-end-flow','xau-rsi-vwap',\n"
         "        'us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30')\n",
         roster),
        ("{throw 'Prop Ready roster changed.'}", "{throw 'FTMO any-broker roster changed.'}"),
        ('Write-Host "${profileDisplay}: nine EAs / five ORBs at 0.5R / broker-neutral MT5 hedging profile."',
         'Write-Host "${profileDisplay}: the 17 FTMO-guarded EAs / five ORBs at 0.5R / broker-neutral TEST build for any MT5 hedging account."'),
        ("Write-Host 'PASS: 9 integrity-checked guarded EAs; all five ORBs at 0.5R. No account accessed.'",
         "Write-Host 'PASS: 17 integrity-checked guarded EAs (any-broker test build); all five ORBs at 0.5R. No account accessed.'"),
        ('Review all nine charts and inputs', 'Review all 17 charts and inputs'),
    ]
    for old, new in replacements:
        assert text.count(old) == 1, old[:80]
        text = text.replace(old, new)
    return text


def main():
    manifest = json.loads(read(SOURCE / 'PACKAGE.json'))
    neutral = json.loads(read(NEUTRAL / 'PACKAGE.json'))
    protected = {p: sha(p) for base in (SOURCE, NEUTRAL) for p in base.rglob('*') if p.is_file()}
    for name, digest in manifest['files'].items():
        assert sha(SOURCE / 'package' / name) == digest, name
    assert sha(SOURCE / 'CalyxFTMOGuard.mqh') == manifest['guard_sha']
    assert sha(NEUTRAL / 'CalyxFTMOGuard.mqh') == neutral['guard_sha']
    entries = copy.deepcopy(manifest['entries'])
    slugs = [e['slug'] for e in entries]
    assert len(entries) == 17 == len(set(slugs)) and manifest['news_enabled'] is False
    assert {e['symbol'] for e in entries} <= {'XAUUSD', 'USTEC', 'USDJPY'}
    package = TARGET / 'package'
    assert not package.exists(), f'{package} exists; this builder only creates a fresh package'
    package.mkdir(parents=True)
    shutil.copy2(NEUTRAL / 'CalyxFTMOGuard.mqh', TARGET / 'CalyxFTMOGuard.mqh')
    for name in ('Account-Helpers.ps1', 'probe_account.py'):
        shutil.copy2(NEUTRAL / name, TARGET / name)
    copied = set()

    def copy_graph(name):
        if name in copied:
            return
        assert '/' not in name and '\\' not in name and name not in ('.', '..')
        copied.add(name)
        if name == 'CalyxFTMOGuard.mqh':
            shutil.copy2(TARGET / name, package / name)
            return
        text = read(SOURCE / 'package' / name)
        if name == 'FTMO_Trade.mqh':
            # Same broker filling adaptation as Prop Ready (IOC-only brokers).
            pattern = r'(bool CTrade::FillingCheck\(const string symbol\)\s*\{)'
            text, count = re.subn(pattern, r'\1\n   ENUM_ORDER_TYPE_FILLING mode=m_type_filling;\n'
                r'   if(!FTMOMarketFilling(symbol,mode))return false;\n'
                r'   m_type_filling=mode;\n', text)
            assert count == 1, 'CTrade filling entry point changed'
        write(package / name, text)
        for child in re.findall(r'#include\s+"([^"]+)"', text):
            copy_graph(child)

    for entry in entries:
        source = entry['expert'].replace('.ex5', '.mq5')
        copy_graph(source)
        compile_ea(package / source)
        values = entry['inputs']
        assert values['InpRiskPercent'] == '0.5' and values['InpAdaptivePortfolioControls'] == 'false'
        if entry['slug'] in manifest['orb_keys']:
            assert values['InpRewardRisk'] == '0.5'
        values.update(FTMOExpectedLogin='0', FTMOExpectedServer='', FTMOExpectedSymbol='',
                      FTMOExpectedCurrency='', FTMOReferenceBalance='0', FTMOStartUtcTime='0',
                      FTMOPhase='3')
        write(package / entry['settings'], '\n'.join(k + '=' + str(v) for k, v in values.items()) + '\n')
        entry['expert_sha'] = sha(package / entry['expert'])
        entry['settings_sha'] = sha(package / entry['settings'])
    write(TARGET / 'Install-Portfolio.ps1', installer(slugs))
    save(TARGET / 'PACKAGE.json', dict(
        version=VERSION, purpose='Owner test build: the 17 FTMO-guarded EAs on any MT5 hedging account/broker.',
        entries=entries, orb_keys=manifest['orb_keys'], news_enabled=False, currency_mode='ACCOUNT_CURRENCY',
        hedging_required=True, reference_mode='PERSISTED_FIRST_INSTALL_BALANCE', default_phase='Funded',
        risk_cap_fraction=.005, risk_cap_input='FTMORiskCapPercent (installer = chosen risk, max 2%; 0.005 is the default)', guard_sha=sha(TARGET / 'CalyxFTMOGuard.mqh'),
        guard_source='Packages/PropReady/CalyxFTMOGuard.mqh', source_version=manifest['version'],
        source_guard_sha=manifest['guard_sha'], neutral_installer_source_sha=sha(NEUTRAL / 'Install-Portfolio.ps1'),
        files={str(p.relative_to(package)).replace('\\', '/'): sha(p)
               for p in package.rglob('*') if p.is_file() and p.suffix != '.log'},
    ))
    assert all(sha(p) == digest for p, digest in protected.items())
    print('Built 17 broker-neutral guarded EAs (any-broker test); FTMO and Prop Ready files unchanged. No MT5 account accessed.')


if __name__ == '__main__':
    main()
