from typing import Literal
from nautilus_trader.model import BarType, Money
from nautilus_trader.model.instruments import Instrument

# https://nautilustrader.io/docs/latest/tutorials/backtest_fx_bars
# https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/crypto_ema_cross_with_binance_provider.py


def get_instrument() -> Instrument:
    from nautilus_trader.test_kit.providers import TestInstrumentProvider

    # from nautilus_trader.adapters.binance.spot.providers import (
    #     BinanceSpotInstrumentProvider,
    # )
    # print(BinanceSpotInstrumentProvider().list_all())
    ETHUSDT_BINANCE = TestInstrumentProvider().ethusdt_binance()
    print(ETHUSDT_BINANCE)
    from nautilus_trader.adapters.binance.common.constants import BINANCE_VENUE

    print(ETHUSDT_BINANCE.venue, BINANCE_VENUE)
    return ETHUSDT_BINANCE


def get_engine(log_level: str = "ERROR"):
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.config import LoggingConfig, RiskEngineConfig

    # Initialize a backtest configuration
    config = BacktestEngineConfig(
        trader_id="BACKTESTER-001",
        logging=LoggingConfig(log_level=log_level),
        risk_engine=RiskEngineConfig(
            bypass=True,  # Example of bypassing pre-trade risk checks for backtests
        ),
    )

    # Build backtest engine
    engine = BacktestEngine(config=config)

    return engine


def get_data(instrument: Instrument, use_1m: bool = False):
    # Add data
    from data.binance_loader import BinanceKlineLoader

    if use_1m:
        # BUG: not able to trigger the "internal aggregation"
        ticks = BinanceKlineLoader("1s").get_date_symbol_ticks(
            "2025-01-01",
            instrument.id.value,
            target_freq="1-MINUTE",
            # ValueError: 'bar_type.aggregation_source' <flag 'AggregationSource'> of 2 was not equal to 'required source' <flag 'AggregationSource'> of 1
            need_agg=False,
            price_precision=instrument.price_precision,
            size_precision=instrument.size_precision,
        )
    else:
        ticks = BinanceKlineLoader("1s").get_date_symbol_ticks(
            "2025-01-01",
            instrument.id.value,
            price_precision=instrument.price_precision,
            size_precision=instrument.size_precision,
        )
    return ticks


def get_strategy(
    instrument: Instrument,
    use_1m: bool = False,
    strategy_name: Literal["ema", "talib"] = "ema",
):
    from decimal import Decimal

    match strategy_name:
        case "ema":
            from nautilus_trader.examples.strategies.ema_cross import (
                EMACross,
                EMACrossConfig,
            )

            # Configure your strategy
            config = EMACrossConfig(
                instrument_id=instrument.id,
                bar_type=(
                    BarType.from_str(f"{instrument.id}-1-SECOND-LAST-EXTERNAL")
                    if not use_1m
                    else BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-INTERNAL")
                ),
                fast_ema_period=10,
                slow_ema_period=20,
                trade_size=Decimal(1),
            )

            # Instantiate and add your strategy
            strategy = EMACross(config=config)
        case "talib":
            # https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/fx_talib_gbpusd_bars_internal.py#L26
            from nautilus_trader.examples.strategies.talib_strategy import (
                TALibStrategy,
                TALibStrategyConfig,
            )

            config = TALibStrategyConfig(
                bar_type=(
                    BarType.from_str(f"{instrument.id}-1-SECOND-LAST-EXTERNAL")
                    if not use_1m
                    else BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-INTERNAL")
                )
            )
            strategy = TALibStrategy(config=config)

    return strategy


