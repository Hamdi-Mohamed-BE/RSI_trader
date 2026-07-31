from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests

from fomc_pipeline import fomc_release_phases
from news_core import EVENTS, ROOT


ANALYSIS_DIR = ROOT / "release_analyses"
ALLOWED_SOURCE_HOSTS = {
    "bea.gov",
    "www.bea.gov",
    "bls.gov",
    "www.bls.gov",
    "federalreserve.gov",
    "www.federalreserve.gov",
    "census.gov",
    "www.census.gov",
}
GOLD_INVERSE_EVENTS = {"NFP", "GDP", "CPI", "PPI"}
FOMC_HAWKISH_PHRASES = {
    "inflation remains somewhat elevated": 1.5,
    "inflation remains elevated": 1.5,
    "economic activity has continued to expand at a solid pace": 0.5,
    "labor market conditions remain solid": 0.5,
    "attentive to the risks of inflation": 1.0,
}
FOMC_DOVISH_PHRASES = {
    "downside risks to employment have risen": 1.5,
    "job gains have slowed": 0.75,
    "unemployment rate has moved up": 0.75,
    "inflation has eased": 0.75,
    "reduce the target range": 1.5,
    "lower the target range": 1.5,
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "header", "footer", "form", "aside"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "header", "footer", "form", "aside"}:
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts.append(text)


