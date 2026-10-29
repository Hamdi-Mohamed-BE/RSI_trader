"""Build the Turbo-guarded 5-EA package (owner 2026-10-27: Nasdaq 5M DI OFF, XAU RSI VWAP, Gold Overnight Value Area, 3 Way Gold, EMA3).
Sources/presets = exactly what the Full EA BAT installs (`_00 Live profiles/Full EA portfolio - Recommended Adaptive/PORTFOLIO.json`).
Transform = the FTMO / Prop Ready build pattern (tools/build_live_profiles.py::ftmo_package): <Trade/Trade.mqh> -> Turbo_Trade.mqh (CTrade
routed through TurboOrderSend), every OrderSend( -> TurboOrderSend(, OnInit/OnTick/OnTimer wrapped by TurboInit/TurboPulse.
MetaEditor of the isolated tester only; no MT5 terminal or account is touched.
python build_turbo5.py
"""
import hashlib, json, re, shutil, subprocess, time
from pathlib import Path

S = Path(__file__).resolve().parent; B = S.parent; LIVE = B / '_00 Live profiles'
TESTER = B / '_Backtests/MT5-DMC-20260811'; EDITOR = TESTER / 'MetaEditor64.exe'
TARGET = LIVE / 'Packages/Turbo5'; PKG = TARGET / 'package'
FULL = json.loads((LIVE / 'Full EA portfolio - Recommended Adaptive/PORTFOLIO.json').read_text(encoding='utf-8'))
VERSION = 'TURBO5-GUARDED-20261027-v2'
ROSTER = {'Nasdaq 5M Candle Momentum': 'nasdaq-5m-candle-momentum', 'XAU RSI VWAP': 'xau-rsi-vwap', 'Gold Overnight Value Area': 'gold-overnight-value-area',
          '3 Way Gold': '3-way-gold', 'AAA Final EMA3': 'ema3'}
RISK = '0.75'          # EA request; the guard cuts every entry to min(0.75% of size, 5% of trailing room, all limits), lots rounded DOWN
GUARD_INPUTS = dict(TurboGuardMode='1', TurboAccountSize='50000', TurboExpectedLogin='0', TurboExpectedServer='', TurboExpectedSymbol='', TurboExpectedCurrency='',
                    TurboReferenceBalance='0', TurboStartUtcTime='0', TurboKnownFloor='0', TurboRebaseOnWithdrawal='true', TurboTrailEquity='false', TurboTesterRewards='false')


def read(p):
    raw = p.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, t): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t, encoding='utf-8')


def compile_ea(path):
    log = path.with_suffix('.compile.log'); began = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    body = read(log); m = re.search(r'Result: (\d+) errors?, (\d+) warnings?', body)
    assert m and m.group(1) == '0', body[-4000:]
    assert path.with_suffix('.ex5').is_file() and path.with_suffix('.ex5').stat().st_mtime >= began - 2
    return int(m.group(2))


def trade_shim():
    t = read(TESTER / 'MQL5/Include/Trade/Trade.mqh')
    for n in ('OrderInfo', 'HistoryOrderInfo', 'PositionInfo', 'DealInfo'):
        assert t.count(f'#include "{n}.mqh"') == 1; t = t.replace(f'#include "{n}.mqh"', f'#include <Trade/{n}.mqh>')
    assert t.count('res=::OrderSendAsync(request,result);') == 1 and t.count('res=::OrderSend(request,result);') == 1
    t = t.replace('res=::OrderSendAsync(request,result);', 'res=TurboOrderSend(request,result);').replace('res=::OrderSend(request,result);', 'res=TurboOrderSend(request,result);')
    t, n = re.subn(r'(bool CTrade::FillingCheck\(const string symbol\)\s*\{)',
                   r'\1\n   ENUM_ORDER_TYPE_FILLING mode=m_type_filling;\n   if(!TurboMarketFilling(symbol,mode))return false;\n   m_type_filling=mode;\n', t)
    assert n == 1
    return '#include "CalyxTurboGuard.mqh"\n' + t


