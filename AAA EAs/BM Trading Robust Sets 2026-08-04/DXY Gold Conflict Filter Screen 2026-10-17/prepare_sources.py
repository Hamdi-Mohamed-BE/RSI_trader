"""Audit and copy frozen native gold signal rows; never connects to MT5.

This does not evaluate a DXY filter or select trades by their outcomes.  It
preserves the already-published unit-risk ledger and validates its accounting
against the historical native position/deal receipts before an analysis freeze.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
SOURCE = BASE / "Portfolio Long History All ORB05 2026-10-14"
EXPECTED = {
    "ema3": 207,
    "orb-volume-profile": 304,
    "orb-volume-profile-volume-confirmed": 119,
    "xau-orb-new-york-m30": 79,
    "xau-orb-london-ny-overlap-m30": 121,
}
CONTRACT = 100.0  # Frozen source XAUUSD contract: USD per $1 move per 1 lot.
SIZING_OR_AUDIT = {
    "InpRiskPercent", "InpGridRiskPercent", "InpAdaptivePortfolioControls",
    "InpRR05AuditTag", "FTMOExpectedLogin", "FTMOExpectedServer",
    "FTMOExpectedSymbol", "FTMOPhase", "FTMOAllocationMode", "FTMOAllocationValue",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def equal(a, b):
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-8)
    except (ValueError, TypeError):
        return str(a).lower() == str(b).lower()


def number(value):
    assert isinstance(value, (float, int)) and not isinstance(value, bool)
    assert math.isfinite(value)
    return float(value)


def close(a, b, tol=1e-7):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=tol), (a, b)


def presets(path):
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    return {k.strip(): v.split("||", 1)[0].strip()
            for line in text.splitlines() if "=" in line and not line.lstrip().startswith((";", "#"))
            for k, v in [line.split("=", 1)]}


def main():
    plan = read(ROOT / "PLAN.json")
    assert plan["scope"] == list(EXPECTED)
    source_plan = read(SOURCE / "PLAN.json")
    state = read(SOURCE / "RUN_STATUS.json")
    published = read(SOURCE / "RISK_ROWS.json")["full-eas"]
    hashes = {}

    def receipt(path, expected_sha=None):
        path = Path(path).resolve()
        value = sha(path)
        assert expected_sha is None or value.lower() == expected_sha.lower(), str(path)
        hashes[str(path)] = value
        return path

    for name in ("PLAN.json", "RUN_STATUS.json", "RISK_ROWS.json"):
        receipt(SOURCE / name)
    receipt(BASE / "Portfolio Long History 2026-10-08" / "publish.py")
    receipt(__file__)
    rows, sources, excluded = [], {}, []
    for key, expected_count in EXPECTED.items():
        case_id = source_plan["mappings"]["full-eas"][key]
        definition = next(c for c in source_plan["cases"] if c["case_id"] == case_id)
        saved = state["complete"][case_id]
        assert saved["verified_same_active_inputs"] and saved["source_closure_identical"] and saved["active_inputs_reconciled"]
        path = receipt(saved["path"], saved["sha256"])
        native = read(path)
        folder = path.parent
        manifest = read(receipt(folder / "manifest.json"))
        deal_path = receipt(folder / "deals.csv")
        receipt(folder / "inputs.set")
        receipt(definition["preset"])
        receipt(definition["source"])
        for production, expected_sha in definition["production_hashes"].items():
            receipt(production, expected_sha)
        declared_defaults, enum_values = {}, {}
        for production in definition["production_hashes"]:
            if Path(production).suffix.lower() in (".mq5", ".mqh"):
                raw = Path(production).read_bytes()
                text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
                text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
                for body in re.findall(r"\benum\s+\w+\s*\{([^}]+)\}", text):
                    next_value = 0
                    for item in body.split(","):
                        match = re.fullmatch(r"\s*(\w+)\s*(?:=\s*(-?\d+))?\s*", item)
                        if match:
                            name, literal = match.groups()
                            if literal is not None:
                                next_value = int(literal)
                            enum_values[name] = next_value
                            next_value += 1
                for name, value in re.findall(r"\binput\s+\w+\s+(\w+)\s*=\s*([^;]+);", text):
                    declared_defaults[name] = value.strip().strip('"')
        declared_defaults = {name: enum_values.get(value, value) for name, value in declared_defaults.items()}
        assert native["slug"] == key and native["window"] == ["2021.10.06", "2026.10.06"]
        assert native["no_live_changes"] and manifest["symbol"] == "XAUUSD"
        assert not any(native["flags"].values())
        manifest_diffs = {k: [manifest["inputs"].get(k), native["inputs"].get(k)]
                          for k in set(manifest["inputs"]) | set(native["inputs"])
                          if not equal(manifest["inputs"].get(k), native["inputs"].get(k))}
        # The historical parser removes inactive FTMO placeholders and adds
        # supported production defaults absent from the original .set manifest.
        for k, (before, after) in manifest_diffs.items():
            if k in SIZING_OR_AUDIT:
                continue
            intended = definition["input_settings"].get(k, declared_defaults.get(k))
            assert before is None and intended is not None and equal(after, intended), (k, before, after, intended)
        assert manifest["build"]["binary_sha256"] == native["binary_sha256"]
        strategy_diffs = {k: [v, native["inputs"].get(k)] for k, v in definition["input_settings"].items()
                          if not equal(v, native["inputs"].get(k))}
        assert set(strategy_diffs) <= SIZING_OR_AUDIT, strategy_diffs
        current_preset = presets(definition["preset"])
        preset_diffs = {k: [v, native["inputs"].get(k)] for k, v in current_preset.items()
                        if not equal(v, native["inputs"].get(k))}
        assert set(preset_diffs) <= SIZING_OR_AUDIT, preset_diffs
        with deal_path.open(newline="", encoding="utf-8-sig") as handle:
            deal_rows = list(csv.DictReader(handle))
        by_position = {}
        for d in deal_rows:
            by_position.setdefault(int(d["position_id"]), []).append(d)
        position_map = {int(t["position_id"]): t for t in native["trades"]}
        assert len(position_map) == len(native["trades"])
        natural = {}
        for pid, t in position_map.items():
            if any("end of test" in c.lower() for c in t["exit_comments"]):
                excluded.append(dict(key=key, position_id=pid, open_epoch=t["open_epoch"],
                                     native_close_epoch=t["close_epoch"], reason="Native forced final liquidation; not a natural closed trade"))
            else:
                natural[pid] = t
        selected = [r for r in published if r["key"] == key]
        assert len(selected) == expected_count and {r["position_id"] for r in selected} == set(natural)
        assert len({(r["key"], r["position_id"]) for r in selected}) == len(selected)
        prior_close = -1
        for row in sorted(selected, key=lambda r: (r["op"], r["position_id"])):
            t = natural[int(row["position_id"])]
            assert row["symbol"] == "XAUUSD" and row["side"] in ("Long", "Short")
            assert row["side"] == t["side"] and row["partial"] is False and row["order_compatible"] is True
            assert t["partial"] is False and t["exit_legs"] == 1
            assert row["risk_reference"] == "filled initial stop" and row["news"] is False
            assert int(row["op"]) == row["op"] < row["cl"] == int(row["cl"])
            assert row["op"] >= prior_close, (key, "within-EA overlap")
            prior_close = row["cl"]
            for field in ("unit_risk", "unit_gross", "unit_comm", "unit_swap", "open_price", "close_price", "risk_weight"):
                number(row[field])
            assert row["unit_risk"] > 0 and row["risk_weight"] == 1.0
            close(row["op"], t["open_epoch"]); close(row["cl"], t["close_epoch"])
            close(row["open_price"], t["open_price"]); close(row["close_price"], t["close_price"])
            vol = number(t["volume"])
            assert vol > 0 and t["sl"] > 0
            assert (t["sl"] < t["open_price"]) if t["side"] == "Long" else (t["sl"] > t["open_price"])
            close(row["unit_risk"], abs(t["open_price"] - t["sl"]) * CONTRACT)
            close(row["unit_gross"] * vol, t["gross"])
            close(row["unit_comm"] * vol, t["commission"] + t.get("fee", 0))
            close(row["unit_swap"] * vol, t["swap"])
            close((row["unit_gross"] + row["unit_comm"] + row["unit_swap"]) * vol, t["net"], .011)
            deals = by_position[int(row["position_id"])]
            entries = [d for d in deals if int(d["entry"]) == 0]
            exits = [d for d in deals if int(d["entry"]) == 1]
            assert len(entries) == len(exits) == 1 and len(deals) == 2
            entry, exit_ = entries[0], exits[0]
            assert int(entry["type"]) == (0 if row["side"] == "Long" else 1)
            assert int(exit_["type"]) == (1 if row["side"] == "Long" else 0)
            close(float(entry["epoch"]), row["op"]); close(float(exit_["epoch"]), row["cl"])
            close(float(entry["sl"]), t["sl"]); close(float(entry["price"]), row["open_price"])
            close(float(exit_["price"]), row["close_price"])
            close(float(entry["volume"]), vol); close(float(exit_["volume"]), vol)
            for field in ("gross", "commission", "swap", "fee"):
                close(math.fsum(float(d[field]) for d in deals), t[field], .011)
        rows.extend(selected)  # Original rows unchanged; no risk or outcome selection.
        sources[key] = dict(case_id=case_id, native_result=str(path), native_manifest=str(folder / "manifest.json"),
                            native_deals=str(deal_path), current_source=definition["source"], current_preset=definition["preset"],
                            current_inputs=current_preset, native_inputs=native["inputs"], native_period=manifest["period"],
                            history_quality=native["native"]["history_quality"], tick_notes=native["tick_notes"],
                            native_positions=len(native["trades"]), natural_closed_rows=len(selected),
                            inactive_manifest_input_differences=manifest_diffs,
                            sizing_or_audit_input_differences=strategy_diffs, preset_sizing_or_audit_differences=preset_diffs,
                            source_receipt=saved)
    assert len(rows) == sum(EXPECTED.values()) == 830
    assert len(excluded) == 1 and excluded[0]["key"] == "ema3"
    output = dict(version=1, rows=rows, metadata=dict(source_collection="full-eas", source_window=["2021-10-06", "2026-10-06"],
                  collection_path=str(SOURCE / "RISK_ROWS.json"), native_symbol="XAUUSD", contract_size=CONTRACT,
                  normalization_reference="Source publisher unit_risk = abs(native filled open minus opening-order SL) * 100 USD per price unit per 1 lot; gross, commission+fee, swap divided by native filled lot volume.",
                  preserves_published_rows=True, live_changes=False, no_filter_outcomes_evaluated=True),
                  sources=sources, source_hashes=hashes, exclusions=excluded)
    audit = dict(status="PASS", validated_rows=len(rows), counts=EXPECTED,
                 native_positions_reconciled=len(rows), native_deals_reconciled=2 * len(rows),
                 initial_stop_normalizations_checked=len(rows),
                 source_file_count=len(hashes), exclusions=excluded, all_rows_unique=True,
                 no_within_ea_overlaps=True, no_partials=True, finite_positive_initial_stop_risk=True,
                 opening_stop_direction_valid=True, native_deals_and_position_costs_reconciled=True,
                 current_production_closure_hashes_match_frozen_source_plan=True,
                 no_filter_outcomes_evaluated=True, no_live_changes=True)
    for name, value in (("INPUTS.json", output), ("SOURCE AUDIT.json", audit)):
        encoded = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        target = ROOT / name
        if (ROOT / "FROZEN.json").exists():
            assert target.exists() and target.read_text(encoding="utf-8") == encoded, "Refusing to change frozen input artifact"
        else:
            target.write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": "PASS", "rows": len(rows), "counts": EXPECTED,
                      "native_deals_reconciled": 2 * len(rows), "source_files": len(hashes),
                      "excluded_native_final_liquidations": len(excluded)}))


if __name__ == "__main__":
    main()
