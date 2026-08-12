import argparse
import getpass

from .config import get_settings
from .database import SessionLocal, create_schema
from .schemas import AdminCreate
from .services.auth import bootstrap_admin, create_admin
from .services.mt5_agents import Mt5AgentBootstrapper
from .services.mt5_discovery import detect_and_import_running_accounts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aaa-trade-copier")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init-db", help="Create the local database schema.")
    subcommands.add_parser(
        "ensure-admin", help="Create the administrator configured in .env when missing."
    )
    subcommands.add_parser(
        "bootstrap-mt5-agents",
        help="Install MT5 agents and auto-attach the publisher to the active master.",
    )
    admin = subcommands.add_parser("create-admin", help="Create a local dashboard administrator.")
    admin.add_argument("--email", default="")
    admin.add_argument("--display-name", default="Administrator")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    create_schema()
    if args.command == "init-db":
        print("Database schema is ready.")
        return
    with SessionLocal() as session:
        if args.command == "bootstrap-mt5-agents":
            if not settings.auto_install_mt5_agents:
                print("Automatic MT5 agent installation is disabled in .env.")
                return
            detect_and_import_running_accounts(session, actor="run-bat-agent-bootstrap")
            results = Mt5AgentBootstrapper(settings=settings).bootstrap(
                session,
                actor="run-bat-agent-bootstrap",
            )
            if not results:
                print("No logged-in MT5 accounts were found; agent bootstrap skipped.")
                return
            master_failures = 0
            for result in results:
                state = "OK" if result.installed else "ERROR"
                print(f"[{state}] {result.display_name}: {result.message}")
                master_failures += not result.installed and result.role == "master"
            if master_failures:
                raise RuntimeError(
                    "The Master Publisher could not be attached. Resolve the reported "
                    "MT5 error and run run.bat again."
                )
            return
        if args.command == "ensure-admin":
            user = bootstrap_admin(session, settings)
            if user is None:
                raise ValueError("ADMIN_PASSWORD must be configured before ensuring an admin.")
            print(f"Default administrator {user.email} is ready.")
            return
        email = args.email or input("Administrator email: ").strip()
        password = getpass.getpass("Administrator password (12+ characters): ")
        create_admin(
            session,
            AdminCreate(email=email, password=password, display_name=args.display_name),
        )
        print(f"Administrator {email} created.")


if __name__ == "__main__":
    main()
