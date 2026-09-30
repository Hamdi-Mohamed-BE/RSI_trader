"""Long-running bot workers and their registry (Factory)."""

from __future__ import annotations

from collections.abc import Callable

from crypto_lab.container import Container
from crypto_lab.workers.base import BotWorker


def _registry() -> dict[str, Callable[[Container], BotWorker]]:
    from crypto_lab.workers.cex import CexWorker  # noqa: PLC0415
    from crypto_lab.workers.copy import CopyWorker  # noqa: PLC0415
    from crypto_lab.workers.polymarket import (  # noqa: PLC0415 - avoids import cycle with container
        PolyScannerWorker,
        PolyWalletWorker,
    )
    from crypto_lab.workers.solana import SolanaWorker  # noqa: PLC0415

    return {w.slug: w for w in (PolyScannerWorker, PolyWalletWorker, CexWorker, CopyWorker, SolanaWorker)}


def available_workers() -> list[str]:
    return sorted(_registry())


def create_worker(slug: str, container: Container) -> BotWorker:
    try:
        factory = _registry()[slug]
    except KeyError as exc:
        raise SystemExit(f"Unknown worker '{slug}'. Available: {', '.join(available_workers())}") from exc
    return factory(container)
