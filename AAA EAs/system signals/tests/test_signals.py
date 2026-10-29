"""Scenario tests for signals.py against a fake MetaTrader5 module (no terminal, no Telegram). Run: python -m pytest tests -q"""
import sys
from collections import namedtuple
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import signals as S  # noqa: E402

Pos = namedtuple('Pos', 'ticket symbol type magic comment sl tp volume price_open time')
Ord = namedtuple('Ord', 'ticket symbol type magic comment price_open sl tp volume_current time_expiration price_stoplimit')
Deal = namedtuple('Deal', 'ticket order time time_msc type entry magic position_id reason volume price commission swap profit fee symbol comment')
Hist = namedtuple('Hist', 'ticket state sl tp')
Info = namedtuple('Info', 'digits')
Term = namedtuple('Term', 'connected')
NOTE = '⚠️ <i>Risk management is required: use the minimum available lot size or risk max 5% per trade.</i>'


class FakeMT5:
    def __init__(self):
        self.positions, self.orders, self.deals, self.hist, self.connected, self.t = {}, {}, [], {}, True, 1_800_000_000

    def terminal_info(self): return Term(self.connected)
    def symbol_info(self, s): return Info(2 if s.startswith(('USTEC', 'XAU')) else 5)

    def positions_get(self, ticket=None):
        return [self.positions[ticket]] if ticket is not None and ticket in self.positions else ([] if ticket is not None else list(self.positions.values()))

    def orders_get(self, ticket=None): return list(self.orders.values())
    def history_orders_get(self, ticket=None): return [self.hist[ticket]] if ticket in self.hist else []
    def history_deals_get(self, frm, to): return list(self.deals)

    def deal(self, ticket, pos, typ, entry, price, vol, reason=3, magic=862020, order=0, symbol='USTEC', profit=0.0):
        self.t += 60
        self.deals.append(Deal(ticket, order or ticket, self.t, self.t * 1000, typ, entry, magic, pos, reason, vol, price, -0.5, 0.0, profit, 0.0, symbol, ''))


def cfg(**kw):
    c = S.Config({}); c.chat = '@chan'
    for k, v in kw.items(): setattr(c, k, v)
    return c


@pytest.fixture
def env(tmp_path):
    mt5 = FakeMT5()
    mt5.positions[1] = Pos(1, 'XAUUSDm', 0, 926400006, '', 1990.0, 2050.0, 0.1, 2000.0, mt5.t)   # open before the first start: not announced
    out = S.ConsoleSender()
    w = S.Watcher(mt5, cfg(), out, {862020: 'nasdaq 5m', 926400006: 'gold RSI VWAP'}, tmp_path / 'state.json', tmp_path / 'logs')
    w.start(1234567, 'Broker-Demo')
    return mt5, out, w, tmp_path


def texts(out): return [m['text'] for m in out.sent]


def test_full_lifecycle(env):
    mt5, out, w, tmp = env
    assert out.sent == []                                                    # baseline is silent
    # market buy with SL/TP
    mt5.positions[10] = Pos(10, 'USTEC', 0, 862020, '', 25000.0, 25300.0, 1.0, 25100.0, mt5.t)
    mt5.deal(100, 10, 0, 0, 25100.0, 1.0)
    w.poll()
    assert texts(out)[-1] == '\n'.join(['🚨🔥 <b>NASDAQ ALERT</b> 🔥🚨', '', '🟢 <b>US100 BUY</b>', '🤖 Bot: nasdaq 5m', '',
                                         '📍 Entry: <b>25100.00</b>', '🎯 TP: <b>25300.00</b>', '🛑 SL: <b>25000.00</b>', '', NOTE])
    open_id = out.sent[-1]['id']
    # stop moved to breakeven
    mt5.positions[10] = mt5.positions[10]._replace(sl=25100.0)
    w.poll()
    t = texts(out)[-1]
    assert t.startswith('✏️ <b>TRADE UPDATE</b>\n\n🟢 <b>US100 BUY</b> · nasdaq 5m\n\n🛑 SL moved → <b>25100.00</b>') and out.sent[-1]['reply_to'] == open_id
    assert '🔒 Stop at or beyond entry: <b>risk-free</b>' in t
    # half closed by the EA
    mt5.positions[10] = mt5.positions[10]._replace(volume=0.5)
    mt5.deal(101, 10, 1, 1, 25200.0, 0.5)
    w.poll()
    t = texts(out)[-1]
    assert t.startswith('💰 <b>PARTIAL CLOSE</b> 💰\n\n🟢 <b>US100 BUY</b> · nasdaq 5m\n\n📤 Exit: <b>25200.00</b>\n✂️ Closed: <b>50%</b> of the position')
    assert '📊 Result: <b>+1.00R (+100.00)</b>' in t and 'ℹ️ Closed by bot' in t
    # rest hits take profit
    del mt5.positions[10]
    mt5.deal(102, 10, 1, 1, 25300.0, 0.5, reason=5)
    w.poll()
    t = texts(out)[-1]
    assert t.startswith('✅ <b>TAKE PROFIT HIT</b> ✅\n\n🟢 <b>US100 BUY</b> · nasdaq 5m\n\n📤 Exit: <b>25300.00</b>') and '+2.00R' in t and 'ℹ️ Take profit hit' in t
    assert out.sent[-1]['reply_to'] == open_id and '10' not in w.state['positions']
    # no duplicates on an idle poll
    n = len(out.sent); w.poll(); assert len(out.sent) == n


