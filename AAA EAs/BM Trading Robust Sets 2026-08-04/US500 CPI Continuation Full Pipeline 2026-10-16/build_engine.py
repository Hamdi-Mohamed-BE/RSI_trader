"""Embed explicitly frozen CPI dates and bounded continuation-only research cases."""
from pathlib import Path
import json
import math

R = Path(__file__).resolve().parent
FIELDS = ("hold_minutes", "target_r", "entry_window_minutes", "impulse_mult", "close_fraction")
BOUNDS = {
    "hold_minutes": (2, 45),
    "target_r": (0.25, 4),
    "entry_window_minutes": (2, 10),
    "impulse_mult": (0.5, 2),
    "close_fraction": (0.1, 0.4),
}


def build(cases):
    assert cases, "At least one explicitly declared case is required"
    for case in cases:
        assert set(case) == set(FIELDS), "Only the five declared parameters may vary"
        for field in FIELDS:
            value = case[field]
            assert type(value) in (int, float) and math.isfinite(value)
            lo, hi = BOUNDS[field]
            assert lo <= value <= hi, (field, value, lo, hi)
        assert float(case["hold_minutes"]).is_integer()
        assert float(case["entry_window_minutes"]).is_integer()
    events = json.loads((R / "calendar.json").read_text(encoding="utf-8"))["events"]
    assert events, "An explicit release calendar is mandatory"
    assert all(type(event["epoch"]) is int and event["epoch"] > 0 for event in events)
    assert all(event["epoch"] % 60 == 0 for event in events), "Release-aligned M1 timestamps required"
    assert all(event["kind"] == "CPI" for event in events), "Continuation experiment remains CPI only"
    epochs = [event["epoch"] for event in events]
    assert epochs == sorted(set(epochs)), "Calendar must be chronological and unique"
    assert all(b - a > 3600 for a, b in zip(epochs, epochs[1:])), "Overlapping event windows"
    header = "double Cases[][5]={" + ",".join(
        "{" + ",".join(repr(case[field]) for field in FIELDS) + "}"
        for case in cases
    ) + "};\n"
    header += "long Events[]={" + ",".join(str(epoch) for epoch in epochs) + "};\n"
    header += "string Kinds[]={" + ",".join(json.dumps(event["kind"]) for event in events) + "};\n"
    return header + (R / "engine.mq5").read_text(encoding="utf-8")


def support(folder):
    """No external libraries, DLLs, includes, or mutable signal files are needed."""
    pass
