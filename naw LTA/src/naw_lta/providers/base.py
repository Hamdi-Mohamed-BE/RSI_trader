from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class MarketDataProvider(ABC):
    @abstractmethod
    def bars(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def trades(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def depth(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        raise NotImplementedError