def test_pending_fill_cancel_and_update(env):
    mt5, out, w, tmp = env
    mt5.orders[20] = Ord(20, 'XAUUSDm', 3, 926400006, '', 2100.0, 2110.0, 2080.0, 0.2, 0, 0.0)
    w.poll()
    assert texts(out)[-1] == '\n'.join(['⏳ <b>PENDING ORDER</b> ⏳', '', '🔴 <b>XAUUSD SELL LIMIT</b> · gold RSI VWAP', '',
                                         '📍 Entry: <b>2100.00</b>', '🎯 TP: <b>2080.00</b>', '🛑 SL: <b>2110.00</b>', '', NOTE])
    pend_id = out.sent[-1]['id']
    mt5.orders[20] = mt5.orders[20]._replace(price_open=2101.5)
    w.poll()
    assert texts(out)[-1] == '✏️ <b>ORDER UPDATE</b>\n\n🔴 <b>XAUUSD SELL LIMIT</b> · gold RSI VWAP\n\n📍 Entry moved → <b>2101.50</b>'
    assert out.sent[-1]['reply_to'] == pend_id
    # filled: order gone, history says filled, deal + position appear
    del mt5.orders[20]; mt5.hist[20] = Hist(20, 4, 2110.0, 2080.0)
    mt5.positions[21] = Pos(21, 'XAUUSDm', 1, 926400006, '', 2110.0, 2080.0, 0.2, 2101.5, mt5.t)
    mt5.deal(200, 21, 1, 0, 2101.5, 0.2, magic=926400006, order=20, symbol='XAUUSDm')
    w.poll()
    t = texts(out)[-1]
    assert t.startswith('⚡ <b>SELL LIMIT FILLED</b> ⚡\n\n🔴 <b>XAUUSD SELL</b>\n🤖 Bot: gold RSI VWAP') and '📍 Entry: <b>2101.50</b>' in t
    assert out.sent[-1]['reply_to'] == pend_id and not any('CANCELLED' in x for x in texts(out))
    # a second pending order is cancelled
    mt5.orders[30] = Ord(30, 'USTEC', 4, 862020, '', 25500.0, 25400.0, 0.0, 1.0, 0, 0.0); w.poll()
    assert '🎯 TP: open (the bot manages the exit)' in texts(out)[-1]
    del mt5.orders[30]; mt5.hist[30] = Hist(30, 2, 0, 0); w.poll()
    assert texts(out)[-1] == '🚫 <b>ORDER CANCELLED</b>\n\n🟢 <b>US100 BUY STOP</b> · nasdaq 5m'


def test_fill_seen_before_deal_keeps_thread(env):
    mt5, out, w, tmp = env
    mt5.orders[40] = Ord(40, 'USTEC', 2, 862020, '', 24900.0, 24800.0, 25100.0, 1.0, 0, 0.0); w.poll(); pid = out.sent[-1]['id']
    del mt5.orders[40]; mt5.hist[40] = Hist(40, 4, 24800.0, 25100.0); w.poll()  # history lag: no deal yet
    assert len(out.sent) == 1
    mt5.positions[41] = Pos(41, 'USTEC', 0, 862020, '', 24800.0, 25100.0, 1.0, 24900.0, mt5.t)
    mt5.deal(400, 41, 0, 0, 24900.0, 1.0, order=40); w.poll()
    assert texts(out)[-1].startswith('⚡ <b>BUY LIMIT FILLED</b> ⚡\n\n🟢 <b>US100 BUY</b>') and out.sent[-1]['reply_to'] == pid and len(out.sent) == 2


def test_restart_catchup_no_duplicates(env):
    mt5, out, w, tmp = env
    mt5.positions[50] = Pos(50, 'USTEC', 1, 862020, '', 25200.0, 0.0, 1.0, 25100.0, mt5.t); mt5.deal(500, 50, 1, 0, 25100.0, 1.0); w.poll()
    n = len(out.sent)
    # forwarder offline: the stop is hit
    del mt5.positions[50]; mt5.deal(501, 50, 0, 1, 25200.0, 1.0, reason=4)
    w2 = S.Watcher(mt5, cfg(), out, w.bots, tmp / 'state.json', tmp / 'logs'); w2.start(1234567, 'Broker-Demo')
    t = texts(out)[-1]
    assert len(out.sent) == n + 1 and t.startswith('🛑 <b>STOP LOSS HIT</b>\n\n🔴 <b>US100 SELL</b> · nasdaq 5m') and '-1.00R' in t and 'Sent late' in t
    w2.poll(); assert len(out.sent) == n + 1
    with pytest.raises(SystemExit):
        S.Watcher(mt5, cfg(), out, w.bots, tmp / 'state.json', tmp / 'logs').start(999, 'Other')


