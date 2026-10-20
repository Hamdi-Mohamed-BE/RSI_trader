"""Item 5: checked event sheet for the news EAs (NFP / CPI / FOMC, USD) from FXMacroData official release times.

Library rule applied: the only events that exist are the ones from the calendar source, with a count check and an
explicit time-zone conversion line. Three outputs:
  1. upcoming sheet (next N days) in UTC / Exness server / Prague (FTMO day) / London / New York;
  2. timing audit: each demo News Pulse / Gold News V9 entry versus the nearest official release, in seconds;
  3. optional research-copy extension of the verified News Pulse TESTER calendar (fail-closed generator, base manifest kept).
Live News Pulse keeps using MT5's broker calendar; nothing here edits a production include, EX5, SET or BAT.

uv run python ".../_Ops Monitor/event_sheet.py" --past-start 2026-09-12 --past-end 2026-10-19 --ahead 14 [--extend-tester]
"""
import argparse, json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from common import OUT, PACKAGE, magic_map, now_utc, save
import news_pulse_calendar as npc
from news_pulse_macro_audit import TARGET_RELEASES, _mcp_call

ZONES = {'UTC': timezone.utc, 'Server (Exness, UTC+0)': timezone.utc, 'Prague (FTMO day)': ZoneInfo('Europe/Prague'),
         'London': ZoneInfo('Europe/London'), 'New York': ZoneInfo('America/New_York')}
NEWS = {'news-pulse-xau', 'news-pulse-xag', 'news-pulse-btc', 'news-pulse-eurusd', 'gold-news-v9-direction'}
BASE_TESTER_MANIFEST = PACKAGE / 'News Pulse Event Replay 2026-09-11' / 'generated-calendar-manifest.json'


def upcoming(start: date, end: date):
    cal, receipt, _ = _mcp_call('release_calendar', {'currency': 'usd', 'start_date': start.isoformat(), 'end_date': end.isoformat(), 'timezone': 'UTC'}, 1)
    rows = [r for r in cal['data'] if str(r.get('release', '')) in TARGET_RELEASES]
    events, unreadable = [], []
    for r in rows:
        if not isinstance(r.get('announcement_datetime'), int):
            unreadable.append(r); continue
        events.append(dict(kind=TARGET_RELEASES[r['release']], epoch=r['announcement_datetime'], confirmed=r.get('release_date_confirmed'),
                           source=r.get('source'), source_url=r.get('source_url')))
    events.sort(key=lambda e: e['epoch'])
    return events, unreadable, receipt, cal.get('data_quality', {}), len(rows)


