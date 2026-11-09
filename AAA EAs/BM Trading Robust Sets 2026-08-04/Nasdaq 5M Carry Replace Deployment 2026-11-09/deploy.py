"""Owner 2026-11-09: "update it in all portfolio bats (keep the DI filter on or off input when presented)". Nasdaq 5M gets InpCarryMode, default
2 = REPLACE: when the previous trade is still open at the 09:35 New York check and today's signal passes, the old trade is closed and today's signal is
taken (Nasdaq 5M Carry Fix 2026-11-09). The code is the exact patch tested there; only the default changes from 0 to 2. Nothing else changes: same stop
choice (ATR6 / 0.60%), DI question, risk, SETs and installers (the SETs carry no InpCarryMode, so every build uses the default).
Stages (run from AAA EAs/EA store with uv run python "<this>" <stage>):
  prepare   new production source + EX5 in this folder (the old EX5 fe9f391db5af stays where it is, as evidence)
  patch     every package copy of the Nasdaq source (backups in before/)
  compile   every wrapper that includes a patched copy (MetaEditor only, no terminal) -> sha-map.json (old -> new)
  finish    copies (EAs/, Experts/, profile folders), manifests and hashes, canonical installer path
Ava, clients/top 5 and research folders are not touched."""
import hashlib, json, re, shutil, subprocess, sys, time
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent; LIVE = B / '_00 Live profiles'; C14 = B / 'Current14 Plus ORB05 Portfolio 2026-10-08'
OLD = B / 'Nasdaq 5M DI ATR Deployment 2026-09-28/EA'; NEW = H / 'EA'; NEW_SRC = NEW / 'Nasdaq 5M DI Wide ATR EA.mq5'
EDITOR = B / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'; SHAMAP = H / 'sha-map.json'; BAK = H / 'before'
PACKAGE_DIRS = [C14 / 'Sources', LIVE / 'Packages/Edge10/Sources', LIVE / 'Packages/PropReady/package', LIVE / 'Packages/FTMO-AnyBroker/package', LIVE / 'Packages/FTMO/package',
                LIVE / 'Packages/FundedV1/package', LIVE / 'Packages/Turbo5/package', LIVE / 'Best Prop Portfolio 2026-10-20/package', LIVE / 'Best Prop 15 Portfolio 2026-10-29/package',
                LIVE / 'ftmo 1_step/package', LIVE / 'Core 9/1-Step/package', LIVE / 'Core 9/2-Step/package']
BUILD_SOURCES = [B / 'FTMO Thirteen EA Deployment 2026-09-27/package']   # the FTMO package build copies its sources from here: patched, not compiled
MARK = 'InpCarryMode='


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    raw = Path(p).read_bytes(); return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')


def sub1(text, old, new):
    assert text.count(old) == 1, (old[:90], text.count(old)); return text.replace(old, new)


def carry_patch(s):
    """The Nasdaq 5M Carry Fix 2026-11-09 research patch (carry.py build_ea), default mode 2."""
    s = sub1(s, 'input group "Risk and execution"\n', '''input group "Carry (2026-11-09: REPLACE by default)"
input int    InpCarryMode=2;               // previous trade still open at the signal check: 0 skip the day, 1 late entry after it closes, 2 close it and take today's signal (default), 3 replace only if opposite
input int    InpLateCutoffMinuteNY=930;    // mode 1 only: no late entry after this New York minute (15:30)

input group "Risk and execution"
''')
    s = sub1(s, 'void ProcessNewBar()\n  {\n', '''int g_pending_dir=0,g_pending_key=0;

bool TryLateEntry(const MqlRates &bar)
  {
   if(g_pending_dir==0) return false;
   MqlDateTime ny; TimeToStruct(ServerToNewYork(bar.time),ny);
   int key=ny.year*10000+ny.mon*100+ny.day,close_minute=ny.hour*60+ny.min+PeriodSeconds(InpSignalTimeframe)/60;
   if(key!=g_pending_key || close_minute>InpLateCutoffMinuteNY || AlreadyTradedOnNewYorkDate(g_pending_key)) { g_pending_dir=0; return false; }
   ulong ticket=0;
   if(SelectOurPosition(ticket) || !InpEnableTrading) return false;
   double ema=0.0,atr=0.0;
   if(!ReadIndicatorValue(g_ema_handle,1,ema) || !ReadIndicatorValue(g_atr_handle,1,atr)) return false;
   if((g_pending_dir>0 && bar.close<=ema) || (g_pending_dir<0 && bar.close>=ema)) return false;   // the signal side must still hold: wait
   int direction=g_pending_dir; g_pending_dir=0;
   SendEntry(direction,atr,bar,SelectedRewardRisk(bar,atr));
   return true;
  }

void ProcessNewBar()
  {
''')
    s = sub1(s, '''   if(!IsNewYorkTime(rates[1].time,InpSignalHourNY,InpSignalMinuteNY)) return;
   int date_key=NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   if(SelectOurPosition(ticket) || AlreadyTradedOnNewYorkDate(date_key) || !InpEnableTrading) return;
''', '''   if(InpCarryMode==1 && TryLateEntry(rates[1])) return;
   if(!IsNewYorkTime(rates[1].time,InpSignalHourNY,InpSignalMinuteNY)) return;
   int date_key=NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   bool held=SelectOurPosition(ticket);
   if((held && InpCarryMode==0) || AlreadyTradedOnNewYorkDate(date_key) || !InpEnableTrading) return;
   int held_direction=(held ? (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1) : 0);
''')
    return sub1(s, '''   if(!DIAgrees(direction)) return;
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }''', '''   if(!DIAgrees(direction)) return;
   if(held)
     {
      if(InpCarryMode==1) { g_pending_dir=direction; g_pending_key=date_key; return; }
      if(InpCarryMode==3 && held_direction==direction) return;
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints)) { Print("N5EMA carry close failed: ",g_trade.ResultRetcodeDescription()); return; }
      if(SelectOurPosition(ticket)) return;
     }
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }''')


