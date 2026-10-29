"""Rebuild bots.json (magic number -> bot name) from the Calyx repository (owner 2026-10-29).

Sources, first match wins:
  1. the EA store catalog SETs via _Ops Monitor/common.magic_map() (product labels);
  2. the client Top 5 build manifest (dedicated magics 93095001-93095005);
  3. every .set file under _00 Live profiles (name = the SET file name) for magics the catalog does not know.
Hand edits survive: an existing entry with a "short" name keeps it. Run: python build_bots.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AAA = HERE.parent
PKG = AAA / 'BM Trading Robust Sets 2026-08-04'
TOP5 = AAA.parent / 'clients' / '_owner' / 'top5' / 'build' / 'manifest.json'
MAGIC = re.compile(r'(?im)^(?:Inp)?Magic(?:Number|Base)?\s*=\s*(\d+)')
SHORT = {'nasdaq-5m-candle-momentum': 'nasdaq 5m', 'xau-rsi-vwap': 'gold RSI VWAP', 'gold-overnight-value-area': 'gold overnight',
         '3-way-gold': '3 way gold', 'ema3': 'EMA3', 'dmc-current-xau': 'DMC gold', 'dmc-fresh-reaction-us100': 'DMC US100',
         'dmc-fresh-reaction-xau': 'DMC fresh gold', 'orb-volume-profile': 'ORB volume profile', 'orb-volume-profile-volume-confirmed': 'ORB VP confirmed',
         'xau-orb-london-ny-overlap-m30': 'gold ORB London-NY', 'xau-orb-new-york-m30': 'gold ORB NY', 'us100-orb-new-york-m30': 'US100 ORB NY',
         'us100-h1-orb-13utc': 'US100 ORB H1', 'us100-selective-orb-v3': 'US100 ORB V3', 'usdjpy-london-open-momentum': 'USDJPY London',
         'nasdaq-overnight': 'nasdaq overnight', 'xau-squeeze-momentum-standard': 'gold squeeze', 'news-pulse-xau': 'news gold',
         'news-pulse-xag': 'news silver', 'news-pulse-btc': 'news BTC', 'news-pulse-eurusd': 'news EURUSD', 'gold-news-v9-direction': 'gold news V9'}


def main():
    out_path = HERE / 'bots.json'
    old = json.loads(out_path.read_text(encoding='utf-8')).get('bots', {}) if out_path.is_file() else {}
    bots = {}
    sys.path.insert(0, str(PKG / '_Ops Monitor'))
    try:
        import common
        labels = {slug: p.label for slug, p in common.products().items()}
        for m, slug in common.magic_map().items():
            bots[str(m)] = dict(name=labels.get(slug, slug), slug=slug, short=SHORT.get(slug, ''), source='catalog')
    except Exception as e:                                                   # the forwarder works without the repo: keep the shipped file
        print(f'catalog not available ({e!r}); using SET scan only')
    if TOP5.is_file():
        for e in json.loads(TOP5.read_text(encoding='utf-8'))['entries']:
            m = str(e.get('inputs', {}).get('InpMagic', ''))
            if m.isdigit():
                bots.setdefault(m, dict(name=f"{e['label']} (Top 5)", slug=e['slug'], short=SHORT.get(e['slug'], ''), source='client top5'))
    for st in (PKG / '_00 Live profiles').rglob('*.set'):
        for m in MAGIC.findall(st.read_text(encoding='utf-8-sig', errors='ignore')):
            name = re.sub(r'^\d+\s*', '', st.stem); name = re.sub(r'\s*-\s*(RAW|SAFE|STANDARD|\d+PCT|ORB05.*)$', '', name, flags=re.I)
            bots.setdefault(m, dict(name=name, short='', source=f'SET {st.parent.name}'))
    for k, v in old.items():                                                 # keep hand-edited short names
        if isinstance(v, dict) and v.get('short') and k in bots: bots[k]['short'] = v['short']
        elif k not in bots: bots[k] = v
    bots.setdefault('0', dict(name='manual', short='manual', source='MT5 manual trades'))
    out = dict(note='magic -> bot name shown in the signals; "short" wins over "name" when set. Edit freely; build_bots.py keeps short names.',
               bots=dict(sorted(bots.items(), key=lambda kv: int(kv[0]))))
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'{len(bots)} bots -> {out_path}')


if __name__ == '__main__':
    main()
