"""Build the broker-neutral Prop Ready nine-EA package. Never connect to MT5.

Strategy sources/settings come from the frozen FTMO package; only the isolated
admission guard and account bindings differ. The FTMO package is never written.
"""
import copy
import re
import shutil

from tools.build_live_profiles import R, read, sha, save, write, compile_ea

SOURCE = R / 'Packages/FTMO'
TARGET = R / 'Packages/PropReady'
SLUGS = frozenset((
    'nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum',
    'us100-month-end-flow', 'xau-rsi-vwap', 'us100-h1-orb-13utc',
    'us100-orb-new-york-m30', 'us100-selective-orb-v3',
    'xau-orb-new-york-m30', 'xau-orb-london-ny-overlap-m30',
))


def main():
    import json
    manifest = json.loads(read(SOURCE / 'PACKAGE.json'))
    source_hashes = {p: sha(p) for p in SOURCE.rglob('*') if p.is_file()}
    for name, digest in manifest['files'].items():
        assert sha(SOURCE / 'package' / name) == digest, name
    assert sha(SOURCE / 'CalyxFTMOGuard.mqh') == manifest['guard_sha']
    entries = copy.deepcopy([e for e in manifest['entries'] if e['slug'] in SLUGS])
    assert len(entries) == len(SLUGS) == 9
    package = TARGET / 'package'
    package.mkdir(parents=True, exist_ok=True)
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
            # CTrade checks filling before our OrderSend admission shim. Some
            # brokers allow IOC but not its default FOK; adapt management too.
            pattern = r'(bool CTrade::FillingCheck\(const string symbol\)\s*\{)'
            # PositionClose may call FillingCheck before assigning request.action.
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
        values.update(FTMOExpectedLogin='0', FTMOExpectedServer='', FTMOExpectedSymbol='',
                      FTMOExpectedCurrency='', FTMOReferenceBalance='0', FTMOStartUtcTime='0',
                      FTMOPhase='3')
        write(package / entry['settings'], '\n'.join(k+'='+str(v) for k, v in values.items())+'\n')
        entry['expert_sha'] = sha(package / entry['expert'])
        entry['settings_sha'] = sha(package / entry['settings'])
    new_manifest = dict(
        version='PROP-READY9-BROKER-NEUTRAL-20261030', entries=entries,
        news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True,
        reference_mode='PERSISTED_FIRST_INSTALL_BALANCE', default_phase='Funded',
        risk_cap_fraction=.005, risk_cap_input='FTMORiskCapPercent (installer = chosen risk, max 2%; 0.005 is the default)', guard_sha=sha(TARGET / 'CalyxFTMOGuard.mqh'),
        source_version=manifest['version'], source_guard_sha=manifest['guard_sha'],
        files={str(p.relative_to(package)).replace('\\', '/'): sha(p)
               for p in package.rglob('*') if p.is_file() and p.suffix != '.log'},
    )
    save(TARGET / 'PACKAGE.json', new_manifest)
    assert all(sha(p) == digest for p, digest in source_hashes.items())
    print('Built nine broker-neutral guarded EAs; original FTMO files unchanged. No MT5 account accessed.')


if __name__ == '__main__':
    main()
