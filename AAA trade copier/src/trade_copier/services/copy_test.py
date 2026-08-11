from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..domain.enums import AccountRole, AccountState, TerminalHealth
from ..models import Account, CopyTestResult, CopyTestRun, SymbolMapping
from ..schemas import CopyTestInput
from .audit import record_audit
from .risk import RiskCalculator, RiskRejectedError
from .snapshots import DatabaseSnapshotProvider, SnapshotUnavailableError


class CopyTestRunner:
    """Runs a no-order copy preflight against every configured follower."""

    def __init__(self) -> None:
        self.risk = RiskCalculator()
        self.snapshots = DatabaseSnapshotProvider()

    def run(self, session: Session, data: CopyTestInput, *, actor: str) -> CopyTestRun:
        data.validate_prices()
        master = session.scalar(select(Account).where(Account.is_master.is_(True)))
        run = CopyTestRun(
            master_account_id=master.id if master else None,
            symbol=data.symbol,
            side=data.side.value,
            master_volume=data.master_volume,
            entry_price=data.entry_price,
            stop_loss=data.stop_loss,
            take_profit=data.take_profit,
            status="running",
        )
        session.add(run)
        session.flush()

        followers = session.scalars(
            select(Account)
            .options(selectinload(Account.risk_profile), selectinload(Account.symbol_specs))
            .where(Account.role == AccountRole.FOLLOWER.value)
            .order_by(Account.display_name)
        ).all()
        run.total_followers = len(followers)

        if master is None:
            run.status = "failed"
            run.error = "No active master account is configured."
        elif not followers:
            run.status = "failed"
            run.error = "No follower accounts are configured."
        else:
            for follower in followers:
                result = self._test_follower(session, run, master, follower, data)
                session.add(result)
                if result.status == "passed":
                    run.passed_followers += 1
                else:
                    run.failed_followers += 1
            run.status = "passed" if run.failed_followers == 0 else "completed_with_errors"
            if run.failed_followers:
                run.error = f"{run.failed_followers} follower account(s) failed readiness checks."

        run.completed_at = datetime.now(UTC)
        record_audit(
            session,
            actor=actor,
            action="copy_test.completed",
            target_type="copy_test_run",
            target_id=run.id,
            message=(
                f"Copy test completed: {run.passed_followers} passed, "
                f"{run.failed_followers} failed."
            ),
            details={"symbol": run.symbol, "status": run.status},
        )
        session.commit()
        session.refresh(run)
        return run

    def _test_follower(
        self,
        session: Session,
        run: CopyTestRun,
        master: Account,
        follower: Account,
        data: CopyTestInput,
    ) -> CopyTestResult:
        checks: dict[str, object] = {
            "account_state": follower.state,
            "terminal_health": follower.health,
            "risk_profile": bool(follower.risk_profile),
        }
        follower_symbol = data.symbol
        try:
            if follower.state != AccountState.ACTIVE.value:
                raise ValueError(f"Follower state is {follower.state}; set it to active.")
            if follower.health != TerminalHealth.HEALTHY.value:
                raise ValueError(f"Terminal health is {follower.health}; reconnect MT5 first.")
            profile = follower.risk_profile
            if profile is None:
                raise ValueError("No risk profile is assigned.")
            if not profile.enabled:
                raise ValueError("The assigned risk profile is disabled.")

            mapping = session.scalar(
                select(SymbolMapping).where(
                    SymbolMapping.follower_account_id == follower.id,
                    SymbolMapping.master_symbol == data.symbol,
                    SymbolMapping.enabled.is_(True),
                )
            )
            price_offset = Decimal(mapping.price_offset) if mapping else Decimal("0")
            follower_symbol = mapping.follower_symbol if mapping else data.symbol
            entry = data.entry_price + price_offset
            stop_distance = abs(data.entry_price - data.stop_loss)
            stop = entry - stop_distance if data.side.value == "buy" else entry + stop_distance

            snapshot = self.snapshots.get(session, follower, follower_symbol)
            spec = snapshot.contract
            matching_spec = next(
                item for item in follower.symbol_specs if item.symbol == follower_symbol
            )
            if not matching_spec.trading_enabled:
                raise ValueError(f"Trading is disabled for {follower_symbol}.")
            if matching_spec.spread_points > profile.max_spread_points:
                raise ValueError(
                    f"Spread {matching_spec.spread_points} exceeds limit "
                    f"{profile.max_spread_points} points."
                )
            decision = self.risk.calculate_volume(
                snapshot=snapshot,
                profile=profile,
                master_volume=data.master_volume,
                master_equity=Decimal(master.equity),
                entry_price=entry,
                stop_loss=stop,
            )
            checks.update(
                {
                    "mapped_symbol": follower_symbol,
                    "contract_spec": spec.symbol,
                    "spread_points": matching_spec.spread_points,
                    "volume_step": str(spec.volume_step),
                }
            )
            return CopyTestResult(
                run_id=run.id,
                follower_account_id=follower.id,
                status="passed",
                follower_symbol=follower_symbol,
                calculated_volume=decision.volume,
                calculated_risk_cash=decision.cash_risk,
                checks=checks,
            )
        except (StopIteration, RiskRejectedError, SnapshotUnavailableError, ValueError) as exc:
            return CopyTestResult(
                run_id=run.id,
                follower_account_id=follower.id,
                status="failed",
                follower_symbol=follower_symbol,
                error=str(exc) or "Follower symbol specification is missing.",
                checks=checks,
            )