def times(epoch):
    t = datetime.fromtimestamp(epoch, timezone.utc)
    return {k: t.astimezone(z).strftime('%a %Y-%m-%d %H:%M %Z') for k, z in ZONES.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--past-start', required=True); ap.add_argument('--past-end', required=True)
    ap.add_argument('--ahead', type=int, default=14); ap.add_argument('--extend-tester', action='store_true')
    a = ap.parse_args()
    folder = OUT / 'event_sheet'; folder.mkdir(parents=True, exist_ok=True)
    today = now_utc().date()

    # 1. past official events: the existing FAIL-CLOSED builder (event times only; News Pulse never uses released values)
    past, _raw = npc.build_calendar(a.past_start, a.past_end, event_times_only=True)
    # 2. upcoming events (confirmed scheduled times; latest-available-date check does not apply to the future)
    up, unreadable, receipt, quality, pasted = upcoming(today, today + timedelta(days=a.ahead))
    all_events = sorted({(e['kind'], e['epoch']): e for e in past['events'] + up}.values(), key=lambda e: e['epoch'])

    # 3. demo-account news entries versus the nearest official release
    snap_path = OUT / 'live' / 'latest.json'; audit = []
    if snap_path.exists():
        snap = json.loads(snap_path.read_text(encoding='utf-8')); mm = magic_map()
        for d in snap['deals']:
            if d['type'] in (0, 1) and d['entry'] == 0 and mm.get(d['magic']) in NEWS:
                near = min(all_events, key=lambda e: abs(e['epoch'] - d['time_msc'] / 1000), default=None)
                audit.append(dict(ea=mm[d['magic']], symbol=d['symbol'], side='Buy' if d['type'] == 0 else 'Sell', comment=d['comment'],
                                  entry_utc=datetime.fromtimestamp(d['time_msc'] / 1000, timezone.utc).isoformat(timespec='seconds'),
                                  nearest_event=None if not near else f"{near['kind']} {datetime.fromtimestamp(near['epoch'], timezone.utc):%Y-%m-%d %H:%M} UTC",
                                  offset_s=None if not near else round(d['time_msc'] / 1000 - near['epoch'], 1)))

    ext = None
    if a.extend_tester:
        tdir = folder / 'tester-calendar-extension'
        ext = npc.generate_calendar(a.past_start, a.past_end, tdir / 'NewsPulseTesterCalendar.mqh', tdir / 'generated-calendar-manifest.json',
                                    tdir / 'generated-calendar-mcp-raw.json', event_times_only=True, base_manifest_path=BASE_TESTER_MANIFEST)

    sheet = dict(generated_utc=now_utc().isoformat(), provider='FXMacroData MCP (public tier)', past_window=[a.past_start, a.past_end],
                 past_event_count=past['event_count'], past_calendar_sha256=past['calendar_sha256'], upcoming_window=[today.isoformat(), (today + timedelta(days=a.ahead)).isoformat()],
                 upcoming_rows_returned=pasted, upcoming_events_listed=len(up), upcoming_unreadable=len(unreadable), upcoming_quality=quality, upcoming_receipt=receipt,
                 events=all_events, live_entry_timing=audit,
                 tester_extension=None if not ext else dict(coverage=ext['coverage'], event_count=ext['event_count'], calendar_sha256=ext['calendar_sha256'],
                                                           folder=str(folder / 'tester-calendar-extension')))
    save('latest.json', sheet, folder=folder)

    md = [f'# Event sheet — generated {now_utc():%Y-%m-%d %H:%M} UTC', '',
          'Source: FXMacroData official US release calendar (NFP, CPI, FOMC only — the events News Pulse trades). '
          'No event is added from memory. Live News Pulse discovers events from the broker\'s MT5 calendar; compare it with this sheet.', '',
          f'## Upcoming ({today} → {today + timedelta(days=a.ahead)})', '',
          '| Event | ' + ' | '.join(ZONES) + ' | Confirmed | Note |', '|---|' + '---|' * len(ZONES) + '---|---|']
    for e in up:
        t = times(e['epoch']); utc = datetime.fromtimestamp(e['epoch'], timezone.utc)
        gap = (utc.astimezone(ZONES['Prague (FTMO day)']).utcoffset() - utc.astimezone(ZONES['New York']).utcoffset()).total_seconds() / 3600
        note = f'DST-gap week: Prague–New York is {gap:g}h, not 6h — check any session filter' if gap != 6 else ''
        md.append(f"| {e['kind']} | " + ' | '.join(t.values()) + f" | {e['confirmed']} | {note} |")
    md += ['', f'Count check: {pasted} NFP/CPI/FOMC rows returned, {len(up)} listed, {len(unreadable)} without an exact timestamp.',
           'Time-zone conversions: from UTC epochs; Exness server time is treated as UTC+0 (matches the demo deal timestamps); '
           'Prague uses CET/CEST for the FTMO trading day; New York uses EST/EDT.', '',
           f"## Official events in the review window {a.past_start} → {a.past_end} (fail-closed check passed: {past['event_count']} events)", '']
    md += [f"- {e['kind']} {datetime.fromtimestamp(e['epoch'], timezone.utc):%a %Y-%m-%d %H:%M} UTC" for e in past['events']]
    md += ['', '## Demo news entries versus the official release', '',
           'Negative offset = the order filled BEFORE the official release time (News Pulse places pending straddles before the release, so a '
           'pre-release price move can trigger a leg).', '',
           '| EA | Symbol | Side | Entry (UTC) | Nearest official event | Offset (s) | Comment |', '|---|---|---|---|---|---:|---|']
    md += [f"| {x['ea']} | {x['symbol']} | {x['side']} | {x['entry_utc']} | {x['nearest_event']} | {x['offset_s']:+.1f} | {x['comment']} |" for x in audit] or ['| — | | | | | | |']
    if ext:
        md += ['', '## Tester calendar extension (research copy)', '',
               f"Verified tester calendar extended to {ext['coverage']['start_date']} → {ext['coverage']['end_date']} ({ext['event_count']} events, hash "
               f"{ext['calendar_sha256'][:12]}…) in `output/event_sheet/tester-calendar-extension/`. The production include is unchanged; using it needs a "
               'separately compiled research build of News Pulse.']
    (folder / 'EVENT_SHEET.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md[:12 + len(up)]))
    print(f'past events {past["event_count"]}; demo news entries audited {len(audit)}')
    for x in audit:
        print(' ', x['ea'], x['entry_utc'], x['nearest_event'], x['offset_s'])


if __name__ == '__main__':
    main()
