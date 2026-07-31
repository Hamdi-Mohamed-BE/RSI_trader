from __future__ import annotations

import csv
import math
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np

from macro_regime import MacroRegimeStore, feature_names as macro_feature_names
from news_core import ROOT


USMPD_SURPRISES = (
    ROOT / "data" / "monetary-policy-surprises" / "mps.csv"
)


@dataclass(frozen=True)
class PolicySurprise:
    released: date
    statement: float | None
    press_conference: float | None
    monetary_event: float | None


def _number(value: str | None) -> float | None:
    if value in (None, "", "NA"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _release_date(value: str | datetime | date) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def policy_feature_names() -> tuple[str, ...]:
    names = [
        "policy_last_statement",
        "policy_last_press",
        "policy_last_meeting",
    ]
    for field in ("statement", "press", "meeting"):
        names.extend(
            (
                f"policy_{field}_mean_3",
                f"policy_{field}_mean_6",
                f"policy_{field}_mean_12",
                f"policy_{field}_std_6",
                f"policy_{field}_hawkish_share_6",
            )
        )
    names.extend(
        (
            "policy_previous_statement_press_reversal",
            "policy_days_since_previous_meeting",
            "policy_short_gap",
            "policy_sep_meeting",
            "policy_month_sin",
            "policy_month_cos",
        )
    )
    return tuple(names)


class FomcRegimeStore:
    def __init__(
        self,
        surprises_path: Path = USMPD_SURPRISES,
        *,
        refresh_macro: bool = False,
    ) -> None:
        if not surprises_path.exists():
            raise FileNotFoundError(
                "SF Fed monetary-policy surprises are missing. Download the "
                "official archive into data/monetary-policy-surprises."
            )
        rows: list[PolicySurprise] = []
        with surprises_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    PolicySurprise(
                        released=date.fromisoformat(row["Date"]),
                        statement=_number(row.get("STMT")),
                        press_conference=_number(row.get("PC")),
                        monetary_event=_number(row.get("ME")),
                    )
                )
        rows.sort(key=lambda item: item.released)
        self.rows = tuple(rows)
        self.dates = tuple(row.released for row in rows)
        self.by_date = {row.released: row for row in rows}
        self.macro = MacroRegimeStore(refresh=refresh_macro)

    def surprise(self, release: str | datetime | date) -> PolicySurprise | None:
        return self.by_date.get(_release_date(release))

    def statement_gold_label(
        self,
        release: str | datetime | date,
        *,
        neutral_threshold: float = 0.0,
    ) -> str | None:
        row = self.surprise(release)
        if row is None or row.statement is None:
            return None
        if abs(row.statement) <= neutral_threshold:
            return None
        return "NEGATIVE" if row.statement > 0 else "POSITIVE"

    @staticmethod
    def _series(
        rows: list[PolicySurprise],
        field: str,
    ) -> list[float]:
        values = [getattr(row, field) for row in rows]
        return [float(value) for value in values if value is not None]

    @staticmethod
    def _summary(values: list[float]) -> list[float]:
        if not values:
            return [0.0] * 5
        recent_3 = values[-3:]
        recent_6 = values[-6:]
        recent_12 = values[-12:]
        return [
            float(np.mean(recent_3)),
            float(np.mean(recent_6)),
            float(np.mean(recent_12)),
            float(np.std(recent_6)),
            float(np.mean([value > 0 for value in recent_6])),
        ]

    def policy_features(
        self,
        release: str | datetime | date,
    ) -> list[float]:
        released = _release_date(release)
        index = bisect_left(self.dates, released)
        prior = list(self.rows[:index])
        if not prior:
            return [0.0] * len(policy_feature_names())

        previous = prior[-1]
        output = [
            float(previous.statement or 0.0),
            float(previous.press_conference or 0.0),
            float(previous.monetary_event or 0.0),
        ]
        for field in (
            "statement",
            "press_conference",
            "monetary_event",
        ):
            output.extend(self._summary(self._series(prior, field)))

        reversal = (
            previous.statement is not None
            and previous.press_conference is not None
            and previous.statement * previous.press_conference < 0
        )
        days_since = float((released - previous.released).days)
        angle = 2 * math.pi * (released.month - 1) / 12
        output.extend(
            (
                float(reversal),
                min(days_since, 180.0) / 180.0,
                float(days_since < 28),
                float(released.month in {3, 6, 9, 12}),
                math.sin(angle),
                math.cos(angle),
            )
        )
        return output

    def features(self, release: str | datetime | date) -> list[float]:
        return [
            *self.policy_features(release),
            *self.macro.features(
                release.isoformat()
                if isinstance(release, datetime)
                else f"{_release_date(release).isoformat()}T18:00:00+00:00"
            ),
        ]


def regime_feature_names() -> tuple[str, ...]:
    return (*policy_feature_names(), *macro_feature_names())
