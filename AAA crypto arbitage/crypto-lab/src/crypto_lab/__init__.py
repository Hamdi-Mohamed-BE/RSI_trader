"""Calyx Crypto Lab: research-first crypto / prediction-market bots with a secure admin dashboard."""

from __future__ import annotations

__version__ = "0.1.0"


def main() -> None:
    """Console-script entry point (``crypto-lab``)."""
    from crypto_lab.cli import main as cli_main  # noqa: PLC0415 - keep package import light

    raise SystemExit(cli_main())
