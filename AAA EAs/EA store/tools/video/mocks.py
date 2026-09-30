"""HTML mock-ups for the explainer video (title/outro cards, ZIP listing, installer console, MT5 steps).

MT5 screens are clean illustrations: no real account numbers, logins, balances or desktop content.
"""
from __future__ import annotations

from html import escape

BASE_CSS = """
*{box-sizing:border-box} body{margin:0;width:1920px;height:1080px;overflow:hidden;font-family:Manrope,Segoe UI,sans-serif;
background:radial-gradient(circle at 75% 20%,rgba(22,91,72,.35),transparent 40%),linear-gradient(180deg,#07100f,#081310);color:#fff}
.mono{font-family:'DM Mono',Consolas,monospace}
.tag{position:absolute;right:48px;bottom:36px;padding:10px 16px;border:1px solid rgba(251,191,36,.5);border-radius:999px;
color:#fde68a;background:rgba(251,191,36,.1);font:600 20px 'DM Mono',Consolas,monospace;letter-spacing:.08em}
.eyebrow{color:#7ef7c7;font:600 22px 'DM Mono',Consolas,monospace;letter-spacing:.28em;text-transform:uppercase}
.win{position:absolute;background:#f0f0f0;color:#111;border:1px solid #7a7a7a;box-shadow:0 30px 90px rgba(0,0,0,.55);font-family:Segoe UI,Tahoma,sans-serif}
.win .bar{height:44px;background:#fff;border-bottom:1px solid #d0d0d0;display:flex;align-items:center;padding:0 16px;font-size:19px}
.hl{outline:4px solid #7ef7c7;outline-offset:4px;border-radius:6px;box-shadow:0 0 0 12px rgba(126,247,199,.18)}
.callout{position:absolute;padding:16px 22px;border-radius:16px;background:linear-gradient(135deg,#c4ff63,#7ef7c7);color:#06110e;
font:800 26px Manrope,Segoe UI,sans-serif;box-shadow:0 20px 60px rgba(0,0,0,.4)}
"""
FONTS = '<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">'


def page(body: str, extra_css: str = "") -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'>{FONTS}<style>{BASE_CSS}{extra_css}</style></head><body>{body}</body></html>"


def title_card(logo_url: str) -> str:
    return page(f"""
<div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 160px">
  <div style="display:flex;align-items:center;gap:28px"><img src="{logo_url}" style="width:110px;height:110px;border-radius:24px;border:1px solid rgba(126,247,199,.35)">
  <div><div style="font-weight:800;font-size:44px;letter-spacing:.16em">CALYX</div><div class="mono" style="color:#8fa6a1;letter-spacing:.3em;font-size:20px">TRADING SYSTEMS</div></div></div>
  <div class="eyebrow" style="margin-top:80px">How it works</div>
  <div style="margin-top:22px;font-size:104px;font-weight:800;letter-spacing:-.045em;line-height:1">Pick your bots.<br>Pay in USDT.<br><span style="background:linear-gradient(135deg,#c4ff63,#7ef7c7);-webkit-background-clip:text;color:transparent">Install in one click.</span></div>
  <div style="margin-top:44px;color:#9cafaa;font-size:30px">Catalogue → cart (buy 3, get 1 free) → USDT checkout → download → MetaTrader 5</div>
</div>""")


def outro_card(logo_url: str) -> str:
    steps = ["Browse the evidence", "Buy 3, get 1 free", "Pay USDT · TRC20 / BEP20", "Download & run the BAT",
             "Allow WebRequest", "Enable Algo Trading yourself"]
    items = "".join(f"<div style='padding:26px 30px;border:1px solid rgba(255,255,255,.1);border-radius:22px;background:rgba(255,255,255,.03);font-size:30px;font-weight:700'><span class='mono' style='color:#7ef7c7;margin-right:16px'>{i + 1:02d}</span>{escape(s)}</div>" for i, s in enumerate(steps))
    return page(f"""
<div style="position:absolute;inset:0;padding:120px 160px">
  <div style="display:flex;align-items:center;gap:22px"><img src="{logo_url}" style="width:80px;height:80px;border-radius:18px"><div style="font-weight:800;font-size:36px;letter-spacing:.16em">CALYX</div></div>
  <div style="margin-top:60px;font-size:86px;font-weight:800;letter-spacing:-.04em">From catalogue to chart.</div>
  <div style="margin-top:50px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:22px">{items}</div>
  <div style="margin-top:60px;color:#9cafaa;font-size:28px;line-height:1.5">Start on a demo account. Backtests are evidence, not a forecast — trading leveraged products can lose all deposited capital.<br><span style="color:#7ef7c7">calyx.duckdns.org/how-it-works</span></div>
</div>""")


