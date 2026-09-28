"""Pin old news evidence to its actual source after the risk-input-only release.

Does not rescale returns, replace a backtest, or validate custom-risk performance.
The ordinary source-change rejection still applies to every unreviewed build.
"""
import hashlib
import json
from pathlib import Path

def historical_news_source(package_root: Path, current_source: Path, expected_sha: str, asset: str) -> Path:
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    if sha(current_source)==expected_sha:
        return current_source
    audit=package_root/'News Standalone Risk 2026-09-28'
    try:
        verification=json.loads((audit/'NATIVE_VERIFICATION.json').read_text())
        build=verification['build']['XAU' if asset=='XAU' else 'MULTI']
        baseline=audit/'baseline'/current_source.name
        valid=(verification['passed'] is True
               and build['baseline_source_sha256']==expected_sha==sha(baseline)
               and build['source_sha256']==sha(current_source)
               and build['binary_sha256']==sha(current_source.with_suffix('.ex5'))
               and any(row['asset']==asset and row['default_risk_exact_trade_parity'] is True
                       and row['custom_risk_geometry_unchanged'] is True for row in verification['checks']))
    except (OSError,KeyError,ValueError,TypeError):
        valid=False
    if not valid:
        raise RuntimeError('News Pulse source changed without a verified default-risk compatibility record; rerun before publishing.')
    return baseline
