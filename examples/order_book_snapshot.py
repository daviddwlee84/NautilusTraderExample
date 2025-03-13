from nautilus_trader.model import OrderBook
from nautilus_trader.model import BookOrder
from nautilus_trader.model import OrderBookDelta
from nautilus_trader.model import OrderBookDepth10
from nautilus_trader.model.enums import OrderSide, BookType
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.identifiers import Venue, InstrumentId
from nautilus_trader.core.datetime import dt_to_unix_nanos
from datetime import datetime
from nautilus_trader.model.enums import OmsType, AccountType
from nautilus_trader.model.currencies import USD
from nautilus_trader.model import Money
from nautilus_trader.backtest.models import FeeModel
from nautilus_trader.model.objects import Price, Quantity
from decimal import Decimal

# Step 1: Define a simple instrument (e.g., BTC/USD on Binance)
venue = Venue("BINANCE")
instrument_id = InstrumentId.from_str("BTC/USD.BINANCE")
instrument = TestInstrumentProvider.default_fx_ccy("BTC/USD", venue=venue)


# Step 2: Create a 5-level order book snapshot
# BUG
# [ERROR] BACKTESTER-001.DataEngine: Cannot handle data: unrecognized type <class 'nautilus_trader.model.book.OrderBook'> OrderBook L3_MBO
# instrument: BTC/USD.BINANCE
# sequence: 0
# ts_last: 1741780800000000000
# update_count: 10
# ╭──────┬─────────────┬──────╮
# │ bids │ price       │ asks │
# ├──────┼─────────────┼──────┤
# │      │ 19530.00000 │ [1]  │
# │      │ 19520.00000 │ [1]  │
# │      │ 19510.00000 │ [1]  │
# │ [1]  │ 19500.00000 │      │
# │ [1]  │ 19490.00000 │      │
# │ [1]  │ 19480.00000 │      │
# ╰──────┴─────────────┴──────╯
def create_order_book_snapshot(
    instrument_id: InstrumentId,
    ts_init: int,
    sequence: int = 0,
    base_price: float = 19500.0,
):

    # Generate mock prices around the base price
    bid_prices = [base_price * (1 - 0.001 * (level + 1)) for level in range(10)]
    ask_prices = [base_price * (1 + 0.001 * (level + 1)) for level in range(10)]

    # Generate mock sizes (larger sizes at worse prices)
    bid_sizes = [1.0 + level * 0.5 for level in range(10)]
    ask_sizes = [1.0 + level * 0.5 for level in range(10)]

    # Create BookOrder objects for bids and asks
    bids = [
        BookOrder(
            side=OrderSide.BUY,
            price=Price(Decimal(str(price)), 3),
            size=Quantity(Decimal(str(size)), 1),
            order_id=sequence * 1000 + idx,
        )
        for idx, (price, size) in enumerate(zip(bid_prices, bid_sizes))
    ]

    asks = [
        BookOrder(
            side=OrderSide.SELL,
            price=Price(Decimal(str(price)), 3),
            size=Quantity(Decimal(str(size)), 1),
            order_id=(sequence * 1000 + idx + 500),
        )
        for idx, (price, size) in enumerate(zip(ask_prices, ask_sizes))
    ]

    # Create timestamp in nanoseconds
    ts_now = ts_init

    # Create the depth update
    depth = OrderBookDepth10(
        instrument_id=instrument_id,
        bids=bids,
        asks=asks,
        bid_counts=[5, 4, 3, 2, 1, 1, 1, 1, 1, 1],
        ask_counts=[5, 4, 3, 2, 1, 1, 1, 1, 1, 1],
        flags=0,
        sequence=sequence,
        ts_event=ts_now,
        ts_init=ts_now,
    )

    return depth


# Step 3: Define a simple strategy
class SimpleOrderBookStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.instrument_id = instrument_id

    def on_start(self):
        """Called when the strategy starts."""
        self.log.info("Strategy starting...")
        self.subscribe_order_book_at_interval(
            self.instrument_id, book_type=BookType.L2_MBP
        )
        self.subscribe_order_book_deltas(self.instrument_id, book_type=BookType.L2_MBP)

    def on_stop(self):
        """Called when the strategy stops."""
        # Unsubscribe from data
        self.unsubscribe_order_book_deltas(self.instrument_id)

    def on_order_book_delta(self, delta: OrderBookDelta) -> None:
        """Called when order book delta is received."""
        # Process order book delta updates
        self.log.info(f"Received order book delta: {delta}")

    def on_order_book(self, snapshot: OrderBook) -> None:
        """Called when order book snapshot is received."""
        # Process the complete order book snapshot
        best_bid = snapshot.best_bid_price()
        best_ask = snapshot.best_ask_price()

        # Add more detailed logging
        self.log.info("Received order book snapshot:")
        self.log.info(f"Timestamp: {snapshot.ts_event}")
        self.log.info(f"Best Bid: {best_bid}, Best Ask: {best_ask}")

        if best_bid and best_ask:
            mid_price = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
            self.log.info(f"Mid Price: {mid_price:.2f}, Spread: {spread:.2f}")

        # Optional: Print full order book depth
        self.log.info("\nFull Order Book:")
        self.log.info("\n" + snapshot.pprint(num_levels=5))  # Show top 5 levels


# Step 4: Set up the backtest engine
# https://nautilustrader.io/docs/latest/concepts/logging/
engine = BacktestEngine()

# Add venue and instrument
# https://nautilustrader.io/docs/latest/concepts/instruments/#commissions


class PerContractFeeModel(FeeModel):
    def __init__(self, commission: Money):
        super().__init__()
        self.commission = commission

    def get_commission(
        self, Order_order, Quantity_fill_qty, Price_fill_px, Instrument_instrument
    ):
        total_commission = Money(
            self.commission * Quantity_fill_qty, self.commission.currency
        )
        return total_commission


engine.add_venue(
    venue=venue,
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    fee_model=PerContractFeeModel(
        Money(2.50, USD)
    ),  # Our custom fee-model injected here: 2.50 USD / per 1 filled contract
    starting_balances=[Money(1_000_000, USD)],
)

engine.add_instrument(instrument)

# Create and add the order book snapshot
ts_init = dt_to_unix_nanos(datetime(2025, 3, 12, 12, 0, 0))
order_book_snapshots = [
    create_order_book_snapshot(
        instrument_id,
        ts_init + i * 1_000_000_000,
        sequence=i,
        base_price=19500.0 * (1 + (0.0002 * (-1 if i % 2 == 0 else 1))),
    )
    for i in range(3)
]
engine.add_data(order_book_snapshots)

# Add the strategy
strategy = SimpleOrderBookStrategy()
engine.add_strategy(strategy=strategy)

# Step 5: Run the backtest
engine.run(start=datetime(2025, 3, 12, 12, 0, 0), end=datetime(2025, 3, 12, 12, 1, 0))