def zip_listing(bot: str, ex5: str) -> str:
    files = [(ex5, "Compiled Expert Advisor (Calyx store build, online license check)", "EX5"),
             (f"{bot} - Calyx.set", "Settings with your license key pre-filled", "SET"),
             (f"INSTALL {bot}.bat", "Double-click to install", "BAT"),
             ("Install-CalyxBot.ps1", "The installer (PowerShell only, no Python)", "PS1"),
             ("README.txt", "Step-by-step instructions", "TXT"),
             ("LICENSE.txt", "1 live + 1 demo account, 12 months of updates", "TXT")]
    rows = "".join(f"""<div class="row {'hl' if kind == 'BAT' else ''}"><span class="ico">{kind}</span><span class="name">{escape(name)}</span><span class="desc">{escape(desc)}</span></div>""" for name, desc, kind in files)
    css = """.row{display:grid;grid-template-columns:90px 640px 1fr;align-items:center;gap:20px;padding:20px 26px;border-bottom:1px solid #e3e3e3;font-size:26px}
.ico{display:grid;place-items:center;height:52px;border-radius:10px;background:#0b1715;color:#7ef7c7;font:700 17px 'DM Mono',Consolas,monospace}.name{font-weight:600}.desc{color:#555}"""
    return page(f"""
<div class="win" style="left:190px;top:150px;width:1540px;height:760px">
  <div class="bar">📁&nbsp; Calyx {escape(bot)}.zip &nbsp;›&nbsp; Calyx {escape(bot)}</div>
  <div style="padding:10px 0">{rows}</div>
</div>
<div class="callout" style="left:1180px;top:80px">Extract the ZIP, then double-click the BAT</div>
<div class="tag">ILLUSTRATION · DEMO LICENSE</div>""", css)


def installer_console(lines: list[str]) -> str:
    body = "".join(f"<div class='{cls}'>{escape(text[:128] + ('…' if len(text) > 128 else '')) if text else '&nbsp;'}</div>" for cls, text in lines)
    css = """.term{position:absolute;left:150px;top:90px;width:1620px;height:900px;background:#0c0c0c;border:1px solid #444;border-radius:12px;box-shadow:0 30px 90px rgba(0,0,0,.6);overflow:hidden}
.term .bar{height:46px;background:#1f1f1f;color:#ddd;display:flex;align-items:center;padding:0 18px;font:18px Segoe UI,sans-serif}
  .out{padding:22px 28px;font:20px/1.45 Consolas,'DM Mono',monospace;color:#d6d6d6;white-space:pre}
.c{color:#61d6d6}.g{color:#7ef7a0}.y{color:#f2d56b}.d{color:#8a8a8a}.w{color:#fff}"""
    return page(f"""<div class="term"><div class="bar">C:\\WINDOWS\\system32\\cmd.exe — INSTALL ORB Volume Profile.bat</div><div class="out">{body}</div></div>
<div class="tag">REAL INSTALLER OUTPUT · FAKE DEMO FOLDERS</div>""", css)


