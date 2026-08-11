from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..domain.enums import OrderType, Side
from ..models import Account, CopyTestResult, CopyTestRun
from .accounts import ensure_system_state
from .audit import record_audit
from .demo_orders import DemoOrderExecutor, DemoOrderOutcome, DemoOrderRequest


class CopyTestExecutionRunner:
    """Executes only readiness-passed Copy Test rows and stores the broker outcome."""

    def __init__(self, executor: DemoOrderExecutor) -> None:
        self.executor = executor

    @staticmethod
    def _decimal(checks: dict[str, object], name: str) -> Decimal:
        value = checks.get(name)
        if value is None or value == "":
            raise ValueError(f"The ready result is missing {name.replace('_', ' ')}.")
        return Decimal(str(value))

    @staticmethod
    def _failed_outcome(message: str) -> DemoOrderOutcome:
        return DemoOrderOutcome(success=False, message=message)

    def _execute_result(
        self,
        session: Session,
        run: CopyTestRun,
        result: CopyTestResult,
        *,
        actor: str,
    ) -> DemoOrderOutcome:
        account = result.follower_account
        try:
            if result.calculated_volume is None:
                raise ValueError("The ready result has no calculated volume.")
            if not result.follower_symbol:
                raise ValueError("The ready result has no mapped broker symbol.")
            checks = result.checks or {}
            target_value = checks.get("take_profit")
            profile = account.risk_profile
            request = DemoOrderRequest(
                side=Side(run.side),
                order_type=OrderType(run.order_type),
                symbol=result.follower_symbol,
                volume=Decimal(result.calculated_volume),
                entry_price=self._decimal(checks, "entry_price"),
                stop_loss=self._decimal(checks, "stop_loss"),
                take_profit=(
                    Decimal(str(target_value))
                    if target_value is not None and target_value != ""
                    else None
                ),
                max_slippage_points=profile.max_slippage_points if profile else 30,
            )
            return self.executor.execute(session, account, request, actor=actor)
        except (ArithmeticError, RuntimeError, TypeError, ValueError) as exc:
            return self._failed_outcome(str(exc) or "Invalid demo-order request.")

    def execute(
        self,
        session: Session,
        run: CopyTestRun,
        *,
        actor: str,
    ) -> CopyTestRun:
        if not run.execute_demo:
            return run

        results = list(
            session.scalars(
                select(CopyTestResult)
                .options(
                    selectinload(CopyTestResult.follower_account).selectinload(Account.risk_profile)
                )
                .where(CopyTestResult.run_id == run.id)
                .order_by(CopyTestResult.created_at)
            ).all()
        )
        results.sort(key=lambda item: not item.follower_account.is_master)
        system = ensure_system_state(session)
        continuous_active = not system.global_pause and system.execution_mode == "demo"
        for result in results:
            if result.status != "passed":
                continue
            if continuous_active and not result.follower_account.is_master:
                checks = dict(result.checks or {})
                checks.update(
                    {
                        "execution_status": "continuous_copier",
                        "execution_message": (
                            "The order was placed on the master; the continuous copier "
                            "will route this follower without creating a duplicate."
                        ),
                    }
                )
                result.checks = checks
                continue
            outcome = self._execute_result(session, run, result, actor=actor)
            checks = dict(result.checks or {})
            checks.update(
                {
                    "execution_status": "completed" if outcome.success else "failed",
                    "execution_message": outcome.message,
                    "broker_order_id": outcome.broker_order_id,
                    "broker_deal_id": outcome.broker_deal_id,
                    "executed_price": (
                        str(outcome.executed_price) if outcome.executed_price is not None else None
                    ),
                    "cleanup_id": outcome.cleanup_id,
                    "broker_retcode": outcome.broker_retcode,
                }
            )
            result.checks = checks
            if outcome.success:
                result.error = ""
            else:
                result.status = "failed"
                result.error = outcome.message

        run.passed_followers = sum(result.status == "passed" for result in results)
        run.failed_followers = sum(result.status != "passed" for result in results)
        run.status = "passed" if run.failed_followers == 0 else "completed_with_errors"
        run.error = (
            ""
            if run.failed_followers == 0
            else (f"{run.failed_followers} account check(s) failed readiness or demo execution.")
        )
        run.completed_at = datetime.now(UTC)
        record_audit(
            session,
            actor=actor,
            action="copy_test.demo_execution_completed",
            target_type="copy_test_run",
            target_id=run.id,
            message=(
                f"Demo execution finished: {run.passed_followers} completed, "
                f"{run.failed_followers} failed."
            ),
            details={
                "symbol": run.symbol,
                "side": run.side,
                "order_type": run.order_type,
                "status": run.status,
            },
        )
        session.commit()
        session.refresh(run)
        return run
