"""What a buyer receives for a catalogue product: which EX5/SET and which inputs.

The selection mirrors the maintained installer's *Best Recommended* choice
(``Get-PortfolioItems`` in ``Install-BMTradingPortfolio.ps1``, read only):

* Safe-by-design items use their dedicated Safe SET, otherwise the SET plus the
  installer's Markov-gate overrides;
* Dynamic-by-design items use their recommended EX5/SET;
* everything else uses ``ExpertSource``/``SetSource``.

Inputs follow ``Get-EffectiveInputs`` for a single-chart buyer at the default
risk (1% per trade, news EAs 0.75% per pending side), without the owner's
account-size adaptive profile. Nothing here writes to the portfolio folder.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.catalog import INSTALLER_PATH, PACKAGE_ROOT, Product, get_sellable_catalog

NEWS_EXEMPT_LABELS = frozenset(
    {"News Pulse XAU", "News Pulse XAG", "News Pulse BTC", "News Pulse EURUSD", "Gold News V9 Direction"}
)
PERCENT_KEYS = ("InpRiskPercent", "InpMomentumRiskPercent", "InpContrarianRiskPercent", "InpAbsoluteRiskCapPercent")
MAGIC_RE = re.compile(r"^(?:Inp)?Magic(?:Number)?$", re.IGNORECASE)
DEFAULT_RISK_PERCENT = 1.0
NEWS_RISK_PERCENT = 0.75


@dataclass
class InstallerItem:
    label: str
    fields: dict[str, str] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)
    fixed_percent_risk: float = 0.0


def _string(block: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*=\s*'([^']*)'", block)
    return match.group(1) if match else ""


def _flag(block: str, name: str) -> bool:
    return bool(re.search(rf"\b{name}\s*=\s*\$true", block))


@lru_cache(maxsize=1)
def installer_items() -> dict[str, InstallerItem]:
    text = INSTALLER_PATH.read_text(encoding="utf-8-sig")
    start = text.index("$items = @(")
    end = text.index("\n    foreach ($item in $items)", start)
    blocks = re.findall(r"\[pscustomobject\]@\{(.*?)\n\s{8}\}(?:,|\s*$)", text[start:end], re.DOTALL | re.MULTILINE)
    items: dict[str, InstallerItem] = {}
    for block in blocks:
        label = _string(block, "Label")
        if not label:
            continue
        fields = {name: _string(block, name) for name in (
            "Canonical", "Expert", "ExpertSource", "SetSource", "SafeSetSource",
            "RecommendedExpertSource", "RecommendedSetSource")}
        if not fields["SetSource"] and re.search(r"\bSetSource\s*=\s*\$atrSet", block):
            fields["SetSource"] = "ATR Candle Breakout EA\\RETEST PASSED 2026-08-07 - ATR Candle Breakout - XAUUSD H1 - 1pct.set"
        flags = {name: _flag(block, name) for name in (
            "RecommendedSafe", "RecommendedDynamic", "ForceEnable", "PercentRisk", "LockRisk", "OptionalSymbol")}
        flags["SupportsSafeFilter"] = not bool(re.search(r"\bSupportsSafeFilter\s*=\s*\$false", block))
        risk = re.search(r"\bFixedPercentRisk\s*=\s*([0-9.]+)", block)
        period = re.search(r"\bPeriod\s*=\s*(\d+)", block)
        fields["Period"] = period.group(1) if period else "0"
        items[label] = InstallerItem(label, fields, flags, float(risk.group(1)) if risk else 0.0)
    return items


@dataclass
class Deliverable:
    product_slug: str
    label: str
    installer_label: str
    symbol: str
    period_minutes: int
    expert_path: Path
    set_path: Path
    mode: str  # standard | safe-set | safe-markov | dynamic
    inputs: "OrderedDict[str, str]"
    magic_input: str | None
    magic: int | None

    @property
    def source_path(self) -> Path:
        return self.expert_path.with_suffix(".mq5")

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_slug": self.product_slug,
            "label": self.label,
            "installer_label": self.installer_label,
            "symbol": self.symbol,
            "period_minutes": self.period_minutes,
            "expert_path": str(self.expert_path),
            "set_path": str(self.set_path),
            "mode": self.mode,
            "magic_input": self.magic_input,
            "magic": self.magic,
        }


def read_set_inputs(path: Path) -> "OrderedDict[str, str]":
    raw = path.read_bytes()
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
    inputs: OrderedDict[str, str] = OrderedDict()
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith((";", "#")):
            continue
        equals = trimmed.find("=")
        if equals < 1:
            continue
        key = trimmed[:equals].strip()
        value = trimmed[equals + 1:]
        separator = value.find("||")
        inputs[key] = value[:separator] if separator >= 0 else value
    return inputs


def _format_number(value: float) -> str:
    text = f"{value:.8f}".rstrip("0").rstrip(".")
    return text or "0"


def effective_inputs(item: InstallerItem, set_path: Path, *, safe_markov: bool) -> "OrderedDict[str, str]":
    inputs = read_set_inputs(set_path)
    label = item.label
    if label == "Nasdaq 5M Candle Momentum" and "InpRequireDIAgreement" in inputs:
        inputs["InpRequireDIAgreement"] = "true"
    if label == "News Pulse XAU":
        inputs["InpUseXauEventSpecific"] = "true"
    if label in {"News Pulse XAG", "News Pulse BTC", "News Pulse EURUSD"}:
        inputs["InpUseAssetEventSpecific"] = "true"
    if label.startswith("News Pulse "):
        inputs["InpEnableBuySide"] = "true"
        inputs["InpEnableSellSide"] = "true"
        inputs["InpUseDynamicTrailingSL"] = "false"
        inputs["InpResearchSession"] = "0"
        inputs["InpUseMarkovRegimeFilter"] = "false"
    if label in NEWS_EXEMPT_LABELS:
        inputs["InpAdaptivePortfolioControls"] = "false"
    if item.flags.get("ForceEnable") and "InpEnableTrading" in inputs:
        inputs["InpEnableTrading"] = "true"
    target = NEWS_RISK_PERCENT if label in NEWS_EXEMPT_LABELS else (item.fixed_percent_risk or DEFAULT_RISK_PERCENT)
    if item.flags.get("PercentRisk") and "InpRiskPercent" in inputs:
        inputs["InpRiskPercent"] = _format_number(target)
    if item.fixed_percent_risk > 0:
        for key in PERCENT_KEYS:
            if key in inputs:
                inputs[key] = _format_number(target)
    if safe_markov:
        inputs.update({
            "InpUseMarkovRegimeFilter": "true",
            "InpMarkovReturnWindow": "40",
            "InpMarkovThreshold": "0.05",
            "InpMarkovSignalGate": "0.05",
            "InpMarkovMinLabels": "252",
            "InpMarkovHistoryBars": "2600",
        })
    return inputs


def magic_of(inputs: dict[str, str]) -> tuple[str | None, int | None]:
    for key, value in inputs.items():
        if MAGIC_RE.match(key):
            try:
                return key, int(str(value).strip())
            except ValueError:
                return key, None
    return None, None


def deliverable_for(product: Product) -> Deliverable:
    items = installer_items()
    item = items.get(product.installer_label)
    if item is None:
        raise LookupError(f"{product.label}: no installer entry named {product.installer_label!r}")
    f, flags = item.fields, item.flags
    safe_by_design = flags["RecommendedSafe"]
    dynamic_by_design = (not safe_by_design) and flags["RecommendedDynamic"] and bool(f["RecommendedSetSource"])
    dedicated_safe = bool(f["SafeSetSource"]) and safe_by_design
    if dedicated_safe:
        set_rel, mode = f["SafeSetSource"], "safe-set"
    elif dynamic_by_design:
        set_rel, mode = f["RecommendedSetSource"], "dynamic"
    else:
        set_rel, mode = f["SetSource"], "standard"
    expert_rel = f["RecommendedExpertSource"] if dynamic_by_design and f["RecommendedExpertSource"] else f["ExpertSource"]
    safe_markov = safe_by_design and flags["SupportsSafeFilter"] and not dedicated_safe
    if safe_markov:
        mode = "safe-markov"
    expert_path = (PACKAGE_ROOT / expert_rel).resolve()
    set_path = (PACKAGE_ROOT / set_rel).resolve()
    inputs = effective_inputs(item, set_path, safe_markov=safe_markov)
    magic_input, magic = magic_of(inputs)
    return Deliverable(
        product_slug=product.slug,
        label=product.label,
        installer_label=product.installer_label,
        symbol=product.canonical or f["Canonical"],
        period_minutes=int(product.period_minutes or f["Period"] or 0),
        expert_path=expert_path,
        set_path=set_path,
        mode=mode,
        inputs=inputs,
        magic_input=magic_input,
        magic=magic,
    )


def sellable_products() -> list[Product]:
    return get_sellable_catalog()


def product_by_slug(slug: str) -> Product | None:
    return next((product for product in get_sellable_catalog() if product.slug == slug), None)
