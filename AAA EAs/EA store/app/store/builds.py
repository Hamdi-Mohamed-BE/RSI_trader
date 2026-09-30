"""Store builds: license-gated wrappers around the unchanged original EA sources.

For every distinct EA binary behind the sellable catalogue this writes

    data/store-builds/<Store EA name>.mq5   wrapper (#define-renamed callbacks)
    data/store-builds/src/src_<hash>.mqh    copies of the original include graph
    data/store-builds/CalyxLicense.mqh      the license module
    data/store-builds/<Store EA name>.ex5   compiled with the isolated MetaEditor
    data/store-builds/logs/<name>.log       compiler log (0 errors, 0 warnings required)
    data/store-builds/manifest.json         builds, products, magic numbers, hashes

The pattern is the one proven in ``FTMO Thirteen EA Deployment 2026-09-27/build_package.py``:
original sources are only read; copies are rewritten to resolve their quoted
includes inside the build folder. Original EA sources, EX5, SETs and the
installer are never modified.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import config
from .deliverables import Deliverable, deliverable_for, sellable_products

METAEDITOR = (config.STORE_ROOT.parent / "BM Trading Robust Sets 2026-08-04" / "_Backtests" / "MT5-DMC-20260811"
              / "metaeditor64.exe")
MANIFEST_NAME = "manifest.json"

CALLBACKS = {
    # name: (regex, wrapper signature, forwarding call)
    "OnTick": (r"\bvoid\s+OnTick\s*\(", "void OnTick()", "Store_StrategyTick()"),
    "OnTimer": (r"\bvoid\s+OnTimer\s*\(", "void OnTimer()", "Store_StrategyTimer()"),
    "OnDeinit": (r"\bvoid\s+OnDeinit\s*\(", "void OnDeinit(const int reason)", "Store_StrategyDeinit(reason)"),
    "OnTrade": (r"\bvoid\s+OnTrade\s*\(", "void OnTrade()", "Store_StrategyTrade()"),
    "OnTradeTransaction": (
        r"\bvoid\s+OnTradeTransaction\s*\(",
        "void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)",
        "Store_StrategyTradeTransaction(trans, request, result)",
    ),
    "OnChartEvent": (
        r"\bvoid\s+OnChartEvent\s*\(",
        "void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)",
        "Store_StrategyChartEvent(id, lparam, dparam, sparam)",
    ),
    "OnBookEvent": (r"\bvoid\s+OnBookEvent\s*\(", "void OnBookEvent(const string &symbol)", "Store_StrategyBookEvent(symbol)"),
}
MACRO_NAMES = {
    "OnInit": "Store_StrategyInit",
    "OnTick": "Store_StrategyTick",
    "OnTimer": "Store_StrategyTimer",
    "OnDeinit": "Store_StrategyDeinit",
    "OnTrade": "Store_StrategyTrade",
    "OnTradeTransaction": "Store_StrategyTradeTransaction",
    "OnChartEvent": "Store_StrategyChartEvent",
    "OnBookEvent": "Store_StrategyBookEvent",
}


def builds_root() -> Path:
    return Path(config.env("CALYX_STORE_BUILDS", str(config.BUILDS_ROOT)))


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def store_ea_name(expert_path: Path) -> str:
    stem = expert_path.stem
    stem = re.sub(r"^AAA Final\s+", "", stem)
    return stem if stem.lower().startswith("calyx") else f"Calyx {stem}"


def build_secret(build_id: str, key: bytes | None = None) -> str:
    """Per-build secret compiled into the EX5; derived, so it is never stored."""
    return hmac.new(key or config.license_secret(), f"calyx-build:{build_id}".encode(), hashlib.sha256).hexdigest()


def license_key_fingerprint(key: bytes | None = None) -> str:
    return hashlib.sha256(b"fingerprint:" + (key or config.license_secret())).hexdigest()[:16]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_source(path: Path) -> str:
    raw = path.read_bytes()
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
    return text.replace("\r\n", "\n")


# ------------------------------------------------------------------ manifest

@lru_cache(maxsize=4)
def _manifest_cached(path: str, mtime: float) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    path = (root or builds_root()) / MANIFEST_NAME
    if not path.is_file():
        return {"builds": {}, "products": {}}
    return _manifest_cached(str(path), path.stat().st_mtime)


def product_build(slug: str, root: Path | None = None) -> dict[str, Any] | None:
    manifest = load_manifest(root)
    product = manifest.get("products", {}).get(slug)
    if not product:
        return None
    build = manifest.get("builds", {}).get(product.get("build_id"))
    if not build:
        return None
    return {"product": product, "build": build}


def build_ex5_path(build: dict[str, Any], root: Path | None = None) -> Path:
    return (root or builds_root()) / build["ex5"]


# ------------------------------------------------------------------ generation

@dataclass
class BuildPlan:
    build_id: str
    name: str
    expert_path: Path
    source_path: Path
    deliverables: list[Deliverable] = field(default_factory=list)


def plan_builds(products=None) -> list[BuildPlan]:
    products = products if products is not None else sellable_products()
    plans: dict[Path, BuildPlan] = {}
    for product in products:
        item = deliverable_for(product)
        key = item.expert_path
        if key not in plans:
            name = store_ea_name(key)
            plans[key] = BuildPlan(slugify(name), name, key, item.source_path)
        plans[key].deliverables.append(item)
    ids = [plan.build_id for plan in plans.values()]
    duplicates = {bid for bid in ids if ids.count(bid) > 1}
    if duplicates:
        raise RuntimeError(f"Store build id collision: {sorted(duplicates)}")
    return list(plans.values())


class GraphCopier:
    """Copy an include graph into ``out/src`` with quoted includes rewritten to the copies."""

    def __init__(self, out: Path) -> None:
        self.out = out
        self.src = out / "src"
        self.src.mkdir(parents=True, exist_ok=True)
        self.names: dict[Path, str] = {}
        self.hashes: dict[str, str] = {}

    def copy(self, path: Path) -> str:
        path = path.resolve()
        if path in self.names:
            return self.names[path]
        if not path.is_file():
            raise FileNotFoundError(path)
        name = "src_" + hashlib.sha256(str(path).lower().encode("utf-8")).hexdigest()[:12] + ".mqh"
        self.names[path] = name
        self.hashes[str(path)] = sha256_file(path)
        text = read_source(path)
        if re.search(r"^\s*#resource\b", text, re.MULTILINE):
            raise RuntimeError(f"{path}: #resource directives are not supported by the store build")

        def rewrite(match: re.Match[str]) -> str:
            target = path.parent / match.group(1).replace("\\", "/")
            return '#include "' + self.copy(target) + '"'

        text = re.sub(r'#include\s+"([^"]+)"', rewrite, text)
        (self.src / name).write_text(text, encoding="utf-8")
        return name

    def expanded(self, name: str, seen: set[str] | None = None) -> str:
        seen = set() if seen is None else seen
        if name in seen:
            return ""
        seen.add(name)
        text = (self.src / name).read_text(encoding="utf-8")
        return text + "\n" + "\n".join(self.expanded(child, seen) for child in re.findall(r'#include "(src_[^"]+)"', text))


def wrapper_source(plan: BuildPlan, include_name: str, code: str, magic_input: str, activation_url: str,
                   secret: str) -> tuple[str, dict[str, bool]]:
    if not re.search(r"\bint\s+OnInit\s*\(", code):
        raise RuntimeError(f"{plan.name}: no OnInit found")
    present = {name: bool(re.search(spec[0], code)) for name, spec in CALLBACKS.items()}
    if not re.search(rf"\bs?input\b[^;\n]*\b{re.escape(magic_input)}\b", code):
        raise RuntimeError(f"{plan.name}: magic input {magic_input} not declared in the source graph")
    origin = re.match(r"^(https?://[^/]+)", activation_url)
    macros = ["OnInit"] + [name for name, found in present.items() if found]
    lines = [
        "// Calyx store build — GENERATED by tools/build_store_eas.py. Do not edit.",
        f"// Original strategy source (unchanged, copied include graph): {plan.source_path.name}",
        "#property strict",
        f'#define CALYX_BUILD_ID "{plan.build_id}"',
        f'#define CALYX_BUILD_SECRET "{secret}"',
        f'#define CALYX_LICENSE_URL "{activation_url}"',
        f'#define CALYX_LICENSE_ORIGIN "{origin.group(1) if origin else activation_url}"',
        '#include "CalyxLicense.mqh"',
    ]
    lines += [f"#define {name} {MACRO_NAMES[name]}" for name in macros]
    lines.append(f'#include "src/{include_name}"')
    lines += [f"#undef {name}" for name in macros]
    lines += [
        "",
        f"long CalyxStoreMagic() {{ return (long){magic_input}; }}",
        "",
        "int CalyxStoreStart()",
        "  {",
        "   EventKillTimer();",
        "   int calyxRc = Store_StrategyInit();",
        "   if(calyxRc != INIT_SUCCEEDED)",
        "     {",
        '      Print("Calyx store build: strategy initialisation failed (code ", calyxRc, ").");',
        "      ExpertRemove();",
        "      return calyxRc;",
        "     }",
        "   CalyxMarkStrategyReady();",
        "   return calyxRc;",
        "  }",
        "",
        "bool CalyxStorePulse()",
        "  {",
        "   if(CalyxLicensePulse() != CALYX_RESULT_ALLOWED)",
        "      return false;",
        "   if(!CalyxStrategyReady() && CalyxStoreStart() != INIT_SUCCEEDED)",
        "      return false;",
        "   return true;",
        "  }",
        "",
        "int OnInit()",
        "  {",
        "   if(CalyxIsTester())",
        "      return Store_StrategyInit();",
        "   int calyxInitState = CalyxLicenseInit(CalyxStoreMagic());",
        "   if(calyxInitState == CALYX_RESULT_DENIED)",
        "      return INIT_FAILED;",
        "   if(calyxInitState == CALYX_RESULT_ALLOWED)",
        "      return CalyxStoreStart();",
        "   EventSetTimer(60);",
        "   return INIT_SUCCEEDED;",
        "  }",
        "",
    ]
    tick_call = "Store_StrategyTick();" if present["OnTick"] else ""
    lines += [
        "void OnTick()",
        "  {",
        "   if(CalyxIsTester())",
        "     {",
        f"      {tick_call}",
        "      return;",
        "     }",
        "   if(CalyxStorePulse())",
        "     {",
        f"      {tick_call}",
        "     }",
        "  }",
        "",
    ]
    timer_call = "Store_StrategyTimer();" if present["OnTimer"] else ""
    lines += [
        "void OnTimer()",
        "  {",
        "   if(CalyxIsTester())",
        "     {",
        f"      {timer_call}",
        "      return;",
        "     }",
        "   if(CalyxStorePulse())",
        "     {",
        f"      {timer_call}",
        "     }",
        "  }",
        "",
    ]
    for name in ("OnDeinit", "OnTrade", "OnTradeTransaction", "OnChartEvent", "OnBookEvent"):
        if not present[name]:
            continue
        signature, call = CALLBACKS[name][1], CALLBACKS[name][2]
        lines += [
            signature,
            "  {",
            "   if(CalyxIsTester() || CalyxStrategyReady())",
            f"      {call};",
            "  }",
            "",
        ]
    return "\n".join(lines) + "\n", present


def compile_mq5(mq5: Path, log: Path, metaeditor: Path = METAEDITOR, timeout: int = 180) -> tuple[bool, str]:
    log.parent.mkdir(parents=True, exist_ok=True)
    if log.exists():
        log.unlink()
    subprocess.run(f'"{metaeditor}" /portable /compile:"{mq5}" /log:"{log}"', timeout=timeout,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if not log.exists():
        return False, "no compiler log written"
    report = read_source(log)
    ok = bool(re.search(r"\b0 errors?, 0 warnings?", report)) and mq5.with_suffix(".ex5").exists()
    return ok, report


def build_all(*, compile_eas: bool = True, only: set[str] | None = None, activation_url: str | None = None,
              out: Path | None = None, metaeditor: Path = METAEDITOR, log=print) -> dict[str, Any]:
    out = out or builds_root()
    out.mkdir(parents=True, exist_ok=True)
    activation_url = activation_url or config.DEFAULT_ACTIVATION_URL
    shutil.copyfile(config.MQL_TEMPLATE_ROOT / "CalyxLicense.mqh", out / "CalyxLicense.mqh")
    previous = load_manifest(out)
    copier = GraphCopier(out)
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "activation_url": activation_url,
        "license_key_fingerprint": license_key_fingerprint(),
        "license_module_sha256": sha256_file(out / "CalyxLicense.mqh"),
        "compiler": str(metaeditor),
        "builds": dict(previous.get("builds", {})),  # keep superseded builds: older buyer installs stay valid
        "products": {},
        "failures": [],
    }
    for build in manifest["builds"].values():
        build["current"] = False
    for plan in plan_builds():
        magic_inputs = {d.magic_input for d in plan.deliverables}
        if len(magic_inputs) != 1 or None in magic_inputs:
            manifest["failures"].append({"build": plan.build_id, "error": f"magic input not unique: {magic_inputs}"})
            continue
        magic_input = magic_inputs.pop()
        include = copier.copy(plan.source_path)
        code = copier.expanded(include)
        graph_hash = hashlib.sha256("".join(sorted(copier.hashes.get(str(p), "") for p in _graph_paths(copier, include))).encode()).hexdigest()
        version_id = f"{plan.build_id}-{graph_hash[:8]}"
        secret = build_secret(version_id)
        wrapper, present = wrapper_source(
            BuildPlan(version_id, plan.name, plan.expert_path, plan.source_path, plan.deliverables),
            include, code, magic_input, activation_url, secret)
        mq5 = out / f"{plan.name}.mq5"
        mq5.write_text(wrapper, encoding="utf-8")
        entry = {
            "build_id": version_id,
            "family": plan.build_id,
            "name": plan.name,
            "ex5": f"{plan.name}.ex5",
            "wrapper": mq5.name,
            "original_source": str(plan.source_path),
            "original_source_sha256": sha256_file(plan.source_path),
            "original_ex5": str(plan.expert_path),
            "original_ex5_sha256": sha256_file(plan.expert_path) if plan.expert_path.exists() else None,
            "graph_sha256": graph_hash,
            "magic_input": magic_input,
            "callbacks": sorted(name for name, found in present.items() if found),
            "products": [d.product_slug for d in plan.deliverables],
            "compiled": False,
            "current": True,
            "activation_url": activation_url,
        }
        selected = only is None or plan.build_id in only or version_id in only
        ex5 = mq5.with_suffix(".ex5")
        if compile_eas and selected:
            ok, report = compile_mq5(mq5, out / "logs" / f"{plan.name}.log", metaeditor)
            summary = next((line.strip() for line in report.splitlines() if "error" in line.lower() and "warning" in line.lower()), "")
            entry["compile_result"] = summary
            if not ok:
                problems = [line.strip() for line in report.splitlines() if (" error " in line.lower() or " warning " in line.lower() or ": error" in line.lower() or ": warning" in line.lower())]
                manifest["failures"].append({"build": version_id, "error": summary or "compile failed", "details": problems[:20]})
                log(f"FAILED {plan.name}: {summary}")
            else:
                log(f"BUILT  {plan.name} ({version_id})")
        prior = previous.get("builds", {}).get(version_id, {})
        if ex5.exists() and (compile_eas and selected and not any(f["build"] == version_id for f in manifest["failures"])
                             or (prior.get("compiled") and prior.get("ex5_sha256") == sha256_file(ex5))):
            entry["compiled"] = True
            entry["ex5_sha256"] = sha256_file(ex5)
            entry["compile_result"] = entry.get("compile_result") or prior.get("compile_result", "")
        manifest["builds"][version_id] = entry
        for item in plan.deliverables:
            set_text = "\n".join(f"{key}={value}" for key, value in item.inputs.items())
            manifest["products"][item.product_slug] = {
                "build_id": version_id,
                "label": item.label,
                "symbol": item.symbol,
                "period_minutes": item.period_minutes,
                "mode": item.mode,
                "magic_input": item.magic_input,
                "magic": item.magic,
                "set_source": str(item.set_path),
                "set_source_sha256": sha256_file(item.set_path),
                "inputs_sha256": hashlib.sha256(set_text.encode("utf-8")).hexdigest(),
                "inputs": dict(item.inputs),
            }
    manifest["source_hashes"] = copier.hashes
    (out / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _manifest_cached.cache_clear()
    return manifest


def _graph_paths(copier: GraphCopier, include: str) -> list[str]:
    reverse = {name: str(path) for path, name in copier.names.items()}
    names: list[str] = []
    stack = [include]
    while stack:
        name = stack.pop()
        if name in names:
            continue
        names.append(name)
        stack.extend(re.findall(r'#include "(src_[^"]+)"', (copier.src / name).read_text(encoding="utf-8")))
    return [reverse[name] for name in names if name in reverse]
