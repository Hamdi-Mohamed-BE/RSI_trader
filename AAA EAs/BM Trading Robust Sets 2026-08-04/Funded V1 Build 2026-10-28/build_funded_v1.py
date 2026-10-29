"""Build the funded_v1 package (owner 2026-10-28): 8 EAs with the configurable funded guard (guard/CalyxFundedGuard.mqh).
Sources / presets = what the Full EA BAT installs (`_00 Live profiles/Full EA portfolio - Recommended Adaptive/PORTFOLIO.json`), except the
two ORBs at 0.5R: XAU ORB London NY Overlap M30 uses the ORB05 preset (= its standalone preset with InpRewardRisk 0.5), and ORB Volume Profile
Volume Confirmed uses its Full EA preset with InpRewardRisk 0.5. Transform = the Turbo5 / Prop Ready pattern (CTrade + OrderSend routed through
FundedOrderSend; OnInit/OnTick/OnTimer wrapped). Settings are UNARMED; the installer writes the account binding, risk and guard choices.
MetaEditor of the isolated tester only; no MT5 terminal or account is touched.
python build_funded_v1.py
"""
import hashlib, json, re, shutil, subprocess, time
from pathlib import Path

S = Path(__file__).resolve().parent; B = S.parent; LIVE = B / '_00 Live profiles'
TESTER = B / '_Backtests/MT5-DMC-20260811'; EDITOR = TESTER / 'MetaEditor64.exe'
TARGET = LIVE / 'Packages/FundedV1'; PKG = TARGET / 'package'
FULLDIR = LIVE / 'Full EA portfolio - Recommended Adaptive'
FULL = json.loads((FULLDIR / 'PORTFOLIO.json').read_text(encoding='utf-8'))
VERSION = 'FUNDED-V1-20261028-9EA'
ROSTER = [('nasdaq-5m-candle-momentum', 'Nasdaq 5M Candle Momentum', None, {}),
          ('ema3', 'AAA Final EMA3', None, {}),
          ('3-way-gold', '3 Way Gold', None, {}),
          ('orb-volume-profile-volume-confirmed', 'ORB Volume Profile Volume Confirmed', None, {'InpRewardRisk': '0.5'}),
          ('xau-orb-london-ny-overlap-m30', 'XAU ORB London NY Overlap M30', LIVE / 'ORB05 Sets/xau-orb-london-ny-overlap-m30.set', {}),
          ('dmc-fresh-reaction-us100', 'DMC Fresh Reaction US100', None, {}),
          ('dmc-current-xau', 'DMC Current XAU', None, {}),
          ('xau-rsi-vwap', 'XAU RSI VWAP', None, {}),
          ('gold-overnight-value-area', 'Gold Overnight Value Area', None, {})]   # owner 2026-10-28: added as the 9th EA
EA_RISK = '0.75'      # EA request (installer: 1.5 x the guard risk); the guard cuts every entry to its own budget, lots rounded DOWN
GUARD_DEFAULTS = dict(FundedGuardMode='1', FundedAccountSize='50000', FundedRiskPercent='0.5', FundedRoomTaperPercent='5', FundedMaxOpenRiskPercent='2',
                      FundedMaxSymbolRiskPercent='1.5', FundedMaxDailyLossPercent='2', FundedMaxDailyWinPercent='0.75', FundedMaxLossPercent='6',
                      FundedTrailMode='0', FundedLockAtInitial='true', FundedBufferPercent='0.25', FundedFirmDailyPercent='3', FundedDayResetUtcHour='0',
                      FundedDailyBasis='1', FundedNewsBlackoutMinutes='5', FundedNewsCancelPending='false', FundedMinRiskPercent='0.05',
                      FundedExpectedLogin='0', FundedExpectedServer='', FundedExpectedSymbol='', FundedExpectedCurrency='',
                      FundedReferenceBalance='0', FundedStartUtcTime='0', FundedKnownFloor='0')


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
    t = t.replace('res=::OrderSendAsync(request,result);', 'res=FundedOrderSend(request,result);').replace('res=::OrderSend(request,result);', 'res=FundedOrderSend(request,result);')
    t, n = re.subn(r'(bool CTrade::FillingCheck\(const string symbol\)\s*\{)',
                   r'\1\n   ENUM_ORDER_TYPE_FILLING mode=m_type_filling;\n   if(!FundedMarketFilling(symbol,mode))return false;\n   m_type_filling=mode;\n', t)
    assert n == 1
    return '#include "CalyxFundedGuard.mqh"\n' + t


def read_set(p):
    out = {}
    for line in read(p).splitlines():
        if '=' in line and not line.startswith(';'): k, v = line.split('=', 1); out[k.strip()] = v.strip().split('||')[0]   # optimizer fields -> current value
    return out