def write_like(p, text, raw_old):
    crlf = b'\r\n' in raw_old; bom = raw_old.startswith(b'\xef\xbb\xbf'); out = text.replace('\n', '\r\n') if crlf else text
    Path(p).write_bytes((b'\xef\xbb\xbf' if bom else b'') + out.encode('utf-8'))


def backup(p):
    dest = BAK / Path(p).relative_to(B)
    if not dest.exists(): dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)


def compile_ea(path):
    log = path.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    t = read(log); assert '0 errors, 0 warnings' in t, t[-2500:]
    ex5 = path.with_suffix('.ex5'); assert ex5.is_file() and ex5.stat().st_mtime >= started - 2, path; print('COMPILED', path.name, flush=True)


def nasdaq_sources(folder):
    return [p for p in Path(folder).glob('*.mq*') if p.suffix in ('.mqh', '.mq5') and 'N5EMA long' in read(p) and 'input group "Signal"' in read(p)]


def includes(folder, name, seen=None):
    seen = set() if seen is None else seen
    if name in seen or not (Path(folder) / name).is_file(): return seen
    seen.add(name)
    for inc in re.findall(r'#include\s+"([^"]+)"', read(Path(folder) / name)): includes(folder, inc, seen)
    return seen


def prepare():
    NEW.mkdir(parents=True, exist_ok=True)
    for n in ('SafeRegimeFilter.mqh', 'DynamicTrailingSessionFilter.mqh'): shutil.copy2(OLD / n, NEW / n)
    raw = (OLD / 'Nasdaq 5M DI Wide ATR EA.mq5').read_bytes(); write_like(NEW_SRC, carry_patch(read(OLD / 'Nasdaq 5M DI Wide ATR EA.mq5').replace('\r\n', '\n')), raw)
    compile_ea(NEW_SRC); print('production', sha(NEW_SRC.with_suffix('.ex5'))[:12], 'old', sha(OLD / 'Nasdaq 5M DI Wide ATR EA.ex5')[:12])


def patch():
    for folder in PACKAGE_DIRS + BUILD_SOURCES:
        for p in nasdaq_sources(folder):
            text = read(p).replace('\r\n', '\n')
            if MARK in text: print('already', p.relative_to(B)); continue
            raw = p.read_bytes(); backup(p); write_like(p, carry_patch(text), raw); print('patched', p.relative_to(B))


def compile_all():
    m = json.loads(SHAMAP.read_text()) if SHAMAP.exists() else {}
    m.setdefault(sha(OLD / 'Nasdaq 5M DI Wide ATR EA.ex5'), dict(new=sha(NEW_SRC.with_suffix('.ex5')), file=str(NEW_SRC.with_suffix('.ex5'))))
    for folder in PACKAGE_DIRS:
        targets = {p.name for p in nasdaq_sources(folder)}; assert targets, folder
        for src in targets:                                                   # the patched source files themselves (manifests hash them)
            old = sha(BAK / (Path(folder) / src).relative_to(B)); m[old] = dict(new=sha(Path(folder) / src), file=str(Path(folder) / src))
        for w in sorted(Path(folder).glob('*.mq5')):
            if not (includes(folder, w.name) & targets): continue
            ex5 = w.with_suffix('.ex5'); old = sha(ex5) if ex5.exists() else None
            if old and any(v.get('file') == str(ex5) for v in m.values()): print('skip (done)', w.name); continue
            if old: backup(ex5)
            compile_ea(w); m[old or ('new:' + str(ex5))] = dict(new=sha(ex5), file=str(ex5)); SHAMAP.write_text(json.dumps(m, indent=1))
    SHAMAP.write_text(json.dumps(m, indent=1)); print('compiled; map', len(m))


