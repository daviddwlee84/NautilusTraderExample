from typing import Literal
import pandas as pd
from pathlib import Path
from nautilus_trader.persistence.wranglers_v2 import TradeTickDataWranglerV2
from nautilus_trader.model import TradeTick

FREQ_TYPE = Literal[
    "1s",
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1mo",
]


class BaseLoader:
    """
    A base class to define the common structure for data loaders.
    """

    def __init__(self, base_dir: str):
        # Store the base directory (by default using Path)
        self.base_dir = Path(base_dir)

    @staticmethod
    def _load_single(path: str | Path, parse_date: bool = True) -> pd.DataFrame:
        """
        Method intended to be overridden by child classes.
        Reads and returns a DataFrame.
        """
        raise NotImplementedError(
            "Please implement the `_load_single` method in your loader subclass."
        )

    def get_date_symbol(self, date_str: str, symbol: str, **kwargs) -> pd.DataFrame:
        """
        Given the date, symbol, and frequency, load the DataFrame.
        This is also intended to be overridden by child classes.
        """
        raise NotImplementedError(
            "Please implement the `get_date_symbol` method in your loader subclass."
        )


class BinanceAggTradesLoader(BaseLoader):
    header = [
        "trade_id",
        "price",
        "quantity",
        "first tradeId",
        "last tradeId",
        "timestamp",
        "buyer_maker",
        "was the trade the best price match",
    ]
    date_columns = ["timestamp"]

    def __init__(
        self,
        base_dir: str = "submodules/binance-public-data/python/data/spot/daily/aggTrades",
    ):
        super().__init__(base_dir=base_dir)

    @staticmethod
    def _load_single(path: str | Path, parse_date: bool = True) -> pd.DataFrame:
        df = pd.read_csv(path, header=None, names=BinanceAggTradesLoader.header)
        if parse_date:
            for col in BinanceAggTradesLoader.date_columns:
                df[col] = pd.to_datetime(df[col], unit="us")
        return df

    def get_date_symbol(self, date_str: str, symbol: str) -> pd.DataFrame:
        return self._load_single(
            self.base_dir / symbol / f"{symbol}-aggTrades-{date_str}.zip"
        )

    def get_date_symbol_ticks(
        self, date_str: str, symbol_venue: str, ts_init_delta: int = 0
    ) -> list[TradeTick]:
        symbol, venue = symbol_venue.split(".")
        trade_df = self.get_date_symbol(date_str=date_str, symbol=symbol)
        trade_df["ts_recv"] = trade_df[
            "timestamp"
        ]  # TODO: maybe add simulate_recv_latency_us
        return TradeTickDataWranglerV2(
            instrument_id=symbol_venue, price_precision=2, size_precision=4
        ).from_pandas(trade_df, ts_init_delta=ts_init_delta)


class BinanceKlineLoader(BaseLoader):
    header = [
        "open time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close time",
        "quote asset volume",
        "number of trades",
        "taker buy base asset volume",
        "taker buy quote asset volume",
        "ignore",
    ]
    date_columns = ["open time", "close time"]

    def __init__(
        self,
        base_dir: str = "submodules/binance-public-data/python/data/spot/daily/klines",
    ):
        super().__init__(base_dir=base_dir)

    @staticmethod
    def _load_single(path: str | Path, parse_date: bool = True) -> pd.DataFrame:
        """
        Reads a single kline CSV (possibly compressed), returning a DataFrame
        with time columns parsed as datetime (microseconds).
        """
        df = pd.read_csv(path, header=None, names=BinanceKlineLoader.header)
        if parse_date:
            for col in BinanceKlineLoader.date_columns:
                df[col] = pd.to_datetime(df[col], unit="us")
        return df.set_index("open time")

    def get_date_symbol(
        self, date_str: str, symbol: str, freq: FREQ_TYPE
    ) -> pd.DataFrame:
        """
        Builds the file path from the base directory, symbol, freq, and date,
        then loads the file using `_load_single`.
        """
        return self._load_single(
            self.base_dir / symbol / freq / f"{symbol}-{freq}-{date_str}.zip"
        )


class BinanceTradesLoader(BaseLoader):
    header = [
        "trade_id",
        "price",
        "quantity",
        "quoteQty",
        "timestamp",
        "buyer_maker",
        "isBestMatch",
    ]
    date_columns = ["timestamp"]

    def __init__(
        self,
        base_dir: str = "submodules/binance-public-data/python/data/spot/daily/trades",
    ):
        super().__init__(base_dir=base_dir)

    @staticmethod
    def _load_single(path: str | Path, parse_date: bool = True) -> pd.DataFrame:
        df = pd.read_csv(path, header=None, names=BinanceTradesLoader.header)
        if parse_date:
            for col in BinanceTradesLoader.date_columns:
                df[col] = pd.to_datetime(df[col], unit="us")
        return df

    def get_date_symbol(self, date_str: str, symbol: str) -> pd.DataFrame:
        return self._load_single(
            self.base_dir / symbol / f"{symbol}-trades-{date_str}.zip"
        )

    def get_date_symbol_ticks(
        self, date_str: str, symbol_venue: str, ts_init_delta: int = 0
    ) -> list[TradeTick]:
        symbol, venue = symbol_venue.split(".")
        trade_df = self.get_date_symbol(date_str=date_str, symbol=symbol)
        trade_df["ts_recv"] = trade_df[
            "timestamp"
        ]  # TODO: maybe add simulate_recv_latency_us
        return TradeTickDataWranglerV2(
            instrument_id=symbol_venue, price_precision=2, size_precision=4
        ).from_pandas(trade_df, ts_init_delta=ts_init_delta)


if __name__ == "__main__":
    # python -m data.binance_loader
    print(
        aggTrades_df := BinanceAggTradesLoader().get_date_symbol(
            "2025-01-01", "ETHUSDT"
        )
    )
    print(
        aggTrades_ticks := BinanceAggTradesLoader().get_date_symbol_ticks(
            "2025-01-01", "ETHUSDT.BINANCE"
        )[:10]
    )
    print(
        kline_df := BinanceKlineLoader().get_date_symbol("2025-01-01", "ETHUSDT", "1s")
    )
    print(trades_df := BinanceTradesLoader().get_date_symbol("2025-01-01", "ETHUSDT"))
    print(
        trades_ticks := BinanceTradesLoader().get_date_symbol_ticks(
            "2025-01-01", "ETHUSDT.BINANCE"
        )[:10]
    )
    import ipdb

    ipdb.set_trace()