def main():
    assert not PKG.exists(), f'{PKG} exists; this builder only creates a fresh package'
    members = {m['label']: m for m in FULL['builds'][0]['members']}
    PKG.mkdir(parents=True)
    for d in (TARGET, PKG): shutil.copy2(S / 'guard/CalyxFundedGuard.mqh', d / 'CalyxFundedGuard.mqh')
    write(PKG / 'Funded_Trade.mqh', trade_shim())
    cache = {}

    def graph(path):
        path = path.resolve()
        if path in cache: return cache[path]
        name = 'src_' + hashlib.sha256(str(path.relative_to(B)).encode()).hexdigest()[:12] + '.mqh'; cache[path] = name
        text = read(path).replace('#include <Trade/Trade.mqh>', '#include "Funded_Trade.mqh"')
        text = re.sub(r'\bOrderSend\(', 'FundedOrderSend(', text)
        text = re.sub(r'#include\s+"([^"]+)"', lambda m: '#include "Funded_Trade.mqh"' if m[1] == 'Funded_Trade.mqh'
                      else '#include "' + graph(path.parent / m[1].replace('\\', '/')) + '"', text)
        write(PKG / name, text); return name

    def expansion(n, seen):
        if n in seen: return ''
        seen.add(n); body = read(PKG / n)
        return body + '\n'.join(expansion(v, seen) for v in re.findall(r'#include "(src_[^"]+)"', body))

    entries, built = [], {}
    for slug, label, preset, overrides in ROSTER:
        m = members[label]
        src = B / m['source_expert'].replace('\\', '/'); assert sha(src) == m['expert_sha256'], label
        mq5 = src.with_suffix('.mq5'); stem = 'Funded - ' + mq5.stem
        if stem not in built:
            include = graph(mq5)
            code = ('#property strict\n#include "CalyxFundedGuard.mqh"\n#define OnInit FUNDED_StrategyInit\n#define OnTick FUNDED_StrategyTick\n#define OnTimer FUNDED_StrategyTimer\n'
                    f'#include "{include}"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
                    'int OnInit(){if(FundedInit()!=INIT_SUCCEEDED)return INIT_FAILED;return FUNDED_StrategyInit();}\nvoid OnTick(){if(FundedPulse())FUNDED_StrategyTick();}\n')
            if re.search(r'void\s+OnTimer\s*\(', expansion(include, set())): code += 'void OnTimer(){if(FundedPulse())FUNDED_StrategyTimer();}\n'
            write(PKG / (stem + '.mq5'), code); built[stem] = compile_ea(PKG / (stem + '.mq5'))
        full_preset = FULLDIR / m['settings']; assert sha(full_preset) == m['settings_sha256'], label
        source_preset = preset or full_preset
        inputs = read_set(source_preset); inputs.update(overrides)
        assert 'InpRiskPercent' in inputs, label
        inputs['InpRiskPercent'] = EA_RISK; inputs['InpAdaptivePortfolioControls'] = 'false'
        if 'InpRiskMode' in inputs: inputs['InpRiskMode'] = '0'
        if slug == 'nasdaq-5m-candle-momentum': inputs['InpRequireDIAgreement'] = 'true'      # installer asks ON / OFF
        inputs.update(GUARD_DEFAULTS)
        setname = f'Funded - {label}.set'
        write(PKG / setname, '\n'.join(f'{k}={v}' for k, v in inputs.items()) + '\n')
        entries.append(dict(slug=slug, label=label, symbol=m['symbol'], timeframe=m['timeframe'], expert=stem + '.ex5', settings=setname,
                            source_expert=m['source_expert'], source_expert_sha256=m['expert_sha256'],
                            source_settings=str(source_preset.relative_to(B)).replace('\\', '/'), source_settings_sha256=sha(source_preset), overrides=overrides,
                            di_prompt=slug == 'nasdaq-5m-candle-momentum', expert_sha256=sha(PKG / (stem + '.ex5')), settings_sha256=sha(PKG / setname),
                            compile_warnings=built[stem]))
        print('BUILT', label, stem, 'warnings', built[stem], flush=True)
    manifest = dict(version=VERSION, name='funded_v1', purpose='Owner 2026-10-28: 9 EAs with the configurable funded guard (defaults = Leveraged $50k rules).',
                    entries=entries, ea_risk_request_percent=float(EA_RISK), guard_defaults=GUARD_DEFAULTS, news_eas=False, hedging_required=True,
                    currency_mode='ACCOUNT_CURRENCY', guard_sha=sha(TARGET / 'CalyxFundedGuard.mqh'), guard_source='Funded V1 Build 2026-10-28/guard/CalyxFundedGuard.mqh',
                    files={str(p.relative_to(PKG)).replace('\\', '/'): sha(p) for p in PKG.rglob('*') if p.is_file() and p.suffix != '.log'})
    write(TARGET / 'PACKAGE.json', json.dumps(manifest, indent=2) + '\n')
    print('Package', TARGET, len(entries), 'entries. No MT5 terminal or account accessed.')


if __name__ == '__main__':
    main()
