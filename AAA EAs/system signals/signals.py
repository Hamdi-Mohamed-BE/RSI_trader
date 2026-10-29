"""Calyx MT5 -> Telegram signal forwarder (owner request 2026-10-29).

Watches ONE MetaTrader 5 terminal (you pick it at start) and posts every trading event of its logged-in account to a Telegram channel:
new positions (entry / TP / SL / bot name), SL / TP updates, partial and full closes (exit, result, reason), pending orders (placed,
modified, filled, cancelled, expired). Updates and closes are posted as replies to the original signal message.

READ-ONLY: it only calls account_info / terminal_info / positions_get / orders_get / history_deals_get / history_orders_get /
symbol_info. It never sends, modifies or closes orders, and it REFUSES to start a terminal that is not already running (the MT5 Python
API would otherwise launch it). One watcher per account (file lock). Secrets live in .env (never committed).

  python signals.py --list                 list terminals (running / installed)
  python signals.py                        pick a running terminal interactively and start
  python signals.py --terminal 2           start on terminal #2 of the list (or pass the terminal64.exe path)
  python signals.py --dry-run              print the messages instead of sending them
  python signals.py --test-telegram        send one test message and exit
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_DIR = HERE / 'state'
LOG_DIR = HERE / 'logs'
VERSION = 'signals-1.2-20261029'

# MT5 enum values (the MetaTrader5 module exposes the same numbers; kept here so the logic is testable without a terminal)
DEAL_BUY, DEAL_SELL = 0, 1
ENTRY_IN, ENTRY_OUT, ENTRY_INOUT, ENTRY_OUT_BY = 0, 1, 2, 3
REASONS = {0: 'closed manually', 1: 'closed manually (mobile)', 2: 'closed manually (web)', 3: 'closed by bot', 4: 'stop loss hit',
           5: 'take profit hit', 6: 'stop out (margin)', 7: 'rollover', 8: 'variation margin', 9: 'split'}
ORDER_NAMES = {0: 'Buy', 1: 'Sell', 2: 'Buy Limit', 3: 'Sell Limit', 4: 'Buy Stop', 5: 'Sell Stop', 6: 'Buy Stop Limit', 7: 'Sell Stop Limit'}
PENDING_TYPES = (2, 3, 4, 5, 6, 7)
ORDER_STATE = {2: 'Cancelled', 4: 'Filled', 5: 'Rejected', 6: 'Expired'}
BALANCE_TYPES = {2: 'balance operation', 3: 'credit', 4: 'charge', 5: 'correction', 6: 'bonus', 7: 'commission', 18: 'interest'}
ASSETS = {'XAUUSD': 'GOLD', 'XAGUSD': 'SILVER', 'US100': 'NASDAQ', 'US30': 'DOW JONES', 'US500': 'S&P 500', 'BTCUSD': 'BITCOIN',
          'ETHUSD': 'ETHEREUM', 'USOIL': 'OIL', 'UKOIL': 'BRENT', 'DE40': 'DAX', 'UK100': 'FTSE 100', 'JP225': 'NIKKEI'}
RISK_NOTE = 'Risk management is required: use the minimum available lot size or risk max 5% per trade.'
DEFAULT_ALIASES = {'USTEC': 'US100', 'NAS100': 'US100', 'NDX100': 'US100', 'NQ100': 'US100', 'US100CASH': 'US100', 'US30CASH': 'US30',
                   'DJ30': 'US30', 'WS30': 'US30', 'DOW30': 'US30', 'US500': 'US500', 'SPX500': 'US500', 'GOLD': 'XAUUSD', 'SILVER': 'XAGUSD'}


# ----------------------------------------------------------------------------------------------------------------------- config
def load_env(path: Path) -> dict:
    env = {}
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1); env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k.startswith(('TELEGRAM_', 'SIGNALS_'))})
    return env


def flag(env, key, default):
    v = env.get(key)
    return default if v is None or v == '' else v.strip().lower() in ('1', 'true', 'yes', 'y', 'on')


class Config:
    def __init__(self, env: dict):
        self.token = env.get('TELEGRAM_BOT_TOKEN', '')
        self.chat = env.get('TELEGRAM_CHAT_ID', '')
        # user = post from your own Telegram account, logged in by QR code (needs api id / hash); bot = a @BotFather bot token
        self.mode = (env.get('TELEGRAM_MODE') or 'user').strip().lower()     # QR login unless TELEGRAM_MODE=bot
        self.api_id = env.get('TELEGRAM_API_ID', ''); self.api_hash = env.get('TELEGRAM_API_HASH', '')
        self.admin_chat = env.get('TELEGRAM_ADMIN_CHAT_ID', '')               # optional: connection / error alerts go here, not to the channel
        self.risk_note = env.get('SIGNALS_RISK_NOTE', RISK_NOTE).strip()      # shown on every new signal / pending order (empty = off)
        self.show_money = flag(env, 'SIGNALS_SHOW_PROFIT', False)            # $ results reveal the account size: off by default
        self.show_r = flag(env, 'SIGNALS_SHOW_R', True)
        self.show_pending = flag(env, 'SIGNALS_SHOW_PENDING', True)
        self.show_account = flag(env, 'SIGNALS_SHOW_ACCOUNT_EVENTS', False)  # deposits / withdrawals (no amounts unless SHOW_PROFIT)
        self.reply = flag(env, 'SIGNALS_REPLY_TO_SIGNAL', True)
        self.announce_open = flag(env, 'SIGNALS_ANNOUNCE_OPEN_ON_START', False)
        self.poll = float(env.get('SIGNALS_POLL_SECONDS', '1') or 1)
        self.catchup_h = float(env.get('SIGNALS_CATCHUP_HOURS', '24') or 24)
        self.only_magics = {int(x) for x in re.split(r'[,\s]+', env.get('SIGNALS_ONLY_MAGICS', '')) if x.strip().isdigit()}
        self.ignore_magics = {int(x) for x in re.split(r'[,\s]+', env.get('SIGNALS_IGNORE_MAGICS', '')) if x.strip().isdigit()}
        self.aliases = dict(DEFAULT_ALIASES)
        for pair in re.split(r'[,;]', env.get('SIGNALS_SYMBOL_ALIASES', '')):
            if '=' in pair:
                a, b = pair.split('=', 1); self.aliases[a.strip().upper()] = b.strip()


def load_bots(path: Path = HERE / 'bots.json') -> dict[int, str]:
    if not path.is_file(): return {}
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    return {int(k): (v.get('short') or v.get('name')) if isinstance(v, dict) else str(v) for k, v in raw.get('bots', raw).items() if str(k).isdigit()}


# ----------------------------------------------------------------------------------------------------------------------- telegram
class Telegram:
    MIN_GAP = 1.1                                                            # Telegram allows ~1 message / second per chat

    def __init__(self, token: str, timeout: float = 15):
        self.token, self.timeout, self.last = token, timeout, 0.0

    def send(self, chat: str, text: str, reply_to: int | None = None) -> int | None:
        data = {'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}
        if reply_to: data.update(reply_to_message_id=str(reply_to), allow_sending_without_reply='true')
        for attempt in range(5):
            gap = self.MIN_GAP - (time.time() - self.last)
            if gap > 0: time.sleep(gap)
            try:
                req = urllib.request.Request(f'https://api.telegram.org/bot{self.token}/sendMessage', urllib.parse.urlencode(data).encode())
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    self.last = time.time(); body = json.loads(r.read().decode())
                    return body['result']['message_id'] if body.get('ok') else None
            except urllib.error.HTTPError as e:
                self.last = time.time()
                try: body = json.loads(e.read().decode())
                except Exception: body = {}
                if e.code == 429: time.sleep(float(body.get('parameters', {}).get('retry_after', 3)) + 0.5); continue
                raise RuntimeError(f"Telegram error {e.code}: {body.get('description', e.reason)}") from None
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(2 * (attempt + 1))
        raise RuntimeError('Telegram unreachable after 5 attempts')


class ConsoleSender:
    """--dry-run: prints instead of sending; returns fake message ids so reply threading can be checked."""
    def __init__(self): self.n = 0; self.sent = []

    def send(self, chat, text, reply_to=None):
        self.n += 1; self.sent.append(dict(chat=chat, text=text, reply_to=reply_to, id=self.n))
        print(f"\n--- message #{self.n} to {chat or '(chat)'}{f' (reply to #{reply_to})' if reply_to else ''} ---\n{text}", flush=True)
        return self.n


# ----------------------------------------------------------------------------------------------------------------------- terminals
def running_terminals() -> list[str]:
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              "Get-Process terminal64 -ErrorAction SilentlyContinue | ForEach-Object { $_.Path }"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    return sorted({line.strip() for line in out.splitlines() if line.strip()}, key=str.lower)


def installed_terminals() -> list[str]:
    found = set()
    root = Path(os.environ.get('APPDATA', '')) / 'MetaQuotes' / 'Terminal'
    for origin in root.glob('*/origin.txt'):
        try:
            raw = origin.read_bytes(); txt = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8', 'ignore')
            exe = Path(txt.strip().strip('\x00')) / 'terminal64.exe'
            if exe.is_file(): found.add(str(exe))
        except Exception:
            pass
    for base in (Path(r'C:\Program Files'), Path(r'C:\MT5 Instances')):
        if base.is_dir():
            for exe in base.glob('*/terminal64.exe'): found.add(str(exe))
    return sorted(found, key=str.lower)


def terminal_list() -> list[dict]:
    run = {p.lower() for p in running_terminals()}
    paths = sorted(set(running_terminals()) | set(installed_terminals()), key=str.lower)
    out = []
    for p in paths:
        low = p.lower(); kind = 'tester / temp copy' if any(s in low for s in ('_backtests', '\\temp\\', 'codex-mt5', 'mt5-raw-spread')) else ''
        out.append(dict(path=p, running=low in run, note=kind))
    return out


def choose_terminal(arg: str | None) -> str:
    items = terminal_list()
    if arg and not arg.isdigit():
        return arg
    if not items:
        raise SystemExit('No MT5 terminal found. Start MT5 and log in, then rerun.')
    if arg is None:
        print_terminals(items)
        arg = input('Number of the terminal to watch: ').strip()
    i = int(arg) if arg.isdigit() else -1
    if not 1 <= i <= len(items):
        raise SystemExit('Invalid choice.')
    return items[i - 1]['path']


def print_terminals(items=None):
    items = items if items is not None else terminal_list()
    print('MT5 terminals on this PC:')
    for i, t in enumerate(items, 1):
        print(f"  {i}. [{'RUNNING' if t['running'] else 'not running'}] {t['path']}{'  (' + t['note'] + ')' if t['note'] else ''}")


# ----------------------------------------------------------------------------------------------------------------------- watcher
def now_utc() -> datetime: return datetime.now(timezone.utc)


def esc(v) -> str: return html.escape(str(v), quote=False)


def mask(login) -> str: return f"****{str(login)[-4:]}"


class Watcher:
    def __init__(self, mt5, cfg: Config, sender, bots: dict[int, str], state_path: Path, log_dir: Path = LOG_DIR):
        self.mt5, self.cfg, self.sender, self.bots, self.state_path, self.log_dir = mt5, cfg, sender, bots, state_path, log_dir
        self.digits: dict[str, int] = {}
        self.state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.is_file() else None
        self.connected = True

    # ---- helpers
    def save(self):
        tmp = self.state_path.with_suffix('.tmp'); tmp.write_text(json.dumps(self.state, indent=1), encoding='utf-8'); tmp.replace(self.state_path)

    def log(self, kind: str, text: str, **data):
        self.log_dir.mkdir(parents=True, exist_ok=True)
        rec = dict(utc=now_utc().isoformat(timespec='seconds'), kind=kind, text=text, **data)
        with open(self.log_dir / f"events-{now_utc():%Y-%m-%d}.jsonl", 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, default=str) + '\n')

    def post(self, kind: str, text: str, reply_to=None, admin=False, **data) -> int | None:
        chat = self.cfg.admin_chat if admin else self.cfg.chat
        self.log(kind, text, reply_to=reply_to, **data)
        if admin and not chat:
            print(f"[{kind}] {text}", flush=True); return None
        try:
            return self.sender.send(chat, text, reply_to if self.cfg.reply else None)
        except Exception as e:                                               # keep watching; the event stays in the local log + outbox
            self.state.setdefault('outbox', []).append(dict(chat=chat, text=text, reply_to=reply_to, kind=kind))
            print(f"[send failed, queued] {e}", flush=True); return None

    def flush_outbox(self):
        box = self.state.get('outbox') or []
        while box:
            m = box[0]
            try: self.sender.send(m['chat'], m['text'], m['reply_to'] if self.cfg.reply else None)
            except Exception: return
            box.pop(0)

    def wanted(self, magic: int) -> bool:
        return (not self.cfg.only_magics or magic in self.cfg.only_magics) and magic not in self.cfg.ignore_magics

    def bot(self, magic: int, comment: str = '') -> str:
        if magic in self.bots: return self.bots[magic]
        if magic == 0: return 'manual'
        return comment.strip() or f'magic {magic}'

    def sym(self, s: str) -> str:
        base = re.match(r'[A-Za-z0-9]+', s or ''); b = (base.group(0) if base else s).upper()
        for cut in (b, re.sub(r'(CASH|M|PRO|ECN|RAW|Z|C)$', '', b)):
            if cut in self.cfg.aliases: return self.cfg.aliases[cut]
        return re.sub(r'(M|PRO|ECN|RAW)$', '', b) if len(b) > 6 and b[:6].isalpha() else b

    def px(self, symbol: str, v) -> str:
        if not v: return 'none'
        if symbol not in self.digits:
            info = self.mt5.symbol_info(symbol); self.digits[symbol] = int(info.digits) if info else 5
        return f"{v:.{self.digits[symbol]}f}"

    # ---- message templates (Telegram HTML: values in bold; names escaped)
    def b(self, v) -> str: return f'<b>{esc(str(v))}</b>'

    def dot(self, side: str) -> str: return '🟢' if side.lower().startswith('buy') else '🔴'

    def tag(self, side: str, symbol: str, magic: int, comment='') -> str:
        return f"{self.dot(side)} <b>{esc(self.sym(symbol))} {esc(side.upper())}</b> · {esc(self.bot(magic, comment))}"

    def levels(self, symbol, entry, tp, sl) -> list[str]:
        return [f"📍 Entry: {self.b(self.px(symbol, entry))}",
                f"🎯 TP: {self.b(self.px(symbol, tp)) if tp else 'open (the bot manages the exit)'}",
                f"🛑 SL: {self.b(self.px(symbol, sl)) if sl else 'none'}"]

    def risk(self) -> list[str]: return ['', f"⚠️ <i>{esc(self.cfg.risk_note)}</i>"] if self.cfg.risk_note else []

    def alert(self, symbol) -> str:
        s = self.sym(symbol); return f"🚨🔥 <b>{esc(ASSETS.get(s, s))} ALERT</b> 🔥🚨"

    def open_text(self, p, entry, header=None, delayed=False) -> str:
        lines = [header or self.alert(p['symbol']), '', f"{self.dot(p['side'])} <b>{esc(self.sym(p['symbol']))} {esc(p['side'].upper())}</b>",
                 f"🤖 Bot: {esc(self.bot(p['magic'], p['comment']))}", '', *self.levels(p['symbol'], entry, p['tp'], p['sl']), *self.risk()]
        if delayed: lines += ['', '🕒 <i>Sent late: this trade opened while the forwarder was offline.</i>']
        return '\n'.join(lines)

    # ---- snapshots
    def snap_positions(self) -> dict:
        return {str(p.ticket): dict(symbol=p.symbol, side='Buy' if p.type == 0 else 'Sell', magic=int(p.magic), comment=p.comment or '', sl=p.sl, tp=p.tp,
                                    volume=p.volume, price=p.price_open, time=int(p.time)) for p in (self.mt5.positions_get() or [])}

    def snap_orders(self) -> dict:
        return {str(o.ticket): dict(symbol=o.symbol, type=int(o.type), magic=int(o.magic), comment=o.comment or '', price=o.price_open, sl=o.sl, tp=o.tp,
                                    volume=o.volume_current, expiration=int(o.time_expiration or 0), stoplimit=getattr(o, 'price_stoplimit', 0.0))
                for o in (self.mt5.orders_get() or []) if int(o.type) in PENDING_TYPES}

    def deals_since(self, since_epoch: int) -> list:
        frm = datetime.fromtimestamp(max(since_epoch - 86400, 0), timezone.utc); to = now_utc() + timedelta(days=3)  # deal times are server time
        return sorted(self.mt5.history_deals_get(frm, to) or [], key=lambda d: (d.time_msc, d.ticket))

    # ---- lifecycle
    def start(self, login: int, server: str):
        if self.state and (self.state.get('login') != login or self.state.get('server') != server):
            raise SystemExit('State file belongs to another account.')
        if self.state is None:                                               # first run: baseline silently (no history replay)
            deals = self.deals_since(int(time.time()) - 7 * 86400)
            self.state = dict(version=VERSION, login=login, server=server, last_deal=max([d.ticket for d in deals], default=0),
                              last_deal_time=max([d.time for d in deals], default=int(time.time())), positions={}, orders={}, msgs={}, order_msgs={},
                              initial_sl={}, outbox=[], seen_deals=[], filled={})
            self.state['positions'] = self.snap_positions(); self.state['orders'] = self.snap_orders()
            for k, p in self.state['positions'].items(): self.state['initial_sl'][k] = p['sl']
            self.log('baseline', f"{len(self.state['positions'])} open positions, {len(self.state['orders'])} pending orders")
            if self.cfg.announce_open:
                for k, p in self.state['positions'].items():
                    if self.wanted(p['magic']):
                        self.state['msgs'][k] = self.post('open', self.open_text(p, p['price'], header='📌 <b>ALREADY OPEN</b>'), position=k)
            self.save()
        else:
            for k, v in (('filled', {}), ('order_msgs', {}), ('outbox', []), ('seen_deals', [])): self.state.setdefault(k, v)
            self.log('restart', 'resuming from saved state'); self.poll(catchup=True)

    def poll(self, catchup=False):
        s = self.state; changed = False
        term = self.mt5.terminal_info()
        ok = bool(term and term.connected)
        if ok != self.connected:
            self.connected = ok
            self.post('connection', f"{'✅ MT5 reconnected' if ok else '⚠️ MT5 connection LOST'} ({esc(s['server'])} {mask(s['login'])})", admin=True)
        if not ok: return
        self.flush_outbox()
        seen = set(s.get('seen_deals', []))
        new = [d for d in self.deals_since(s['last_deal_time']) if d.ticket > s['last_deal'] and d.ticket not in seen]
        newest = max([d.time for d in new], default=0)                      # deal times are broker server time: compare deals with deals
        for d in new:
            if catchup and newest - d.time > self.cfg.catchup_h * 3600:      # restart after a long gap: log old events, do not post them
                self.log('skipped-old', f'deal {d.ticket} older than the catch-up window', deal=d.ticket)
            else:
                self.on_deal(d, delayed=catchup)                             # catch-up events happened while the forwarder was offline
            s['last_deal'] = d.ticket; s['last_deal_time'] = max(s['last_deal_time'], int(d.time)); seen.add(d.ticket); changed = True
        s['seen_deals'] = sorted(seen)[-500:]
        cur = self.snap_positions()
        for k, p in cur.items():
            old = s['positions'].get(k)
            if old is None:                                                  # opened without a visible deal yet (history lag): announce now
                self.announce_open(k, p, None, False); changed = True; continue
            if (abs((p['sl'] or 0) - (old['sl'] or 0)) > 1e-12 or abs((p['tp'] or 0) - (old['tp'] or 0)) > 1e-12) and self.wanted(p['magic']):
                sl_moved = abs((p['sl'] or 0) - (old['sl'] or 0)) > 1e-12
                lines = ['✏️ <b>TRADE UPDATE</b>', '', self.tag(p['side'], p['symbol'], p['magic'], p['comment']), '']
                if sl_moved: lines.append(f"🛑 SL moved → {self.b(self.px(p['symbol'], p['sl']))}" if p['sl'] else '🛑 SL removed')
                if abs((p['tp'] or 0) - (old['tp'] or 0)) > 1e-12: lines.append(f"🎯 TP moved → {self.b(self.px(p['symbol'], p['tp']))}" if p['tp'] else '🎯 TP removed')
                be = p['sl'] and ((p['side'] == 'Buy' and p['sl'] >= p['price']) or (p['side'] == 'Sell' and p['sl'] <= p['price']))
                if be and sl_moved: lines += ['', '🔒 Stop at or beyond entry: <b>risk-free</b>']
                self.post('update', '\n'.join(lines), reply_to=s['msgs'].get(k), position=k)
                if not s['initial_sl'].get(k) and p['sl']: s['initial_sl'][k] = p['sl']
            s['positions'][k] = p; changed = True if p != old else changed
        for k in [k for k in s['positions'] if k not in cur]:               # closed: the OUT deal already posted; drop the record
            s['positions'].pop(k); changed = True
        changed |= self.diff_orders()
        if changed: self.save()

    def announce_open(self, pos_key: str, p: dict, deal, delayed: bool, from_order: str | None = None):
        s = self.state; s['positions'][pos_key] = p; s['initial_sl'].setdefault(pos_key, p['sl'])
        if not self.wanted(p['magic']): return
        header = None
        if from_order:
            o = s['orders'].get(from_order) or s['filled'].get(from_order) or {}
            header = f"⚡ <b>{esc(ORDER_NAMES.get(o.get('type', -1), 'Pending').upper())} FILLED</b> ⚡"
        entry = deal.price if deal is not None else p['price']
        txt = self.open_text(p, entry, header=header, delayed=delayed)
        reply = s['order_msgs'].pop(from_order, None) if from_order else None
        s['msgs'][pos_key] = self.post('open', txt, reply_to=reply, position=pos_key, deal=getattr(deal, 'ticket', None))

    def on_deal(self, d, delayed=False):
        s = self.state
        if d.type not in (DEAL_BUY, DEAL_SELL):
            name = BALANCE_TYPES.get(d.type, f'account operation {d.type}')
            if d.type == 2: name = 'deposit' if d.profit > 0 else 'withdrawal'
            self.log('account', name, deal=d.ticket)
            if self.cfg.show_account:
                amount = f": {self.b(f'{d.profit:+,.2f}')}" if self.cfg.show_money else ''
                self.post('account', f"🏦 <b>ACCOUNT</b> · {esc(name)}{amount}", admin=False)
            return
        key = str(d.position_id)
        if d.entry == ENTRY_IN:
            pos = next(iter(self.mt5.positions_get(ticket=d.position_id) or []), None)
            if pos is not None:
                p = dict(symbol=pos.symbol, side='Buy' if pos.type == 0 else 'Sell', magic=int(pos.magic), comment=pos.comment or '', sl=pos.sl, tp=pos.tp,
                         volume=pos.volume, price=pos.price_open, time=int(pos.time))
            else:                                                            # already closed again: take SL / TP from the opening order
                o = next(iter(self.mt5.history_orders_get(ticket=d.order) or []), None)
                p = dict(symbol=d.symbol, side='Buy' if d.type == DEAL_BUY else 'Sell', magic=int(d.magic), comment=d.comment or '',
                         sl=getattr(o, 'sl', 0.0), tp=getattr(o, 'tp', 0.0), volume=d.volume, price=d.price, time=int(d.time))
            if key in s['positions'] and key in s['msgs']:                  # scaling into an existing position (netting)
                s['positions'][key] = p; return
            from_order = str(d.order) if str(d.order) in s['orders'] or str(d.order) in s['filled'] else None
            self.announce_open(key, p, d, delayed, from_order)
            if from_order: s['orders'].pop(from_order, None); s['filled'].pop(from_order, None)
            if pos is None:                                                  # opened and closed between two polls: keep it for the OUT deal
                s['positions'][key] = p
            return
        if d.entry in (ENTRY_OUT, ENTRY_OUT_BY, ENTRY_INOUT):
            p = s['positions'].get(key) or dict(symbol=d.symbol, side='Sell' if d.type == DEAL_BUY else 'Buy', magic=int(d.magic), comment=d.comment or '',
                                                sl=0.0, tp=0.0, volume=d.volume, price=0.0)
            if not self.wanted(p['magic']): return
            still = next(iter(self.mt5.positions_get(ticket=d.position_id) or []), None)
            sign = 1 if p['side'] == 'Buy' else -1
            res = []; pts = None; risk = 0.0
            if p['price']:
                pts = sign * (d.price - p['price']); res.append(f"{pts:+.{self.digits_of(p['symbol'])}f}")
                risk = abs(p['price'] - (s['initial_sl'].get(key) or 0)) if s['initial_sl'].get(key) else 0
                if self.cfg.show_r and risk > 0: res.insert(0, f"{pts / risk:+.2f}R")
            money = d.profit + d.commission + d.swap + getattr(d, 'fee', 0.0)
            reason = REASONS.get(int(d.reason), 'closed')
            body = ['', self.tag(p['side'], p['symbol'], p['magic'], p['comment']), '', f"📤 Exit: {self.b(self.px(p['symbol'], d.price))}"]
            if still is not None and d.entry != ENTRY_INOUT:
                part = f"{100 * d.volume / max(p['volume'], 1e-12):.0f}%" if p['volume'] else 'part'
                lines = ['💰 <b>PARTIAL CLOSE</b> 💰', *body, f"✂️ Closed: <b>{part}</b> of the position"]
                p['volume'] = still.volume
            else:
                lines = [self.close_head(int(d.reason), pts, risk, money), *body]
            if res: lines.append(f"📊 Result: {self.b(' (' .join(res) + (')' if len(res) > 1 else ''))}")
            if self.cfg.show_money: lines.append(f"💵 Profit: {self.b(f'{money:+,.2f} ' + self.state.get('currency', ''))}")
            lines.append(f"ℹ️ {esc(reason[0].upper() + reason[1:])}")
            if delayed: lines += ['', '🕒 <i>Sent late: closed while the forwarder was offline.</i>']
            self.post('close' if still is None else 'partial', '\n'.join(lines), reply_to=s['msgs'].get(key), position=key, deal=d.ticket)
            if still is None:
                s['positions'].pop(key, None); s['msgs'].pop(key, None); s['initial_sl'].pop(key, None)

    @staticmethod
    def close_head(reason: int, pts, risk: float, money: float) -> str:
        if reason == 5: return '✅ <b>TAKE PROFIT HIT</b> ✅'
        ref = pts if pts is not None else money
        flat = ref is not None and abs(ref) <= (0.05 * risk if risk > 0 and pts is not None else 1e-9)
        if reason == 4:
            return '🛑 <b>STOP LOSS HIT</b>' if ref is not None and ref < 0 and not flat else '⚪ <b>CLOSED AT BREAKEVEN</b>' if flat else '🔒 <b>STOPPED IN PROFIT</b>'
        if reason == 6: return '⛔ <b>STOP OUT</b>'
        if flat: return '⚪ <b>CLOSED AT BREAKEVEN</b>'
        return '✅ <b>CLOSED IN PROFIT</b>' if ref > 0 else '❌ <b>CLOSED AT A LOSS</b>'

    def digits_of(self, symbol):
        self.px(symbol, 1.0); return self.digits.get(symbol, 5)

    def diff_orders(self) -> bool:
        s = self.state; cur = self.snap_orders(); changed = False
        for k, o in cur.items():
            old = s['orders'].get(k)
            if not self.wanted(o['magic']):
                s['orders'][k] = o; continue
            name = self.tag(ORDER_NAMES.get(o['type'], 'Pending'), o['symbol'], o['magic'], o['comment'])
            if old is None:
                if self.cfg.show_pending:
                    lines = ['⏳ <b>PENDING ORDER</b> ⏳', '', name, '', *self.levels(o['symbol'], o['price'], o['tp'], o['sl'])]
                    if o['expiration']: lines.append(f"⌛ Expires: {datetime.fromtimestamp(o['expiration'], timezone.utc):%Y-%m-%d %H:%M} (server time)")
                    s['order_msgs'][k] = self.post('pending', '\n'.join(lines + self.risk()), order=k)
                changed = True
            else:
                lines = [f"{icon} {lab} moved → {self.b(self.px(o['symbol'], o[f]))}" for f, lab, icon in (('price', 'Entry', '📍'), ('sl', 'SL', '🛑'), ('tp', 'TP', '🎯'))
                         if abs((o[f] or 0) - (old[f] or 0)) > 1e-12]
                if lines and self.cfg.show_pending:
                    self.post('pending-update', '\n'.join(['✏️ <b>ORDER UPDATE</b>', '', name, ''] + lines), reply_to=s['order_msgs'].get(k), order=k)
                changed |= o != old
            s['orders'][k] = o
        for k in [k for k in s['orders'] if k not in cur]:
            o = s['orders'].pop(k); changed = True
            h = next(iter(self.mt5.history_orders_get(ticket=int(k)) or []), None)
            state = ORDER_STATE.get(int(h.state), 'Removed') if h is not None else 'Removed'
            if state == 'Filled':                                            # its IN deal (maybe not in the history yet) announces the position
                s['filled'][k] = o; continue
            if not self.wanted(o['magic']) or not self.cfg.show_pending:
                s['order_msgs'].pop(k, None); continue
            name = self.tag(ORDER_NAMES.get(o['type'], 'Pending'), o['symbol'], o['magic'], o['comment'])
            self.post('pending-' + state.lower(), f"🚫 <b>ORDER {state.upper()}</b>\n\n{name}", reply_to=s['order_msgs'].pop(k, None), order=k)
        return changed


# ----------------------------------------------------------------------------------------------------------------------- main
class AccountLock:
    def __init__(self, path: Path): self.path, self.fh = path, None

    def __enter__(self):
        self.fh = open(self.path, 'a+')
        try:
            import msvcrt
            self.fh.seek(0); msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
        except ImportError:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SystemExit('Another forwarder is already watching this account (lock held).') from None
        return self

    def __exit__(self, *a):
        try: self.fh.close()
        except Exception: pass


def main(argv=None):
    ap = argparse.ArgumentParser(description='Forward MT5 trade events to Telegram (read-only).')
    ap.add_argument('--list', action='store_true', help='list MT5 terminals and exit')
    ap.add_argument('--terminal', help='number from --list, or the full path of terminal64.exe')
    ap.add_argument('--dry-run', action='store_true', help='print messages instead of sending')
    ap.add_argument('--test-telegram', action='store_true', help='send one test message to the channel and exit')
    ap.add_argument('--login', action='store_true', help='user mode: QR login + choose the channel, then exit')
    ap.add_argument('--pick-chat', action='store_true', help='user mode: choose the channel again')
    ap.add_argument('--logout', action='store_true', help='user mode: end the Telegram session and delete the saved login')
    ap.add_argument('--env', default=str(HERE / '.env'))
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):                                  # emojis must not crash a legacy Windows code page
        try: stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception: pass
    if a.list:
        print_terminals(); return
    cfg = Config(load_env(Path(a.env)))
    client = None; path = None
    if not (a.login or a.pick_chat or a.logout or a.test_telegram):          # choose + check the terminal before any Telegram login
        path = choose_terminal(a.terminal)
        if path.lower() not in {p.lower() for p in running_terminals()}:
            raise SystemExit(f'{path} is not running. Start it yourself and log in (this tool never launches MT5).')
    if a.dry_run:
        sender = ConsoleSender()
    elif cfg.mode == 'user':                                                 # QR login with your own Telegram account
        import telegram_user as tu
        STATE_DIR.mkdir(exist_ok=True); session = STATE_DIR / 'telegram-user.session'; saved = STATE_DIR / 'telegram-chat.json'
        if not (str(cfg.api_id).strip().isdigit() and cfg.api_hash):
            cfg.api_id, cfg.api_hash = tu.obtain_api_credentials(Path(a.env))
        client = tu.make_client(cfg.api_id, cfg.api_hash, session)
        if a.logout:
            tu.logout(client, session); saved.unlink(missing_ok=True); print('Logged out; saved Telegram login deleted.'); return
        tu.qr_login(client, STATE_DIR)
        if a.pick_chat or (not cfg.chat and not saved.is_file()):
            tu.pick_chat(client, saved)
        if not cfg.chat:
            c = json.loads(saved.read_text(encoding='utf-8')); cfg.chat = c['id']; print(f"Posting to: {c['title']}")
        cfg.admin_chat = cfg.admin_chat or 'me'                              # alerts go to your Saved Messages
        sender = tu.UserTelegram(client)
        if a.login or a.pick_chat:
            client.disconnect(); print('Login saved. Start the forwarder normally now.'); return
    else:
        if a.login or a.pick_chat or a.logout:
            raise SystemExit('--login / --pick-chat / --logout are for QR (user) mode. Remove TELEGRAM_MODE=bot from .env to use the QR login.')
        if not cfg.token or not cfg.chat:
            raise SystemExit('Bot mode: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env, or set TELEGRAM_MODE=user for QR login, or use --dry-run.')
        sender = Telegram(cfg.token)
    if a.test_telegram:
        sender.send(cfg.chat, f'Signal forwarder test message ({VERSION}).'); print('Test message sent.')
        if client: client.disconnect()
        return
    if not path:
        raise SystemExit('No MT5 terminal selected.')
    import MetaTrader5 as mt5
    if not mt5.initialize(path=path, timeout=60_000):
        raise SystemExit(f'MT5 attach failed: {mt5.last_error()}')
    acc = mt5.account_info()
    if acc is None:
        mt5.shutdown(); raise SystemExit('The terminal has no logged-in account.')
    STATE_DIR.mkdir(exist_ok=True)
    key = re.sub(r'[^A-Za-z0-9_.-]', '_', f'{acc.server}-{acc.login}') + ('-dryrun' if a.dry_run else '')   # dry runs never touch the real state
    print(f"Watching {acc.server} {mask(acc.login)} ({'demo' if acc.trade_mode == 0 else 'real' if acc.trade_mode == 2 else 'contest'}) via {path}")
    print(f"Posting to {'console (dry run)' if a.dry_run else 'Telegram chat ' + cfg.chat}. Ctrl+C to stop.")
    with AccountLock(STATE_DIR / f'{key}.lock'):
        w = Watcher(mt5, cfg, sender, load_bots(), STATE_DIR / f'{key}.json')
        w.start(acc.login, acc.server); w.state['currency'] = acc.currency
        fails = 0
        try:
            while True:
                try:
                    w.poll(); fails = 0
                except Exception as e:                                       # transient API errors: log, back off, re-attach if the terminal is gone
                    fails += 1; w.log('error', repr(e)); print(f'[error] {e!r}', flush=True)
                    if fails in (5, 50): w.post('error', f'Forwarder error x{fails}: {e!r}', admin=True)
                    if path.lower() not in {p.lower() for p in running_terminals()}:
                        print('Terminal closed; waiting for it to be started again (not launching it).', flush=True)
                        while path.lower() not in {p.lower() for p in running_terminals()}: time.sleep(15)
                        mt5.initialize(path=path, timeout=60_000)
                    time.sleep(min(30, 2 * fails))
                time.sleep(cfg.poll)
        except KeyboardInterrupt:
            print('Stopped.')
        finally:
            w.save(); mt5.shutdown()
            if client: client.disconnect()


if __name__ == '__main__':
    main()
