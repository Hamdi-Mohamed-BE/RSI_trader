import argparse
import getpass

from .config import get_settings
from .database import SessionLocal, create_schema
from .schemas import AdminCreate
from .services.auth import bootstrap_admin, create_admin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aaa-trade-copier")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init-db", help="Create the local database schema.")
    subcommands.add_parser(
        "ensure-admin", help="Create the administrator configured in .env when missing."
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
