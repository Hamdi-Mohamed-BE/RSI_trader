from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from ..domain.enums import RiskMode
from ..domain.messages import AccountSnapshot
from ..models import RiskProfile


class RiskRejectedError(ValueError):
    pass


@dataclass(frozen=True)
class VolumeDecision:
    volume: Decimal
    cash_risk: Decimal
    expected_loss_per_lot: Decimal
    sizing_method: str


class RiskCalculator:
    @staticmethod
    def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
        units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
        return units * step

    def calculate_volume(
        self,
        *,
        snapshot: AccountSnapshot,
        profile: RiskProfile,
        master_volume: Decimal,
        master_equity: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal | None,
    ) -> VolumeDecision:
        contract = snapshot.contract
        mode = RiskMode(profile.mode)
        minimum_volume_fallback = False

        if mode is RiskMode.MIRROR_LOTS:
            raw_volume = master_volume
            cash_risk = Decimal("0")
            expected_loss_per_lot = Decimal("0")
            sizing_method = RiskMode.MIRROR_LOTS.value
            minimum_volume_fallback = True
        elif mode is RiskMode.FIXED_LOTS:
            if profile.fixed_lots is None:
                raise RiskRejectedError("Fixed-lot mode has no configured volume.")
            raw_volume = Decimal(profile.fixed_lots)
            cash_risk = Decimal("0")
            expected_loss_per_lot = Decimal("0")
            sizing_method = RiskMode.FIXED_LOTS.value
        elif mode is RiskMode.EQUITY_PROPORTIONAL:
            if master_equity <= 0:
                raise RiskRejectedError("Master equity is unavailable.")
            raw_volume = master_volume * snapshot.equity / master_equity
            cash_risk = Decimal("0")
            expected_loss_per_lot = Decimal("0")
            sizing_method = RiskMode.EQUITY_PROPORTIONAL.value
        elif stop_loss is None and not profile.reject_without_stop:
            raw_volume = master_volume
            cash_risk = Decimal("0")
            expected_loss_per_lot = Decimal("0")
            sizing_method = "mirror_lots_no_stop"
            minimum_volume_fallback = True
        else:
            if stop_loss is None:
                raise RiskRejectedError("Trade has no stop loss.")
            stop_distance = abs(entry_price - stop_loss)
            if stop_distance <= 0:
                raise RiskRejectedError("Stop distance must be positive.")
            expected_loss_per_lot = stop_distance / contract.tick_size * contract.tick_value
            if expected_loss_per_lot <= 0:
                raise RiskRejectedError("Broker contract values produce no measurable risk.")

            if mode is RiskMode.FIXED_CASH:
                if profile.fixed_cash_risk is None:
                    raise RiskRejectedError("Fixed-cash mode has no configured cash risk.")
                cash_risk = Decimal(profile.fixed_cash_risk)
            else:
                requested_percent = min(
                    Decimal(profile.risk_percent),
                    Decimal(profile.max_risk_per_trade_percent),
                )
                cash_risk = snapshot.equity * requested_percent / Decimal("100")
            raw_volume = cash_risk / expected_loss_per_lot
            sizing_method = mode.value

        volume = self._floor_to_step(raw_volume, contract.volume_step)
        volume = min(volume, contract.volume_max)
        if volume < contract.volume_min:
            if minimum_volume_fallback:
                volume = contract.volume_min
            else:
                raise RiskRejectedError(
                    "Minimum broker volume would exceed the configured risk; "
                    "the trade was rejected."
                )

        if expected_loss_per_lot > 0:
            cash_risk = volume * expected_loss_per_lot
        return VolumeDecision(
            volume=volume,
            cash_risk=cash_risk.quantize(Decimal("0.01")),
            expected_loss_per_lot=expected_loss_per_lot,
            sizing_method=sizing_method,
        )