def mt5_frame(inner: str, callout: str, callout_pos: tuple[int, int]) -> str:
    menu = "".join(f"<span style='padding:0 14px'>{m}</span>" for m in ["File", "View", "Insert", "Charts", "Tools", "Window", "Help"])
    css = """.mt5{position:absolute;left:90px;top:70px;width:1740px;height:940px;background:#fff;border:1px solid #888;box-shadow:0 30px 90px rgba(0,0,0,.55);font-family:Segoe UI,Tahoma,sans-serif;color:#111;overflow:hidden}
.menu{height:34px;background:#f5f5f5;border-bottom:1px solid #ddd;display:flex;align-items:center;font-size:17px}
.tool{height:44px;background:#fafafa;border-bottom:1px solid #ddd;display:flex;align-items:center;gap:10px;padding:0 12px;font-size:16px}
.btn{padding:6px 12px;border:1px solid #cfcfcf;border-radius:4px;background:#fff}
.nav{position:absolute;left:0;top:78px;width:330px;bottom:190px;border-right:1px solid #ddd;background:#fff;font-size:17px;padding:10px 14px;line-height:1.9}
.chart{position:absolute;left:331px;top:78px;right:0;bottom:190px;background:#000}
.tbx{position:absolute;left:0;right:0;bottom:0;height:190px;border-top:1px solid #bbb;background:#fff;font:16px Consolas,monospace}
.dlg{position:absolute;background:#f0f0f0;border:1px solid #777;box-shadow:0 20px 70px rgba(0,0,0,.45);font-size:18px}
.dlg .t{height:40px;background:#fff;border-bottom:1px solid #ccc;display:flex;align-items:center;padding:0 14px}
.tabs{display:flex;gap:2px;padding:10px 12px 0;font-size:16px}.tabs span{padding:6px 12px;border:1px solid #ccc;border-bottom:0;background:#e9e9e9}.tabs .on{background:#fff}
.chk{display:flex;gap:10px;align-items:center;margin:9px 0}.box{width:20px;height:20px;border:1px solid #666;background:#fff;display:grid;place-items:center;font-size:16px}
"""
    return page(f"""<div class="mt5"><div class="menu">{menu}</div>
<div class="tool"><span class="btn">New Order</span><span class="btn" id="algo">▶ Algo Trading</span><span class="btn">M1</span><span class="btn">M5</span><span class="btn">M15</span><span class="btn">H1</span></div>
{inner}</div>
<div class="callout" style="left:{callout_pos[0]}px;top:{callout_pos[1]}px">{escape(callout)}</div>
<div class="tag">ILLUSTRATION · MOCK-UP, NO REAL ACCOUNT</div>""", css)


def _chart_svg(with_ea: bool) -> str:
    import random

    rnd = random.Random(7)
    price, candles = 250.0, []
    for i in range(70):
        o = price
        c = o + rnd.uniform(-24, 26)
        h, l = max(o, c) + rnd.uniform(3, 16), min(o, c) - rnd.uniform(3, 16)
        price = c
        x = 20 + i * 19
        color = "#00e676" if c >= o else "#ff3d3d"
        candles.append(f"<line x1='{x}' x2='{x}' y1='{600 - h}' y2='{600 - l}' stroke='{color}'/><rect x='{x - 6}' y='{600 - max(o, c)}' width='12' height='{max(2, abs(c - o))}' fill='{color}'/>")
    label = ("<text x='24' y='36' fill='#fff' font-size='20' font-family='Segoe UI'>XAUUSD.r, M5</text>"
             "<text x='1370' y='36' fill='#7ef7c7' font-size='20' font-family='Segoe UI' text-anchor='end'>Calyx ORB Volume Data EA  ☺</text>" if with_ea else
             "<text x='24' y='36' fill='#fff' font-size='20' font-family='Segoe UI'>XAUUSD.r, M5</text>")
    return f"<svg viewBox='0 0 1400 660' width='100%' height='100%' preserveAspectRatio='none'>{''.join(candles)}{label}</svg>"


NAV = """<div class="nav"><b>Navigator</b><br>▾ Expert Advisors<br>&nbsp;&nbsp;▾ Calyx<br>&nbsp;&nbsp;&nbsp;&nbsp;☺ Calyx ORB Volume Data EA<br>&nbsp;&nbsp;▸ Examples<br>▸ Indicators<br>▸ Scripts</div>"""


def mt5_webrequest() -> str:
    inner = NAV + f"<div class='chart'>{_chart_svg(False)}</div><div class='tbx'></div>" + """
<div class="dlg" style="left:420px;top:120px;width:900px;height:640px">
 <div class="t">Options</div>
 <div class="tabs"><span>Server</span><span>Charts</span><span>Trade</span><span class="on">Expert Advisors</span><span>Notifications</span><span>Email</span></div>
 <div style="background:#fff;margin:0 12px;border:1px solid #ccc;height:500px;padding:22px 26px">
  <div class="chk"><span class="box"></span>Disable algorithmic trading when the account has been changed</div>
  <div class="chk"><span class="box"></span>Allow DLL imports (potentially dangerous, enable only for trusted applications)</div>
  <div class="chk hl" style="padding:6px 8px"><span class="box">✔</span><b>Allow WebRequest for listed URL:</b></div>
  <div style="margin:10px 0 0 34px;border:1px solid #999;height:150px;background:#fff;padding:8px 12px;font-family:Consolas,monospace">
   <div style="color:#999">+ add new URL like 'https://www.mql5.com'</div>
   <div class="hl" style="margin-top:8px;padding:4px 6px;background:#dff7ee">https://calyx.duckdns.org</div>
  </div>
  <div style="position:absolute;right:40px;bottom:30px;display:flex;gap:12px"><span class="btn">OK</span><span class="btn">Cancel</span></div>
 </div>
</div>"""
    return mt5_frame(inner, "Tools › Options › Expert Advisors", (1150, 36))