def test_open_and_close_between_polls_and_filters(env):
    mt5, out, w, tmp = env
    mt5.hist[60] = Hist(60, 4, 25000.0, 25300.0)
    mt5.deal(60, 60, 0, 0, 25100.0, 1.0, order=60); mt5.deal(61, 60, 1, 1, 25000.0, 1.0, reason=4)     # never visible as a position
    w.poll()
    assert '📍 Entry: <b>25100.00</b>\n🎯 TP: <b>25300.00</b>\n🛑 SL: <b>25000.00</b>' in texts(out)[-2]
    assert texts(out)[-1].startswith('🛑 <b>STOP LOSS HIT</b>') and '-1.00R' in texts(out)[-1]
    # ignored magic and an unknown magic with no stop
    w.cfg.ignore_magics = {862020}; n = len(out.sent)
    mt5.positions[70] = Pos(70, 'USTEC', 0, 862020, '', 0, 0, 1, 25000.0, mt5.t); mt5.deal(700, 70, 0, 0, 25000.0, 1); w.poll()
    assert len(out.sent) == n
    mt5.positions[71] = Pos(71, 'EURUSD.raw', 1, 555, 'my bot', 0.0, 0.0, 0.1, 1.08, mt5.t); mt5.deal(710, 71, 1, 0, 1.08, 0.1, magic=555, symbol='EURUSD.raw'); w.poll()
    t = texts(out)[-1]                                                       # unknown magic: the order comment names the bot
    assert t.startswith('🚨🔥 <b>EURUSD ALERT</b> 🔥🚨\n\n🔴 <b>EURUSD SELL</b>\n🤖 Bot: my bot')
    assert '🎯 TP: open (the bot manages the exit)\n🛑 SL: none' in t


def test_privacy_defaults_and_connection_alert(env):
    mt5, out, w, tmp = env
    mt5.positions[80] = Pos(80, 'USTEC', 0, 862020, '', 25000.0, 0.0, 2.0, 25100.0, mt5.t); mt5.deal(800, 80, 0, 0, 25100.0, 2.0, profit=0); w.poll()
    del mt5.positions[80]; mt5.deal(801, 80, 1, 1, 25150.0, 2.0, profit=100.0); w.poll()
    assert all('lots' not in t and 'Profit:' not in t for t in texts(out))   # volume never shown; $ hidden by default
    assert texts(out)[-1].startswith('✅ <b>CLOSED IN PROFIT</b>')
    mt5.connected = False; n = len(out.sent); w.poll(); mt5.connected = True; w.poll()
    assert len(out.sent) == n                                                # alerts go to the admin chat (console when unset), not the channel
    logs = list((tmp / 'logs').glob('events-*.jsonl')); assert logs and 'connection LOST' in logs[0].read_text(encoding='utf-8')


def test_close_headlines_and_html_escape(env):
    mt5, out, w, tmp = env
    assert S.Watcher.close_head(4, 50.0, 100.0, 0) == '🔒 <b>STOPPED IN PROFIT</b>'
    assert S.Watcher.close_head(4, 1.0, 100.0, 0) == '⚪ <b>CLOSED AT BREAKEVEN</b>'
    assert S.Watcher.close_head(3, -30.0, 100.0, 0) == '❌ <b>CLOSED AT A LOSS</b>'
    assert S.Watcher.close_head(0, 30.0, 100.0, 0) == '✅ <b>CLOSED IN PROFIT</b>'
    w.bots[777] = 'A<B & Co'
    mt5.positions[90] = Pos(90, 'XAUUSDm', 1, 777, '', 0, 0, 0.1, 2000.0, mt5.t); mt5.deal(900, 90, 1, 0, 2000.0, 0.1, magic=777, symbol='XAUUSDm'); w.poll()
    assert '🤖 Bot: A&lt;B &amp; Co' in texts(out)[-1] and texts(out)[-1].startswith('🚨🔥 <b>GOLD ALERT</b> 🔥🚨\n\n🔴 <b>XAUUSD SELL</b>')
    w.cfg.risk_note = ''
    mt5.positions[91] = Pos(91, 'XAUUSDm', 0, 777, '', 0, 0, 0.1, 2000.0, mt5.t); mt5.deal(910, 91, 0, 0, 2000.0, 0.1, magic=777, symbol='XAUUSDm'); w.poll()
    assert '⚠️' not in texts(out)[-1]