def fetch_official_text(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_SOURCE_HOSTS:
        raise ValueError("Official source URL must be HTTPS and use an approved government domain.")
    response = requests.get(
        url,
        headers={"User-Agent": "Gold-News-AI/0.2"},
        timeout=25,
    )
    response.raise_for_status()
    parser = TextExtractor()
    parser.feed(response.text)
    return " ".join(parser.parts)[:24_000]


def numeric(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def deterministic_surprise(
    event: str,
    actual: str | float | None,
    forecast: str | float | None,
    previous: str | float | None,
    revised: str | float | None = None,
) -> dict:
    actual_value = numeric(actual)
    forecast_value = numeric(forecast)
    previous_value = numeric(revised) if numeric(revised) is not None else numeric(previous)
    if actual_value is None or forecast_value is None:
        return {
            "direction": "UNCERTAIN",
            "confidence_pct": 0.0,
            "surprise": None,
            "reason": "Actual and forecast values are both required for numeric surprise analysis.",
        }
    scale_candidates = [
        abs(forecast_value),
        abs(previous_value) if previous_value is not None else 0.0,
        1.0,
    ]
    scale = max(scale_candidates)
    surprise = (actual_value - forecast_value) / scale
    if event not in GOLD_INVERSE_EVENTS or abs(surprise) < 0.01:
        direction = "UNCERTAIN"
    else:
        direction = "NEGATIVE" if surprise > 0 else "POSITIVE"
    confidence = min(85.0, 45.0 + abs(surprise) * 180.0) if direction != "UNCERTAIN" else 35.0
    return {
        "direction": direction,
        "confidence_pct": round(confidence, 2),
        "surprise": round(surprise, 6),
        "reason": (
            "The immediate Gold mapping treats a stronger-than-forecast USD release as bearish "
            "for Gold and a weaker release as bullish. Statement context can override this."
        ),
    }


def _target_range(text: str) -> list[float] | None:
    match = re.search(
        r"target range for the federal funds rate (?:at|to) "
        r"(\d+(?:\.\d+)?)\s*(?:percent)?\s+to\s+"
        r"(\d+(?:\.\d+)?)\s*percent",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return [float(match.group(1)), float(match.group(2))]


def _phrase_score(text: str) -> dict:
    lowered = re.sub(r"\s+", " ", text.lower())
    hawkish = {
        phrase: weight
        for phrase, weight in FOMC_HAWKISH_PHRASES.items()
        if phrase in lowered
    }
    dovish = {
        phrase: weight
        for phrase, weight in FOMC_DOVISH_PHRASES.items()
        if phrase in lowered
    }
    return {
        "score": round(sum(hawkish.values()) - sum(dovish.values()), 3),
        "hawkish_phrases": list(hawkish),
        "dovish_phrases": list(dovish),
    }


def _policy_sentences(text: str) -> list[str]:
    keywords = (
        "inflation",
        "employment",
        "labor market",
        "federal funds",
        "economic activity",
        "risks",
        "committee decided",
    )
    sentences = [
        re.sub(r"\s+", " ", sentence).strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
    ]
    return [
        sentence
        for sentence in sentences
        if 20 <= len(sentence) <= 500
        and any(keyword in sentence.lower() for keyword in keywords)
    ]


def analyze_fomc_statement_diff(
    current_text: str,
    previous_text: str,
) -> dict:
    current_range = _target_range(current_text)
    previous_range = _target_range(previous_text)
    current_tone = _phrase_score(current_text)
    previous_tone = _phrase_score(previous_text)
    tone_change = current_tone["score"] - previous_tone["score"]
    rate_change_bps = None
    if current_range and previous_range:
        current_midpoint = sum(current_range) / 2
        previous_midpoint = sum(previous_range) / 2
        rate_change_bps = 100 * (current_midpoint - previous_midpoint)

    stance_change = tone_change
    if rate_change_bps is not None:
        stance_change += rate_change_bps / 12.5
    if stance_change >= 0.75:
        direction = "NEGATIVE"
    elif stance_change <= -0.75:
        direction = "POSITIVE"
    else:
        direction = "UNCERTAIN"
    confidence = min(85.0, 50.0 + 10.0 * abs(stance_change))
    if direction == "UNCERTAIN":
        confidence = min(confidence, 55.0)

    current_sentences = _policy_sentences(current_text)
    previous_normalized = {
        re.sub(r"\W+", " ", sentence.lower()).strip()
        for sentence in _policy_sentences(previous_text)
    }
    changed = [
        sentence
        for sentence in current_sentences
        if re.sub(r"\W+", " ", sentence.lower()).strip()
        not in previous_normalized
    ][:8]
    return {
        "gold_impact": direction,
        "confidence_pct": round(confidence, 2),
        "current_target_range_pct": current_range,
        "previous_target_range_pct": previous_range,
        "rate_change_bps": (
            round(rate_change_bps, 3)
            if rate_change_bps is not None
            else None
        ),
        "tone_change_score": round(tone_change, 3),
        "combined_stance_change": round(stance_change, 3),
        "current_tone": current_tone,
        "previous_tone": previous_tone,
        "changed_policy_sentences": changed,
        "interpretation": (
            "More dovish than the previous statement; positive for gold."
            if direction == "POSITIVE"
            else (
                "More hawkish than the previous statement; negative for gold."
                if direction == "NEGATIVE"
                else "No sufficiently strong deterministic statement change."
            )
        ),
        "timing_warning": (
            "Post-release statement analysis only. The press conference is a "
            "separate shock and can reverse this result."
        ),
    }


def _analysis_prompt(payload: dict, statement_text: str, timing_mode: str) -> str:
    timing_instruction = (
        "This is a PRE-RELEASE forecast. Use only information timestamped before publication."
        if timing_mode == "pre_release_prediction"
        else "This is POST-RELEASE interpretation, never a pre-release forecast."
    )
    return f"""Analyze the immediate XAUUSD reaction to this US macro release.
{timing_instruction}

Event data:
{json.dumps(payload, indent=2)}

Official release text:
{statement_text[:18_000] or "Not available"}

Return JSON only with:
gold_impact: POSITIVE, NEGATIVE, or UNCERTAIN
confidence_pct: number 0-100
summary: one short sentence
drivers: array of up to 4 strings
contradictions: array of up to 3 strings
data_quality: complete, partial, or insufficient

Prioritize actual-versus-forecast surprise, revisions, policy guidance, and contradictions.
Do not invent values or claim the text existed before publication."""


def build_pre_release_packet(
    prediction: dict,
    forecast: str | None = None,
    previous: str | None = None,
    source_url: str | None = None,
) -> dict:
    payload = {
        "timing_mode": "pre_release_prediction",
        "generated_at_utc": prediction.get("generated_at_utc"),
        "event": prediction.get("event"),
        "release_time": prediction.get("release_time_utc"),
        "minutes_before_release": prediction.get("minutes_before_release"),
        "model_gold_impact": prediction.get("gold_impact"),
        "model_confidence_pct": prediction.get("confidence_pct"),
        "model_probabilities": prediction.get("probabilities"),
        "expected_impulse_range_usd": prediction.get("expected_impulse_range_usd"),
        "market_context": prediction.get("market_context"),
        "forecast": forecast,
        "previous": previous,
        "source_url": source_url,
        "missing_inputs": [
            name
            for name, value in {
                "forecast": forecast,
                "previous": previous,
            }.items()
            if not value
        ],
    }
    return {
        "payload": payload,
        "prompt_for_codex": _analysis_prompt(payload, "", "pre_release_prediction"),
        "instruction": "Ask Codex to analyze this packet 15-30 minutes before the release.",
    }


def analyze_release(
    event: str,
    release_time: str,
    actual: str | None,
    forecast: str | None,
    previous: str | None,
    revised: str | None = None,
    source_url: str | None = None,
    previous_source_url: str | None = None,
) -> dict:
    event = event.upper()
    if event not in EVENTS:
        raise ValueError(f"Unsupported event: {event}")
    statement_text = fetch_official_text(source_url) if source_url else ""
    previous_statement_text = (
        fetch_official_text(previous_source_url)
        if previous_source_url
        else ""
    )
    numeric_result = deterministic_surprise(event, actual, forecast, previous, revised)
    fomc_statement_diff = (
        analyze_fomc_statement_diff(
            statement_text,
            previous_statement_text,
        )
        if event == "FOMC" and statement_text and previous_statement_text
        else None
    )
    payload = {
        "event": event,
        "release_time": release_time,
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "revised": revised,
        "numeric_surprise": numeric_result,
        "source_url": source_url,
        "previous_source_url": previous_source_url,
        "fomc_statement_diff": fomc_statement_diff,
    }
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "timing_mode": "post_release_interpretation",
        "event": event,
        "release_time": release_time,
        "numeric_analysis": numeric_result,
        "official_source_url": source_url,
        "official_text_characters": len(statement_text),
        "previous_official_text_characters": len(previous_statement_text),
        "fomc_statement_diff": fomc_statement_diff,
        "fomc_release_phases": (
            fomc_release_phases(
                datetime.fromisoformat(
                    release_time.replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            )
            if event == "FOMC"
            else None
        ),
        "codex_analysis_packet": {
            "payload": payload,
            "prompt_for_codex": _analysis_prompt(
                payload,
                statement_text,
                "post_release_interpretation",
            ),
        },
        "warning": (
            "This layer is valid only after publication. It is intentionally excluded from "
            "the 15-30 minute pre-release model and backtest."
        ),
    }
    ANALYSIS_DIR.mkdir(exist_ok=True)
    safe_time = re.sub(r"[^0-9]", "", release_time)[:14] or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    (ANALYSIS_DIR / f"{safe_time}-{event.lower()}.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result