def mt5_profiles() -> str:
    inner = NAV + f"<div class='chart'>{_chart_svg(False)}</div><div class='tbx'></div>" + """
<div class="dlg" style="left:12px;top:34px;width:330px;background:#fff;font-size:18px">
 <div style="padding:8px 16px">New Chart</div><div style="padding:8px 16px">Open Data Folder</div>
 <div style="padding:8px 16px;background:#dff7ee">Profiles ▸</div><div style="padding:8px 16px">Login to Trade Account</div><div style="padding:8px 16px">Exit</div>
</div>
<div class="dlg" style="left:342px;top:150px;width:520px;background:#fff;font-size:18px">
 <div style="padding:8px 16px">Default</div><div style="padding:8px 16px">Euro</div>
 <div class="hl" style="padding:8px 16px;background:#dff7ee;font-weight:700">Calyx - ORB Volume Profile</div>
 <div style="padding:8px 16px;border-top:1px solid #ddd">Save As…</div>
</div>"""
    return mt5_frame(inner, "File › Profiles › Calyx - <your bot>", (1060, 36))


def mt5_algo() -> str:
    inner = NAV + f"<div class='chart'>{_chart_svg(True)}</div><div class='tbx'></div>" + """
<div class="dlg" style="left:520px;top:130px;width:820px;height:600px">
 <div class="t">Calyx ORB Volume Data EA 1.20</div>
 <div class="tabs"><span>About</span><span class="on">Common</span><span>Inputs</span><span>Dependencies</span></div>
 <div style="background:#fff;margin:0 12px;border:1px solid #ccc;height:470px;padding:22px 26px">
  <div style="color:#555;margin-bottom:12px">Common</div>
  <div class="chk hl" style="padding:6px 8px"><span class="box">✔</span><b>Allow Algo Trading</b></div>
  <div class="chk"><span class="box"></span>Allow modification of Signals settings</div>
  <div class="chk"><span class="box"></span>Allow DLL imports</div>
  <div style="margin-top:26px;color:#555">Inputs tab: InpCalyxLicenseKey = CLX-DEMO0-DEMO0-DEMO0-DEMO0 (pre-filled)</div>
  <div style="position:absolute;right:40px;bottom:30px;display:flex;gap:12px"><span class="btn">OK</span><span class="btn">Cancel</span></div>
 </div>
</div>"""
    html = mt5_frame(inner, "F7 › Common › Allow Algo Trading, then the toolbar button", (560, 20))
    return html.replace('<span class="btn" id="algo">', '<span class="btn hl" id="algo" style="background:#dff7ee">')


def mt5_chart() -> str:
    log = [("2026.09.30 14:02:11", "Calyx ORB Volume Data EA (XAUUSD.r,M5)", "Calyx license: activated for account 12345678 (calyx-orb-volume-data-ea)."),
           ("2026.09.30 14:02:11", "Calyx ORB Volume Data EA (XAUUSD.r,M5)", "ORB Volume Data EA initialised (demo account)"),
           ("2026.09.30 14:02:05", "Calyx ORB Volume Data EA (XAUUSD.r,M5)", "loaded successfully")]
    rows = "".join(f"<div style='display:grid;grid-template-columns:220px 470px 1fr;padding:3px 12px;{'background:#dff7ee;font-weight:700' if i == 0 else ''}'><span>{t}</span><span>{s}</span><span>{m}</span></div>" for i, (t, s, m) in enumerate(log))
    inner = NAV + f"<div class='chart'>{_chart_svg(True)}</div>" + f"""<div class="tbx"><div style="display:flex;gap:18px;padding:6px 12px;border-bottom:1px solid #ddd;font-family:Segoe UI"><span>Trade</span><span>History</span><span><b>Experts</b></span><span>Journal</span></div>
<div class="hl" style="margin:8px 6px">{rows}</div></div>"""
    return mt5_frame(inner, "Experts tab: “Calyx license: activated”", (1150, 660))
