from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import RiskEngineConfig
from nautilus_trader.examples.strategies.ema_cross import EMACross
from nautilus_trader.examples.strategies.ema_cross import EMACrossConfig
from nautilus_trader.model import BarType
from nautilus_trader.model import Money
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.test_kit.providers import TestInstrumentProvider

# https://nautilustrader.io/docs/latest/tutorials/backtest_fx_bars
# https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/crypto_ema_cross_with_binance_provider.py

# from nautilus_trader.adapters.binance.spot.providers import (
#     BinanceSpotInstrumentProvider,
# )
# print(BinanceSpotInstrumentProvider().list_all())

ETHUSDT_BINANCE = TestInstrumentProvider().ethusdt_binance()
print(ETHUSDT_BINANCE)
from nautilus_trader.adapters.binance.common.constants import BINANCE_VENUE

print(ETHUSDT_BINANCE.venue, BINANCE_VENUE)

# Initialize a backtest configuration
config = BacktestEngineConfig(
    trader_id="BACKTESTER-001",
    # logging=LoggingConfig(log_level="ERROR"),
    logging=LoggingConfig(log_level="INFO"),
    risk_engine=RiskEngineConfig(
        bypass=True,  # Example of bypassing pre-trade risk checks for backtests
    ),
)

# Build backtest engine
engine = BacktestEngine(config=config)

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
        Money(10_000, ETHUSDT_BINANCE.quote_currency),
    ],
    fill_model=fill_model,
)

# Add instruments
engine.add_instrument(ETHUSDT_BINANCE)

# Add data
from data.binance_loader import BinanceKlineLoader

# ticks = BinanceKlineLoader("1s").get_date_symbol_ticks(
#     "2025-01-01", "ETHUSDT.BINANCE", target_freq="1-MINUTE", need_agg=True
# )
ticks = BinanceKlineLoader("1s").get_date_symbol_ticks("2025-01-01", "ETHUSDT.BINANCE")

engine.add_data(ticks)

# Configure your strategy
config = EMACrossConfig(
    instrument_id=ETHUSDT_BINANCE.id,
    # bar_type=BarType.from_str(f"{ETHUSDT_BINANCE.id}-1-MINUTE-LAST-INTERNAL"),
    bar_type=BarType.from_str(f"{ETHUSDT_BINANCE.id}-1-SECOND-LAST-INTERNAL"),
    fast_ema_period=10,
    slow_ema_period=20,
    trade_size=Decimal(1),
)

# Instantiate and add your strategy
strategy = EMACross(config=config)
engine.add_strategy(strategy=strategy)

engine.run()
print(engine.trader.generate_account_report(BINANCE_VENUE))
print(engine.trader.generate_order_fills_report())
print(engine.trader.generate_positions_report())

import ipdb

ipdb.set_trace()