def main():
    assert not PKG.exists(), f'{PKG} exists; this builder only creates a fresh package'
    members = [m for m in FULL['builds'][0]['members'] if m['label'] in ROSTER]
    assert len(members) == 5, [m['label'] for m in members]
    PKG.mkdir(parents=True)
    shutil.copy2(S / 'guard/CalyxTurboGuard.mqh', TARGET / 'CalyxTurboGuard.mqh'); shutil.copy2(S / 'guard/CalyxTurboGuard.mqh', PKG / 'CalyxTurboGuard.mqh')
    write(PKG / 'Turbo_Trade.mqh', trade_shim())
    cache = {}

    def graph(path):
        path = path.resolve()
        if path in cache: return cache[path]
        name = 'src_' + hashlib.sha256(str(path.relative_to(B)).encode()).hexdigest()[:12] + '.mqh'; cache[path] = name
        text = read(path).replace('#include <Trade/Trade.mqh>', '#include "Turbo_Trade.mqh"')
        text = re.sub(r'\bOrderSend\(', 'TurboOrderSend(', text)
        text = re.sub(r'#include\s+"([^"]+)"', lambda m: '#include "Turbo_Trade.mqh"' if m[1] == 'Turbo_Trade.mqh'
                      else '#include "' + graph(path.parent / m[1].replace('\\', '/')) + '"', text)
        write(PKG / name, text); return name

    def expansion(n, seen):
        if n in seen: return ''
        seen.add(n); body = read(PKG / n)
        return body + '\n'.join(expansion(v, seen) for v in re.findall(r'#include "(src_[^"]+)"', body))

    entries = []; built = {}
    for m in members:
        src = B / m['source_expert'].replace('\\', '/'); assert sha(src) == m['expert_sha256'], m['label']
        mq5 = src.with_suffix('.mq5'); stem = 'Turbo - ' + mq5.stem
        if stem not in built:
            include = graph(mq5)
            code = ('#property strict\n#include "CalyxTurboGuard.mqh"\n#define OnInit TURBO_StrategyInit\n#define OnTick TURBO_StrategyTick\n#define OnTimer TURBO_StrategyTimer\n'
                    f'#include "{include}"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
                    'int OnInit(){if(TurboInit()!=INIT_SUCCEEDED)return INIT_FAILED;return TURBO_StrategyInit();}\nvoid OnTick(){if(TurboPulse())TURBO_StrategyTick();}\n')
            if re.search(r'void\s+OnTimer\s*\(', expansion(include, set())): code += 'void OnTimer(){if(TurboPulse())TURBO_StrategyTimer();}\n'
            write(PKG / (stem + '.mq5'), code); built[stem] = compile_ea(PKG / (stem + '.mq5'))
        preset = LIVE / 'Full EA portfolio - Recommended Adaptive' / m['settings']; assert sha(preset) == m['settings_sha256'], m['label']
        inputs = {}
        for line in read(preset).splitlines():
            if '=' in line and not line.startswith(';'): k, v = line.split('=', 1); inputs[k.strip()] = v.strip()
        assert 'InpRiskPercent' in inputs, m['label']
        inputs['InpRiskPercent'] = RISK; inputs['InpAdaptivePortfolioControls'] = 'false'
        if 'InpRiskMode' in inputs: inputs['InpRiskMode'] = '0'
        if ROSTER[m['label']] == 'nasdaq-5m-candle-momentum': inputs['InpRequireDIAgreement'] = 'false'
        inputs.update(GUARD_INPUTS)
        setname = stem.replace('Turbo - ', 'Turbo - ') + ('' if list(ROSTER).count(m['label']) else '') + '.set'
        write(PKG / setname, '\n'.join(f'{k}={v}' for k, v in inputs.items()) + '\n')
        entries.append(dict(slug=ROSTER[m['label']], label=m['label'], symbol=m['symbol'], timeframe=m['timeframe'], expert=stem + '.ex5', settings=setname,
                            source_expert=m['source_expert'], source_expert_sha256=m['expert_sha256'], source_settings=m['source_settings'], source_settings_sha256=m['settings_sha256'],
                            expert_sha256=sha(PKG / (stem + '.ex5')), settings_sha256=sha(PKG / setname), compile_warnings=built[stem]))
        print('BUILT', m['label'], stem, 'warnings', built[stem], flush=True)
    manifest = dict(version=VERSION, purpose='Owner 2026-10-27: 5 EAs with the Turbo $50k reward-account guard (Turbo 50k Funded Portfolio 2026-10-26 improved 0.75 profile).',
                    entries=entries, ea_risk_request_percent=float(RISK), news_enabled=False, hedging_required=True, currency_mode='ACCOUNT_CURRENCY',
                    guard_sha=sha(TARGET / 'CalyxTurboGuard.mqh'), guard_source='Turbo Guard Build 2026-10-26/guard/CalyxTurboGuard.mqh',
                    files={str(p.relative_to(PKG)).replace('\\', '/'): sha(p) for p in PKG.rglob('*') if p.is_file() and p.suffix != '.log'})
    write(TARGET / 'PACKAGE.json', json.dumps(manifest, indent=2) + '\n')
    print('Package', TARGET, len(entries), 'entries. No MT5 terminal or account accessed.')


if __name__ == '__main__':
    main()
