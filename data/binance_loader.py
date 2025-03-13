from typing import Literal
import pandas as pd
from pathlib import Path
from nautilus_trader.persistence.wranglers_v2 import (
    TradeTickDataWranglerV2,
    BarDataWranglerV2,
)
from nautilus_trader.core.nautilus_pyo3 import (
    TradeTick as TradeTickV2,
    Bar as BarV2,
)
from nautilus_trader.model import TradeTick, Bar
import numpy as np

# from nautilus_trader.persistence.wranglers import BarDataWrangler, TradeTickDataWrangler, QuoteTickDataWrangler

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

    NOTE: wranglers_v2 will return pyo3 object, while wranglers will return nautilus_trader.core.data.Data (which is required by engine)
    https://nautilustrader.io/docs/latest/concepts/data#data-wranglers

    At the risk of causing confusion, there are also a growing number of DataWrangler v2 components, which will take a pd.DataFrame typically with a different fixed width Nautilus arrow v2 schema, and output pyo3 Nautilus objects which are only compatible with the new version of the Nautilus core, currently in development.
    These pyo3 provided data objects are not compatible where the legacy Cython objects are currently used (adding directly to a BacktestEngine etc).
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

    def get_date_symbol(self, date_str: str, symbol: str) -> pd.DataFrame:
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
        self,
        date_str: str,
        symbol_venue: str,
        ts_init_delta: int = 0,
        use_pyo3: bool = False,
        price_precision: int = 2,
        size_precision: int = 5,
    ) -> list[TradeTick | TradeTickV2]:
        symbol, venue = symbol_venue.split(".")
        trade_df = self.get_date_symbol(date_str=date_str, symbol=symbol)
        trade_df["ts_recv"] = trade_df[
            "timestamp"
        ]  # TODO: maybe add simulate_recv_latency_us
        ticks = TradeTickDataWranglerV2(
            instrument_id=symbol_venue,
            price_precision=price_precision,
            size_precision=size_precision,
        ).from_pandas(trade_df, ts_init_delta=ts_init_delta)
        if use_pyo3:
            return ticks
        return [TradeTick.from_pyo3(tick) for tick in ticks]


class BinanceKlineLoader(BaseLoader):
    header = [
        "timestamp",
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
    date_columns = ["timestamp", "close time"]

    def __init__(
        self,
        freq: FREQ_TYPE = "1s",
        base_dir: str = "submodules/binance-public-data/python/data/spot/daily/klines",
    ):
        self.freq = freq
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
        return df

    def get_date_symbol(self, date_str: str, symbol: str) -> pd.DataFrame:
        """
        Builds the file path from the base directory, symbol, freq, and date,
        then loads the file using `_load_single`.
        """
        return self._load_single(
            self.base_dir / symbol / self.freq / f"{symbol}-{self.freq}-{date_str}.zip"
        )

    def get_date_symbol_ticks(
        self,
        date_str: str,
        symbol_venue: str,
        ts_init_delta: int = 0,
        use_pyo3: bool = False,
        target_freq: str = "1-SECOND",
        need_agg: bool = False,
        price_precision: int = 2,
        size_precision: int = 5,
    ) -> list[Bar | BarV2]:
        """
        https://nautilustrader.io/docs/latest/api_reference/model/data#class-bartype

        https://nautilustrader.io/docs/latest/concepts/data/#bars-and-aggregation
        https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/fx_ema_cross_bracket_gbpusd_bars_external.py
        https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/fx_ema_cross_bracket_gbpusd_bars_internal.py

        TODO:
        Able to return
        QuoteTickDataWrangler.process_bar_data()
        => Bar.is_single_price() == False
        """
        symbol, venue = symbol_venue.split(".")
        ohlcv_df = self.get_date_symbol(date_str=date_str, symbol=symbol)
        ohlcv_df["ts_recv"] = ohlcv_df[
            "timestamp"
        ]  # TODO: maybe add simulate_recv_latency_us
        # ValueError: Invalid column type `volume` at index 4: expected UInt64, found Float64
        ohlcv_df["volume"] = (ohlcv_df["volume"] * 1e9).astype(np.uint64)
        # TODO: able to use different aggregation rules
        ticks = BarDataWranglerV2(
            bar_type=f"{symbol_venue}-{target_freq}-LAST-{'EXTERNAL' if not need_agg else 'INTERNAL'}",
            price_precision=price_precision,
            size_precision=size_precision,
        ).from_pandas(ohlcv_df, ts_init_delta=ts_init_delta)
        if use_pyo3:
            return ticks
        return [Bar.from_pyo3(tick) for tick in ticks]


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
        self,
        date_str: str,
        symbol_venue: str,
        ts_init_delta: int = 0,
        use_pyo3: bool = False,
        price_precision: int = 2,
        size_precision: int = 5,
    ) -> list[TradeTick | TradeTickV2]:
        symbol, venue = symbol_venue.split(".")
        trade_df = self.get_date_symbol(date_str=date_str, symbol=symbol)
        trade_df["ts_recv"] = trade_df[
            "timestamp"
        ]  # TODO: maybe add simulate_recv_latency_us
        ticks = TradeTickDataWranglerV2(
            instrument_id=symbol_venue,
            price_precision=price_precision,
            size_precision=size_precision,
        ).from_pandas(trade_df, ts_init_delta=ts_init_delta)
        if use_pyo3:
            return ticks
        return [TradeTick.from_pyo3(tick) for tick in ticks]


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
    print(kline_df := BinanceKlineLoader("1s").get_date_symbol("2025-01-01", "ETHUSDT"))
    print(
        bar_ticks_1s := BinanceKlineLoader().get_date_symbol_ticks(
            "2025-01-01", "ETHUSDT.BINANCE", use_pyo3=True
        )[:10]
    )
    print(
        bar_ticks_1s_v1 := BinanceKlineLoader().get_date_symbol_ticks(
            "2025-01-01", "ETHUSDT.BINANCE", use_pyo3=False
        )[:10]
    )
    print(
        isinstance(bar_ticks_1s[0], BarV2),
        isinstance(bar_ticks_1s_v1[0], Bar),
    )
    # NOTE: seems not aggregate here, not sure if backtest engine will handle this
    print(
        bar_ticks_1m := BinanceKlineLoader().get_date_symbol_ticks(
            "2025-01-01", "ETHUSDT.BINANCE", target_freq="1-MINUTE", need_agg=True
        )[:10]
    )
    print(trades_df := BinanceTradesLoader().get_date_symbol("2025-01-01", "ETHUSDT"))
    print(
        trades_ticks := BinanceTradesLoader().get_date_symbol_ticks(
            "2025-01-01", "ETHUSDT.BINANCE"
        )[:10]
    )
    import ipdb

    ipdb.set_trace()
