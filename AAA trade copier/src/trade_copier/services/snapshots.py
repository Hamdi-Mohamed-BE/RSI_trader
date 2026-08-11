from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.messages import AccountSnapshot, ContractSpec
from ..models import Account, AccountSymbolSpec


class SnapshotUnavailableError(ValueError):
    pass


class DatabaseSnapshotProvider:
    def get(self, session: Session, account: Account, symbol: str) -> AccountSnapshot:
        spec = session.scalar(
            select(AccountSymbolSpec).where(
                AccountSymbolSpec.account_id == account.id,
                AccountSymbolSpec.symbol == symbol,
                AccountSymbolSpec.trading_enabled.is_(True),
            )
        )
        if spec is None:
            raise SnapshotUnavailableError(
                f"No verified contract specification exists for {account.display_name} {symbol}."
            )
        if account.equity <= 0:
            raise SnapshotUnavailableError(
                f"{account.display_name} has no current equity snapshot."
            )
        return AccountSnapshot(
            account_id=UUID(account.id),
            equity=Decimal(account.equity),
            free_margin=Decimal(account.free_margin),
            currency=account.account_currency,
            contract=ContractSpec(
                symbol=spec.symbol,
                tick_size=Decimal(spec.tick_size),
                tick_value=Decimal(spec.tick_value),
                volume_min=Decimal(spec.volume_min),
                volume_max=Decimal(spec.volume_max),
                volume_step=Decimal(spec.volume_step),
                contract_size=Decimal(spec.contract_size),
            ),
        )
