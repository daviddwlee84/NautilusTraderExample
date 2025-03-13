from nautilus_trader.model import OrderBook
from nautilus_trader.model import BookOrder
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
def create_order_book_snapshot(instrument_id: InstrumentId, ts_init: int):
    order_book = OrderBook(
        instrument_id=instrument_id,
        # book_type=BookType.L2_MBP,  # Level 2 Market By Price
        book_type=BookType.L3_MBO,  # Level 3 Market By Order
    )

    # Simulated 5-level bid and ask data (price, volume)
    bids = [
        (19500.0, 1.0),  # Level 1
        (19490.0, 0.8),  # Level 2
        (19480.0, 0.6),  # Level 3
        (19470.0, 0.5),  # Level 4
        (19460.0, 0.4),  # Level 5
    ]
    asks = [
        (19510.0, 1.2),  # Level 1
        (19520.0, 0.9),  # Level 2
        (19530.0, 0.7),  # Level 3
        (19540.0, 0.6),  # Level 4
        (19550.0, 0.5),  # Level 5
    ]

    # Add bids
    for i, (price, volume) in enumerate(bids):
        order = BookOrder(
            price=Price(price, instrument.price_precision),
            size=Quantity(volume, instrument.size_precision),
            side=OrderSide.BUY,
            order_id=i,
        )
        order_book.add(order, ts_init)

    # Add asks
    for i, (price, volume) in enumerate(asks, start=len(bids)):
        order = BookOrder(
            price=Price(price, instrument.price_precision),
            size=Quantity(volume, instrument.size_precision),
            side=OrderSide.SELL,
            order_id=i,
        )
        order_book.add(order, ts_init)

    return order_book


# Step 3: Define a simple strategy
class SimpleOrderBookStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.instrument_id = instrument_id

    def on_start(self):
        """Called when the strategy starts."""
        # Subscribe to order book data
        self.subscribe_order_book_at_interval(
            self.instrument_id, book_type=BookType.L2_MBP
        )
        self.subscribe_order_book_deltas(self.instrument_id, book_type=BookType.L2_MBP)

    def on_stop(self):
        """Called when the strategy stops."""
        # Unsubscribe from data
        self.unsubscribe_order_book_deltas(self.instrument_id)

    def on_order_book_delta(self, delta) -> None:
        """Called when order book delta is received."""
        # Process order book delta updates
        self.log.info(f"Received order book delta: {delta}")

    def on_order_book(self, snapshot: OrderBook) -> None:
        """Called when order book snapshot is received."""
        # Process the complete order book snapshot
        best_bid = snapshot.best_bid_price()
        best_ask = snapshot.best_ask_price()
        self.log.info(f"Best Bid: {best_bid}, Best Ask: {best_ask}")
        if best_bid and best_ask:  # Check if we have both bid and ask prices
            mid_price = (best_bid + best_ask) / 2
            self.log.info(f"Mid Price: {mid_price}")


# Step 4: Set up the backtest engine
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
order_book_snapshot = create_order_book_snapshot(instrument_id, ts_init)
engine.add_data([order_book_snapshot])

# Add the strategy
strategy = SimpleOrderBookStrategy()
engine.add_strategy(strategy=strategy)

# Step 5: Run the backtest
engine.run(start=datetime(2025, 3, 12, 12, 0, 0), end=datetime(2025, 3, 12, 12, 1, 0))
