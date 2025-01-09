from decimal import Decimal
from nautilus_trader.model.instruments import Instrument
from pathlib import Path
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.backtest.node import (
    BacktestVenueConfig,
    BacktestDataConfig,
    BacktestRunConfig,
    BacktestEngineConfig,
    BacktestNode,
)
from nautilus_trader.model import TradeTick
from nautilus_trader.config import ImportableStrategyConfig

# https://nautilustrader.io/docs/latest/tutorials/backtest_fx_bars
# https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/crypto_ema_cross_with_binance_provider.py

# https://nautilustrader.io/docs/latest/getting_started/backtest_high_level/


def get_instrument() -> Instrument:
    from nautilus_trader.test_kit.providers import TestInstrumentProvider

    ETHUSDT_BINANCE = TestInstrumentProvider().ethusdt_binance()
    return ETHUSDT_BINANCE


def prepare_data(instrument: Instrument) -> ParquetDataCatalog:
    from data.binance_loader import BinanceAggTradesLoader

    ticks = BinanceAggTradesLoader().get_date_symbol_ticks(
        "2025-01-01", instrument.id.value
    )
    catalog_path = Path.cwd() / "catalog"

    # Create a catalog instance
    catalog = ParquetDataCatalog(catalog_path)

    # Write instrument to the catalog
    catalog.write_data([instrument])

    # Write ticks to catalog
    catalog.write_data(ticks)

    print(catalog.instruments())

    return catalog


if __name__ == "__main__":
    ETHUSDT_BINANCE = get_instrument()
    catalog = prepare_data(ETHUSDT_BINANCE)

    # Add venue
    venue_configs = [
        BacktestVenueConfig(
            name=ETHUSDT_BINANCE.venue.value,
            oms_type="NETTING",
            account_type="CASH",
            base_currency=None,
            starting_balances=["1_000_000 USDT"],
        ),
    ]

    # Add data
    data_configs = [
        BacktestDataConfig(
            catalog_path=catalog.path,
            data_cls=TradeTick,
            instrument_id=ETHUSDT_BINANCE.id,
        ),
    ]

    # Add strategies
    strategies = [
        ImportableStrategyConfig(
            strategy_path="nautilus_trader.examples.strategies.signal_strategy:SignalStrategy",
            config_path="nautilus_trader.examples.strategies.signal_strategy:SignalStrategyConfig",
            config={
                "instrument_id": ETHUSDT_BINANCE.id,
            },
        ),
    ]

    config = BacktestRunConfig(
        engine=BacktestEngineConfig(strategies=strategies),
        data=data_configs,
        venues=venue_configs,
    )

    node = BacktestNode(configs=[config])

    results = node.run()
    print(results)

    import ipdb

    ipdb.set_trace()
