from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class NewsEvent:
    date_label: str
    name: str
    event_type: str
    release_utc: datetime


def dt_utc(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# Last ~3 months from the current project date, focused on scheduled US macro
# releases that commonly move XAU/USD. Times are release windows converted from
# ET to UTC. During Apr-Jul 2026 the US is on EDT, so 08:30 ET = 12:30 UTC.
NEWS_EVENTS: list[NewsEvent] = [
    NewsEvent("Apr 21", "Retail Sales", "Retail", dt_utc(2026, 4, 21, 12, 30)),
    NewsEvent("Apr 29", "FOMC Statement", "FOMC", dt_utc(2026, 4, 29, 18, 0)),
    NewsEvent("Apr 30", "Employment Cost Index", "LaborCosts", dt_utc(2026, 4, 30, 12, 30)),
    NewsEvent("May 05", "JOLTS", "JOLTS", dt_utc(2026, 5, 5, 14, 0)),
    NewsEvent("May 08", "NFP / Jobs", "NFP", dt_utc(2026, 5, 8, 12, 30)),
    NewsEvent("May 12", "CPI", "CPI", dt_utc(2026, 5, 12, 12, 30)),
    NewsEvent("May 13", "PPI", "PPI", dt_utc(2026, 5, 13, 12, 30)),
    NewsEvent("May 14", "Retail Sales", "Retail", dt_utc(2026, 5, 14, 12, 30)),
    NewsEvent("May 20", "FOMC Minutes", "FOMC", dt_utc(2026, 5, 20, 18, 0)),
    NewsEvent("May 29", "PCE", "PCE", dt_utc(2026, 5, 29, 12, 30)),
    NewsEvent("Jun 02", "JOLTS", "JOLTS", dt_utc(2026, 6, 2, 14, 0)),
    NewsEvent("Jun 05", "NFP / Jobs", "NFP", dt_utc(2026, 6, 5, 12, 30)),
    NewsEvent("Jun 10", "CPI", "CPI", dt_utc(2026, 6, 10, 12, 30)),
    NewsEvent("Jun 11", "PPI", "PPI", dt_utc(2026, 6, 11, 12, 30)),
    NewsEvent("Jun 16", "Import / Export Prices", "Inflation", dt_utc(2026, 6, 16, 12, 30)),
    NewsEvent("Jun 17", "Retail Sales", "Retail", dt_utc(2026, 6, 17, 12, 30)),
    NewsEvent("Jun 17", "FOMC Statement", "FOMC", dt_utc(2026, 6, 17, 18, 0)),
    NewsEvent("Jun 25", "PCE", "PCE", dt_utc(2026, 6, 25, 12, 30)),
    NewsEvent("Jun 30", "JOLTS", "JOLTS", dt_utc(2026, 6, 30, 14, 0)),
    NewsEvent("Jul 02", "NFP / Jobs", "NFP", dt_utc(2026, 7, 2, 12, 30)),
    NewsEvent("Jul 08", "FOMC Minutes", "FOMC", dt_utc(2026, 7, 8, 18, 0)),
    NewsEvent("Jul 14", "CPI", "CPI", dt_utc(2026, 7, 14, 12, 30)),
]