if __name__ == "__main__":

    INIT_CASH = 10_000
    USE_1M = False

    engine = get_engine(log_level="ERROR")

    ETHUSDT_BINANCE = get_instrument()

    # Add venue
    # nautilus_trader.common.config.InvalidConfiguration: Cannot add an `Instrument` object without first adding its associated venue. Add the BINANCE venue using the `add_venue` method.
    # We need to add venue before adding instruments
    from nautilus_trader.backtest.models import FillModel
    from nautilus_trader.model.enums import AccountType, OmsType

    fill_model = FillModel(
        prob_fill_on_limit=0.2,
        prob_fill_on_stop=0.95,
        prob_slippage=0.5,
        random_seed=42,
    )

    engine.add_venue(
        venue=ETHUSDT_BINANCE.venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[
            Money(1_000_000, ETHUSDT_BINANCE.base_currency),
            Money(INIT_CASH, ETHUSDT_BINANCE.quote_currency),
        ],
        fill_model=fill_model,
    )

    # Add instruments
    engine.add_instrument(ETHUSDT_BINANCE)

    # Add data
    ticks = get_data(ETHUSDT_BINANCE, use_1m=USE_1M)
    engine.add_data(ticks)

    # Add strategy
    if not ticks[0].is_single_price():
        # NOTE: talib strategy will skip all "single price bar"
        talib_strategy = get_strategy(
            ETHUSDT_BINANCE, use_1m=USE_1M, strategy_name="talib"
        )
        engine.add_strategy(strategy=talib_strategy)
    else:
        ema_strategy = get_strategy(ETHUSDT_BINANCE, use_1m=USE_1M, strategy_name="ema")
        engine.add_strategy(strategy=ema_strategy)

    import time

    start_time = time.perf_counter()
    # Run the engine (from start to end of data)
    engine.run()
    print("Time:", time.perf_counter() - start_time)

    print(
        account_report := engine.trader.generate_account_report(ETHUSDT_BINANCE.venue)
    )
    print(order_fills_report := engine.trader.generate_order_fills_report())
    # BUG: viewing positions_report and order_fills_report directly in ipdb will cause error:
    # BlockingIOError: [Errno 35] write could not complete without blocking
    print(positions_report := engine.trader.generate_positions_report())

    # For repeated backtest runs make sure to reset the engine
    engine.reset()

    # Good practice to dispose of the object when done
    engine.dispose()

    import os

    # BUG (solved by disable numba): numba.core.errors.TypingError: Failed in nopython mode pipeline (step: nopython frontend)
    os.environ["NUMBA_DISABLE_JIT"] = "1"
    import vectorbt as vbt
    import numpy as np

    USE_TIME_INDEX = True
    if USE_TIME_INDEX:
        order_df = order_fills_report.reset_index().set_index("ts_init")
    else:
        order_df = order_fills_report

    USE_DETAIL_PRICE = False
    if USE_DETAIL_PRICE:
        import pandas as pd
        from vectorbt.base.reshape_fns import broadcast_to

        close_price = pd.Series({tick.ts_init: tick.close for tick in ticks})
        close_price.index = pd.to_datetime(close_price.index, unit="ns", utc=True)

        # TODO: solve this
        # BUG: ValueError: shape mismatch: objects cannot be broadcast to a single shape.  Mismatch is between arg 0 with shape (4756,) and arg 16 with shape (86400,).
        # NOTE: there exist duplicate ts_init among different orders (non-unique)
        pf = vbt.Portfolio.from_orders(
            close=close_price,
            price=order_df.avg_px.astype(float),
            size=order_df.filled_qty.astype(float)
            * np.where(order_df.side.eq("BUY"), 1, -1),
            fees=ETHUSDT_BINANCE.taker_fee,
            slippage=order_df.slippage.astype(float),
            init_cash=INIT_CASH,
            freq="1s" if not USE_1M else "1m",
        )
    else:
        pf = vbt.Portfolio.from_orders(
            order_df.avg_px.astype(float),
            size=order_df.filled_qty.astype(float)
            * np.where(order_df.side.eq("BUY"), 1, -1),
            fees=ETHUSDT_BINANCE.taker_fee,
            slippage=order_df.slippage.astype(float),
            init_cash=INIT_CASH,
            freq="1s" if not USE_1M else "1m",
        )

    print(pf.stats())
    pf.plot().show()
    # pf.plot(
    #     subplots=[
    #         "orders",
    #         "trade_pnl",
    #         "cum_returns",
    #         "drawdowns",
    #         "underwater",
    #         "asset_flow",
    #         "asset_value",
    #         "assets",
    #         "cash",
    #         "cash_flow",
    #         "gross_exposure",
    #         "net_exposure",
    #         # "position_pnl",
    #         # "positions",
    #         "trades",
    #         "value",
    #     ]
    # ).show()

    import ipdb

    ipdb.set_trace()
