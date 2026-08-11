import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from .config import Settings, get_settings
from .database import SessionLocal, create_schema
from .domain.enums import AccountRole, AccountState, TerminalHealth
from .domain.messages import SourceTradeMessage
from .models import Account
from .services.accounts import ensure_system_state
from .services.copier import CopierCore
from .services.credentials import build_credential_vault
from .services.mt5_discovery import detect_and_import_running_accounts
from .services.terminals import TerminalManager
from .transport.protocol import ProtocolError, decode_message
from .transport.windows_named_pipe import WindowsNamedPipeTransport
from .transport.windows_pipe_io import PyWin32PipeChannel, WindowsNamedPipeServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("aaa.copier_core")


def mark_stale_accounts(settings: Settings) -> None:
    with SessionLocal() as session:
        accounts = session.scalars(select(Account)).all()
        now = datetime.now(UTC)
        for account in accounts:
            if account.last_heartbeat_at is None:
                continue
            heartbeat = account.last_heartbeat_at
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=UTC)
            if (now - heartbeat).total_seconds() > settings.heartbeat_timeout_seconds:
                account.health = TerminalHealth.OFFLINE.value
        session.commit()


async def accept_followers(
    settings: Settings,
    server: WindowsNamedPipeServer,
    transport: WindowsNamedPipeTransport,
) -> None:
    pending: dict[str, asyncio.Task[PyWin32PipeChannel]] = {}
    while True:
        with SessionLocal() as session:
            follower_ids = session.scalars(
                select(Account.id).where(
                    Account.role == AccountRole.FOLLOWER.value,
                    Account.state == AccountState.ACTIVE.value,
                )
            ).all()

        for account_id in follower_ids:
            if not transport.is_connected(account_id) and account_id not in pending:
                pipe_name = f"{settings.follower_pipe_prefix}_{account_id}"
                pending[account_id] = asyncio.create_task(server.accept(pipe_name))

        for account_id, task in list(pending.items()):
            if not task.done():
                continue
            del pending[account_id]
            try:
                channel = task.result()
            except (OSError, RuntimeError, ValueError) as exc:
                logger.error("Follower pipe failed account=%s error=%s", account_id, exc)
                continue
            transport.register_verified_handle(account_id, channel)
            logger.info("Follower pipe connected account=%s", account_id)

        await asyncio.sleep(1)


async def consume_master(
    settings: Settings,
    server: WindowsNamedPipeServer,
    transport: WindowsNamedPipeTransport,
) -> None:
    while True:
        logger.info("Waiting for master pipe=%s", settings.master_pipe_name)
        try:
            channel = await server.accept(settings.master_pipe_name)
            logger.info("Master publisher connected")
            while True:
                payload = await asyncio.to_thread(channel.read_line)
                decoded = decode_message(payload)
                if not isinstance(decoded, SourceTradeMessage):
                    raise ProtocolError("Master pipe accepts only source-trade messages.")
                with SessionLocal() as session:
                    core = CopierCore(settings=settings, transport=transport)
                    jobs = await core.process(session, decoded)
                    logger.info(
                        "Source event=%s produced jobs=%d",
                        decoded.event_uid,
                        len(jobs),
                    )
        except (OSError, ConnectionError, ProtocolError, ValueError) as exc:
            logger.warning("Master pipe disconnected or rejected: %s", exc)
            await asyncio.sleep(1)


async def watchdog(settings: Settings) -> None:
    vault = build_credential_vault(settings.storage_dir / "vault")
    terminal_manager = TerminalManager(
        instances_root=settings.mt5_instances_dir,
        vault=vault,
        default_template_path=settings.mt5_template_path,
    )
    while True:
        with SessionLocal() as session:
            detect_and_import_running_accounts(session, actor="connection-monitor")
            terminal_manager.reconnect_managed_accounts(
                session,
                actor="connection-monitor",
            )
        mark_stale_accounts(settings)
        await asyncio.sleep(settings.mt5_discovery_interval_seconds)


async def run() -> None:
    settings = get_settings()
    create_schema()
    with SessionLocal() as session:
        state = ensure_system_state(session)
        logger.info(
            "Copier Core started mode=%s paused=%s live_gate=%s",
            state.execution_mode,
            state.global_pause,
            settings.execution_is_permitted,
        )
    server = WindowsNamedPipeServer()
    transport = WindowsNamedPipeTransport(live_execution_permitted=settings.execution_is_permitted)
    await asyncio.gather(
        accept_followers(settings, server, transport),
        consume_master(settings, server, transport),
        watchdog(settings),
    )


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Copier Core stopped")


if __name__ == "__main__":
    main()