def finish():
    m = json.loads(SHAMAP.read_text()); files = {old: Path(v['file']) for old, v in m.items() if not old.startswith('new:')}
    roots = [LIVE, C14]; skip = ('superseded', 'before', 'INVALID')
    # 1. every binary copy of an old EX5 (EAs/, Experts/, profile folders, Mixed 22 / Core 9 copies) becomes the new build
    n = 0
    for root in roots:
        for f in [p for p in root.rglob('*.ex5') if not any(s in str(p) for s in skip)]:
            old = sha(f)
            if old in files and f.resolve() != files[old].resolve():
                backup(f); shutil.copy2(files[old], f); n += 1
    print('binary copies replaced', n)
    # Current 14 package: Experts/ holds the compiled Sources/ wrapper
    for w in (C14 / 'Sources').glob('*.ex5'):
        e = C14 / 'Experts' / w.name
        if e.exists() and sha(e) != sha(w): backup(e); shutil.copy2(w, e); print('Current14 Experts copy', w.name)
    for w in (LIVE / 'Packages/Edge10/Sources').glob('*.ex5'):
        e = LIVE / 'Packages/Edge10/Experts' / w.name
        if e.exists() and sha(e) != sha(w): backup(e); shutil.copy2(w, e); print('Edge10 Experts copy', w.name)
    # 2. hashes in manifests / readmes / checksums
    rep = {old: v['new'] for old, v in m.items() if not old.startswith('new:')}
    for root in roots:
        for f in [p for p in root.rglob('*') if p.is_file() and p.suffix in ('.json', '.md', '.txt') and not any(s in str(p) for s in skip)]:
            raw = f.read_bytes()
            try: t = raw.decode('utf-8')
            except UnicodeDecodeError: continue
            k = 0
            for old, new in rep.items():
                if old in t: k += t.count(old); t = t.replace(old, new)
            for old, new in ((f'{o[:12]}', f'{n_[:12]}') for o, n_ in rep.items()):
                pass
            if k: backup(f); f.write_bytes(t.encode('utf-8')); print('rehashed', f.relative_to(B), k)
    # 3. the canonical installer (Full EA / Reviewed / Dynamic) loads the new production EX5
    inst = B / '_Auto Deploy/Install-BMTradingPortfolio.ps1'; t = inst.read_text(encoding='utf-8-sig'); old_path = 'Nasdaq 5M DI ATR Deployment 2026-09-28\\EA\\Nasdaq 5M DI Wide ATR EA.ex5'
    if old_path in t:
        assert t.count(old_path) == 2; raw = inst.read_bytes(); backup(inst)
        write_like(inst, t.replace('\r\n', '\n').replace(old_path, 'Nasdaq 5M Carry Replace Deployment 2026-11-09\\EA\\Nasdaq 5M DI Wide ATR EA.ex5'), raw); print('installer path updated')
    # 4. every package manifest matches the disk again
    for d in ('Packages/PropReady', 'Packages/FTMO-AnyBroker', 'Packages/FTMO', 'Best Prop Portfolio 2026-10-20', 'Best Prop 15 Portfolio 2026-10-29', 'ftmo 1_step', 'Core 9/1-Step', 'Core 9/2-Step', 'Packages/FundedV1', 'Packages/Turbo5'):
        man = json.loads((LIVE / d / 'PACKAGE.json').read_text(encoding='utf-8-sig')); bad = []
        for fn, digest in (man.get('files') or {}).items():
            p = LIVE / d / 'package' / fn
            if p.exists() and sha(p) != digest: bad.append(fn)
        for e in man.get('entries', []):
            ex = e.get('expert'); p = LIVE / d / 'package' / ex if ex else None
            if p and p.exists() and e.get('expert_sha') and sha(p) != e['expert_sha']: bad.append(ex)
        print('manifest', d, 'OK' if not bad else ('MISMATCH ' + str(bad)))
    for d in (LIVE / 'Packages/Edge10', LIVE / 'Packages/Mixed22', LIVE / 'Packages/Core9', C14):
        ck = json.loads((d / 'Checksums.json').read_text(encoding='utf-8-sig')); bad = [k for k, v in ck.items() if (d / k).exists() and sha(d / k) != v]
        print('checksums', d.name, 'OK' if not bad else ('MISMATCH ' + str(bad[:5])))


if __name__ == '__main__':
    {'prepare': prepare, 'patch': patch, 'compile': compile_all, 'finish': finish}[sys.argv[1]]()
