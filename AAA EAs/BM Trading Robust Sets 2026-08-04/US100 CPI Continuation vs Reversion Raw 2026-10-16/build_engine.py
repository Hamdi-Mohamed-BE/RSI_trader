"""Embed the frozen CPI calendar and predeclared raw cases; never compile or launch."""
from pathlib import Path
import json

R = Path(__file__).resolve().parent


def build(cases):
    assert cases, "At least one explicitly declared case is required"
    for case in cases:
        assert set(case) == {"mode", "require_positive_spread"}
        assert type(case["mode"]) is int and case["mode"] in (0, 1, 2)
        assert type(case["require_positive_spread"]) is int
        assert case["require_positive_spread"] in (0, 1)
    events = json.loads((R / "calendar.json").read_text(encoding="utf-8"))["events"]
    assert events, "An explicit release calendar is mandatory"
    assert all(type(event["epoch"]) is int and event["epoch"] > 0 for event in events)
    assert all(event["epoch"] % 60 == 0 for event in events), "Release-aligned M1 timestamps required"
    assert all(event["kind"] == "CPI" for event in events), "This raw experiment is CPI only"
    epochs = [event["epoch"] for event in events]
    assert epochs == sorted(set(epochs)), "Calendar must be chronological and unique"
    assert all(b - a > 3600 for a, b in zip(epochs, epochs[1:])), "Overlapping event windows"
    header = "double Cases[][2]={" + ",".join(
        "{" + str(case["mode"]) + "," + str(case["require_positive_spread"]) + "}"
        for case in cases
    ) + "};\n"
    header += "long Events[]={" + ",".join(str(epoch) for epoch in epochs) + "};\n"
    header += "string Kinds[]={" + ",".join(json.dumps(event["kind"]) for event in events) + "};\n"
    return header + (R / "engine.mq5").read_text(encoding="utf-8")


def support(folder):
    """No external libraries, DLLs, includes, or mutable signal files are needed."""
    pass
