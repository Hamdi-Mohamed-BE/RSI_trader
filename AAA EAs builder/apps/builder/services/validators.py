import re
from dataclasses import dataclass

from django.utils.text import slugify

from apps.builder.models import CodeVersion, Project


@dataclass(frozen=True)
class ValidationOutcome:
    source_code: str
    status: str
    diagnostics: list[dict[str, str]]
    language: str
    filename: str


def strip_markdown_fences(source_code: str) -> str:
    source = source_code.strip().lstrip("\ufeff")
    match = re.fullmatch(r"```(?:[\w+#.-]+)?\s*\n(.*)\n```", source, flags=re.DOTALL)
    return match.group(1).strip() if match else source


def _diagnostic(level: str, code: str, message: str) -> dict[str, str]:
    return {"severity": level, "code": code, "message": message}


def _check_balanced(source: str, opening: str, closing: str, name: str) -> list[dict[str, str]]:
    if source.count(opening) == source.count(closing):
        return []
    return [_diagnostic("error", "unbalanced-syntax", f"Unbalanced {name} detected.")]


def _validate_common(source: str) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    if len(source) < 300:
        diagnostics.append(
            _diagnostic("error", "source-too-short", "The generated source is incomplete.")
        )
    if re.search(r"\b(TODO|FIXME|YOUR[_ ]CODE|IMPLEMENT[_ ]HERE)\b", source, re.IGNORECASE):
        diagnostics.append(
            _diagnostic("error", "placeholder", "The source contains an unfinished placeholder.")
        )
    if "\x00" in source:
        diagnostics.append(_diagnostic("error", "null-byte", "The source contains a null byte."))
    diagnostics.extend(_check_balanced(source, "{", "}", "braces"))
    diagnostics.extend(_check_balanced(source, "(", ")", "parentheses"))
    return diagnostics


def _validate_mql5(
    source: str, artifact_type: str, project_description: str
) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    required = ["#property strict", "OnInit"]
    if artifact_type == Project.ArtifactType.MT5_EA:
        required.append("OnTick")
        if not re.search(r"\b(CTrade|OrderSend)\b", source):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "no-trade-api",
                    "No CTrade or OrderSend usage was detected in this Expert Advisor.",
                )
            )
        if re.search(r"\brisk\b|\bpercent\b|%", project_description, re.IGNORECASE):
            if "OrderCalcProfit" not in source:
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "risk-currency-conversion",
                        "Risk-based MQL5 sizing must use OrderCalcProfit for "
                        "account-currency loss.",
                    )
                )
        if (
            re.search(r"\btrade\.(Buy|Sell)\s*\(", source)
            and "SYMBOL_TRADE_STOPS_LEVEL" not in source
        ):
            diagnostics.append(
                _diagnostic(
                    "error",
                    "broker-stop-level",
                    "Order prices must enforce the broker's SYMBOL_TRADE_STOPS_LEVEL.",
                )
            )
    else:
        required.append("OnCalculate")
        if "#property indicator_" not in source:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing-indicator-properties",
                    "The MT5 indicator has no indicator property declarations.",
                )
            )

    for marker in required:
        if marker not in source:
            diagnostics.append(
                _diagnostic(
                    "error", "missing-entry-point", f"Required MQL5 marker missing: {marker}."
                )
            )

    prohibited = {
        r"#import\b": "DLL imports are not allowed.",
        r"\bWebRequest\s*\(": "Network requests are not allowed in generated code.",
        r"\bFile(Open|Write|Delete|Move)\s*\(": "Filesystem access is not allowed.",
    }
    for pattern, message in prohibited.items():
        if re.search(pattern, source, flags=re.IGNORECASE):
            diagnostics.append(_diagnostic("error", "prohibited-capability", message))
    return diagnostics


def _validate_pine(source: str, artifact_type: str) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    if not re.search(r"^\s*//@version=(5|6)\s*$", source, flags=re.MULTILINE):
        diagnostics.append(
            _diagnostic("error", "missing-version", "Pine Script must declare version 5 or 6.")
        )
    declaration = (
        "strategy(" if artifact_type == Project.ArtifactType.PINE_STRATEGY else "indicator("
    )
    if declaration not in source:
        diagnostics.append(
            _diagnostic(
                "error", "wrong-declaration", f"Pine source must contain {declaration} declaration."
            )
        )
    if re.search(
        r"request\.security\([^)]*,[^)]*,[^)]*lookahead\s*=\s*barmerge\.lookahead_on", source
    ):
        diagnostics.append(
            _diagnostic(
                "warning", "lookahead", "Look-ahead behavior may repaint historical signals."
            )
        )
    return diagnostics


def validate_source(project: Project, source_code: str) -> ValidationOutcome:
    source = strip_markdown_fences(source_code)
    diagnostics = _validate_common(source)
    is_mql5 = project.artifact_type in {
        Project.ArtifactType.MT5_EA,
        Project.ArtifactType.MT5_INDICATOR,
    }
    if is_mql5:
        diagnostics.extend(_validate_mql5(source, project.artifact_type, project.description))
        language = "mql5"
        extension = ".mq5"
    else:
        diagnostics.extend(_validate_pine(source, project.artifact_type))
        language = "pine-script"
        extension = ".pine"

    if any(item["severity"] == "error" for item in diagnostics):
        status = CodeVersion.ValidationStatus.FAILED
    elif diagnostics:
        status = CodeVersion.ValidationStatus.WARNINGS
    else:
        status = CodeVersion.ValidationStatus.PASSED

    safe_name = slugify(project.name).replace("-", "_") or "strategy"
    return ValidationOutcome(
        source_code=source,
        status=status,
        diagnostics=diagnostics,
        language=language,
        filename=f"{safe_name}{extension}",
    )
