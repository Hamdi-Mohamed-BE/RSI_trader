from sqlalchemy.orm import Session

from ..models import RuntimeState, StrategyConfig
from ..schemas import RuntimeConfig


def get_runtime_config(db: Session) -> RuntimeConfig:
    row = db.get(StrategyConfig, 1)
    if row is None:
        config = RuntimeConfig()
        row = StrategyConfig(id=1, values=config.model_dump(mode="json"))
        db.add(row)
        db.commit()
        return config
    return RuntimeConfig.model_validate(row.values)


def save_runtime_config(db: Session, config: RuntimeConfig) -> RuntimeConfig:
    row = db.get(StrategyConfig, 1)
    if row is None:
        row = StrategyConfig(id=1, values={})
        db.add(row)
    row.values = config.model_dump(mode="json")
    db.commit()
    return config


def get_runtime_state(db: Session) -> RuntimeState:
    state = db.get(RuntimeState, 1)
    if state is None:
        state = RuntimeState(id=1)
        db.add(state)
        db.commit()
    return state

