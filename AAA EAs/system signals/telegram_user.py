"""Post the signals from YOUR Telegram account, logged in by scanning a QR code (owner request 2026-10-29).

Telegram only allows QR login for user accounts through its official client API (MTProto, here the Telethon library). That API needs an
api_id + api_hash that you create once at https://my.telegram.org -> API development tools (free, 2 minutes). No bot, no phone code.

Login: Telegram app on your phone -> Settings -> Devices -> Link Desktop Device -> scan the QR this tool shows (in the window and as an
image). If your account has two-step verification you type that password into this window yourself.
The login is saved in state/telegram-user.session. That file is FULL ACCESS to your Telegram account: never share it; delete it (or end
the "Calyx Signals" session in Telegram -> Settings -> Devices) to log out. `python signals.py --logout` does both.
"""
from __future__ import annotations

import asyncio
import getpass
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

DEVICE = 'Calyx Signals'
# The owner's Telegram copier project already holds an api id / hash; offered (never printed) when this forwarder has none.
SIBLING_ENVS = [Path(__file__).resolve().parents[2] / 'AAA telegram signals' / '.env']


def _read_env(path: Path) -> dict:
    out = {}
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1); out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def save_env_values(path: Path, values: dict):
    """Set KEY=VALUE lines in .env (replace existing keys, append new ones); values are never printed."""
    lines = path.read_text(encoding='utf-8-sig').splitlines() if path.is_file() else []
    done = set()
    for i, line in enumerate(lines):
        k = line.split('=', 1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else None
        if k in values:
            lines[i] = f'{k}={values[k]}'; done.add(k)
    lines += [f'{k}={v}' for k, v in values.items() if k not in done]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def obtain_api_credentials(env_path: Path) -> tuple[str, str]:
    """QR login needs an api id / hash. Reuse the copier project's (with consent) or let the owner paste them once; saved to .env."""
    for sib in SIBLING_ENVS:
        e = _read_env(sib); aid, ahash = e.get('TELEGRAM_API_ID', ''), e.get('TELEGRAM_API_HASH', '')
        if aid.isdigit() and ahash:
            a = input(f'Telegram API id / hash found in "{sib.parent.name}". Use them here too? [Y/n]: ').strip().lower()
            if a in ('', 'y', 'yes'):
                save_env_values(env_path, {'TELEGRAM_API_ID': aid, 'TELEGRAM_API_HASH': ahash}); print('Saved to .env.'); return aid, ahash
    print('\nQR login needs a Telegram api_id + api_hash (one time, free):')
    print('  1. open https://my.telegram.org and log in with your phone number')
    print('  2. API development tools -> create an app (any name) -> copy api_id and api_hash\n')
    aid = input('api_id: ').strip()
    ahash = getpass.getpass('api_hash (hidden): ').strip()
    if not aid.isdigit() or len(ahash) < 16:
        raise SystemExit('That does not look like an api_id (digits) and api_hash (32 characters).')
    save_env_values(env_path, {'TELEGRAM_API_ID': aid, 'TELEGRAM_API_HASH': ahash}); print('Saved to .env.')
    return aid, ahash


def make_client(api_id: str, api_hash: str, session: Path):
    from telethon.sync import TelegramClient
    if not str(api_id).strip().isdigit() or not api_hash:
        raise SystemExit('QR login needs TELEGRAM_API_ID and TELEGRAM_API_HASH in .env (create them at https://my.telegram.org -> API development tools).')
    session.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(session), int(api_id), api_hash, device_model=DEVICE, system_version='Windows', app_version='signals-1.1')


def show_qr(url: str, folder: Path) -> Path | None:
    import qrcode
    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L); qr.add_data(url); qr.make(fit=True)
    try:
        qr.print_ascii(invert=True)
    except Exception:
        pass
    path = None
    try:
        path = folder / 'login-qr.png'; qr.make_image(fill_color='black', back_color='white').save(path)
    except Exception:                                                        # no Pillow: SVG works in any browser
        import qrcode.image.svg
        path = folder / 'login-qr.svg'; qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage).save(str(path))
    try:
        os.startfile(str(path))                                              # Windows: opens the image so the phone can scan it
    except Exception:
        pass
    return path


