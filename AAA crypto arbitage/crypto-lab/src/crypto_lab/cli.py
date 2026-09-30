"""Command-line entry point: ``uv run crypto-lab <command>``."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import sys

from crypto_lab.config import get_settings
from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.errors import ValidationError
from crypto_lab.infrastructure.db.migrations import upgrade_to_head
from crypto_lab.infrastructure.db.paper_models import PaperAccount
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.workers import available_workers, create_worker


async def _prepare() -> Container:
    container = Container.build(get_settings())
    await upgrade_to_head(container.engine)
    async with unit_of_work(container.session_factory) as session:
        await container.bots(session).seed(paper=container.settings.default_paper_mode)
        if await session.get(PaperAccount, 1) is None:
            session.add(
                PaperAccount(
                    id=1,
                    initial=container.settings.paper_balance_usdc,
                    trade_limit=container.settings.paper_trade_limit_usdc,
                )
            )
    return container


async def _create_admin(username: str) -> int:
    password = getpass.getpass("New admin password (min 12 chars): ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1
    container = await _prepare()
    try:
        async with unit_of_work(container.session_factory) as session:
            await container.auth(session).create_admin(username, password)
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        await container.dispose()
    print(f"Admin '{username}' created. Sign in at http://{get_settings().host}:{get_settings().port}/login")
    return 0


async def _run_worker(slug: str, once: bool, mode: str | None) -> int:
    container = await _prepare()
    worker = create_worker(slug, container)
    try:
        if once:
            print(await worker.run_once(BotMode(mode or BotMode.SHADOW.value)))
        else:
            await worker.run_forever()
    finally:
        if once:
            await worker.aclose()
        await container.dispose()
    return 0


async def _migrate() -> int:
    container = await _prepare()
    await container.dispose()
    print("Database is at the latest migration.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crypto-lab", description="Calyx Crypto Lab command line")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="run the dashboard (127.0.0.1:8090 by default)")
    admin = sub.add_parser("create-admin", help="create a dashboard admin (password is prompted)")
    admin.add_argument("username")
    sub.add_parser("migrate", help="apply database migrations and seed bots")
    worker = sub.add_parser("worker", help="run a bot worker")
    worker.add_argument("slug", choices=available_workers())
    worker.add_argument("--once", action="store_true", help="run one cycle and exit (ignores the dashboard mode)")
    worker.add_argument(
        "--mode", choices=[BotMode.SHADOW.value, BotMode.PAPER.value], help="mode for --once (default: shadow)"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.command == "serve":
        import uvicorn  # noqa: PLC0415 - only needed for `serve`

        settings = get_settings()
        uvicorn.run(
            "crypto_lab.web.app:create_app", factory=True, host=settings.host, port=settings.port, proxy_headers=False
        )
        return 0
    if args.command == "create-admin":
        return asyncio.run(_create_admin(args.username))
    if args.command == "migrate":
        return asyncio.run(_migrate())
    if args.command == "worker":
        return asyncio.run(_run_worker(args.slug, args.once, args.mode))
    return 2