def qr_login(client, folder: Path):
    """Connect; if not logged in, show QR codes until the phone scans one (each code lives ~30 s and is renewed)."""
    from telethon import errors
    client.connect()
    if client.is_user_authorized():
        return client.get_me()
    print('\nLog in to Telegram: open Telegram on your phone -> Settings -> Devices -> Link Desktop Device, then scan this QR code.')
    print('(The same code is opened as an image. It renews automatically; Ctrl+C cancels.)\n')
    loop = client.loop; qr = client.qr_login(); img = None; renewals = 0
    try:
        while True:
            img = show_qr(qr.url, folder)
            left = max(5.0, (qr.expires - datetime.now(timezone.utc)).total_seconds())
            try:
                loop.run_until_complete(qr.wait(timeout=left)); break
            except (asyncio.TimeoutError, TimeoutError):
                renewals += 1
                if renewals % 4 == 0:                                        # ~2 minutes without a scan: offer the phone-code login
                    a = input('\nNot scanned yet. Press Enter for a new QR code, or type P to log in with your phone number + code: ').strip().lower()
                    if a == 'p':
                        phone_login(client); break
                loop.run_until_complete(qr.recreate()); print('\nQR code renewed:\n')
            except errors.SessionPasswordNeededError:
                two_step(client); break
    finally:
        if img and img.exists():
            try: img.unlink()
            except OSError: pass
    me = client.get_me()
    print(f"Logged in as {me.first_name or ''} {('@' + me.username) if me.username else ''}".strip())
    return me


def two_step(client):
    from telethon import errors
    for _ in range(3):
        try:
            client.sign_in(password=getpass.getpass('Two-step verification password (typed here, not shown): ')); return
        except errors.PasswordHashInvalidError:
            print('Wrong password, try again.')
    raise SystemExit('Login cancelled after 3 wrong passwords.')


def phone_login(client):
    """Fallback (as in the copier project): Telegram sends a login code to your Telegram app."""
    from telethon import errors
    phone = input('Phone number with country code (e.g. +32...): ').strip()
    client.send_code_request(phone)
    for _ in range(3):
        code = input('Login code from the Telegram app: ').strip()
        try:
            client.sign_in(phone=phone, code=code); return
        except errors.SessionPasswordNeededError:
            two_step(client); return
        except (errors.PhoneCodeInvalidError, errors.PhoneCodeExpiredError) as e:
            print(f'{e.__class__.__name__}: try again.')
    raise SystemExit('Login cancelled after 3 wrong codes.')


def postable_chats(client) -> list[dict]:
    out = [dict(id='me', title='Saved Messages (private test)', kind='self')]
    for d in client.get_dialogs():
        e = d.entity
        if d.is_channel and getattr(e, 'broadcast', False):
            rights = getattr(e, 'admin_rights', None)
            if getattr(e, 'creator', False) or (rights and getattr(rights, 'post_messages', False)):
                out.append(dict(id=str(d.id), title=d.name, kind='channel'))
        elif d.is_group:
            out.append(dict(id=str(d.id), title=d.name, kind='group'))
    return out


def pick_chat(client, saved: Path) -> dict:
    chats = postable_chats(client)
    print('\nWhere should the signals be posted?')
    for i, c in enumerate(chats, 1):
        print(f"  {i}. [{c['kind']}] {c['title']}  ({c['id']})")
    while True:
        a = input('Number: ').strip()
        if a.isdigit() and 1 <= int(a) <= len(chats):
            c = chats[int(a) - 1]; saved.write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding='utf-8'); return c
        print('Invalid choice.')


class UserTelegram:
    """Same interface as signals.Telegram: send(chat, text, reply_to) -> message id."""
    def __init__(self, client):
        self.client = client; self.cache = {}

    def entity(self, chat):
        chat = str(chat).strip()
        if chat in self.cache: return self.cache[chat]
        key = chat if chat == 'me' or chat.startswith('@') else int(chat)
        try:
            ent = self.client.get_input_entity(key)
        except ValueError:                                                   # not in the session cache yet: load the dialog list once
            self.client.get_dialogs(); ent = self.client.get_input_entity(key)
        self.cache[chat] = ent; return ent

    def send(self, chat, text, reply_to=None):
        from telethon import errors
        for attempt in range(5):
            try:
                m = self.client.send_message(self.entity(chat), text, reply_to=reply_to, link_preview=False, parse_mode='html')
                return m.id
            except errors.FloodWaitError as e:                               # Telegram rate limit: wait as told
                time.sleep(e.seconds + 1)
            except (errors.ChatWriteForbiddenError, errors.ChannelPrivateError) as e:
                raise RuntimeError(f'Cannot post to {chat}: {e.__class__.__name__}') from None
            except (ConnectionError, OSError):
                time.sleep(2 * (attempt + 1))
        raise RuntimeError('Telegram unreachable after 5 attempts')


def logout(client, session: Path):
    try:
        client.connect()
        if client.is_user_authorized(): client.log_out()
    finally:
        try: client.disconnect()
        except Exception: pass
    for p in session.parent.glob(session.name + '*'):
        try: p.unlink()
        except OSError: pass
