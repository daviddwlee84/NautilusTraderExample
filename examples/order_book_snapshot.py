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
def create_order_book_snapshot(
    instrument_id: InstrumentId,
    ts_init: int,
    sequence: int = 0,
    base_price: float = 19500.0,
):
    # Generate mock prices around the base price (only 5 levels)
    bid_prices = [base_price * (1 - 0.001 * (level + 1)) for level in range(5)]
    ask_prices = [base_price * (1 + 0.001 * (level + 1)) for level in range(5)]

    # Generate mock sizes for 5 levels
    bid_sizes = [1.0 + level * 0.5 for level in range(5)]
    ask_sizes = [1.0 + level * 0.5 for level in range(5)]

    # Create BookOrder objects for active levels (first 5)
    bids = [
        BookOrder(
            side=OrderSide.BUY,
            price=Price(Decimal(str(price)), 3),
            size=Quantity(Decimal(str(size)), 1),
            order_id=sequence * 1000 + idx,
        )
        for idx, (price, size) in enumerate(zip(bid_prices, bid_sizes))
    ]

    # Add empty orders for remaining levels (with zero quantity)
    bids.extend(
        [
            BookOrder(
                side=OrderSide.BUY,
                price=Price(Decimal(str(bid_prices[-1])), 3),
                size=Quantity(Decimal("0"), 1),
                order_id=sequence * 1000 + idx + 5,
            )
            for idx in range(5)
        ]
    )

    asks = [
        BookOrder(
            side=OrderSide.SELL,
            price=Price(Decimal(str(price)), 3),
            size=Quantity(Decimal(str(size)), 1),
            order_id=(sequence * 1000 + idx + 500),
        )
        for idx, (price, size) in enumerate(zip(ask_prices, ask_sizes))
    ]

    # Add empty orders for remaining levels (with zero quantity)
    asks.extend(
        [
            BookOrder(
                side=OrderSide.SELL,
                price=Price(Decimal(str(ask_prices[-1])), 3),
                size=Quantity(Decimal("0"), 1),
                order_id=sequence * 1000 + idx + 505,
            )
            for idx in range(5)
        ]
    )

    ts_now = ts_init

    # https://nautilustrader.io/docs/latest/api_reference/model/book/
    # https://nautilustrader.io/docs/latest/api_reference/model/data/#class-orderbookdepth10
    depth = OrderBookDepth10(
        instrument_id=instrument_id,
        bids=bids,
        asks=asks,
        bid_counts=[5, 4, 3, 2, 1, 0, 0, 0, 0, 0],  # Only 5 levels have counts
        ask_counts=[5, 4, 3, 2, 1, 0, 0, 0, 0, 0],  # Only 5 levels have counts
        flags=0,
        sequence=sequence,
        ts_event=ts_now,
        ts_init=ts_now,
    )

    # BUG: we cannot only pass in 5 levels, we need to pass in 10 levels
    # thread '<unnamed>' panicked at crates/model/src/enums.rs:844:18:
    # Order invariant failed: side must be `Buy` or `Sell`
    # note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
    # [1]    1411 abort      python examples/order_book_snapshot.py
    # depth = OrderBookDepth10(
    #     instrument_id=instrument_id,
    #     bids=bids[:5],
    #     asks=asks[:5],
    #     bid_counts=[5, 4, 3, 2, 1, 0, 0, 0, 0, 0][:5],  # Only 5 levels have counts
    #     ask_counts=[5, 4, 3, 2, 1, 0, 0, 0, 0, 0][:5],  # Only 5 levels have counts
    #     flags=0,
    #     sequence=sequence,
    #     ts_event=ts_now,
    #     ts_init=ts_now,
    # )

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
        self.log.info(
            f"Timestamp: {datetime.fromtimestamp(snapshot.ts_event / 1e9).strftime('%Y-%m-%d %H:%M:%S.%f')}"
        )
        self.log.info(f"Best Bid: {best_bid}, Best Ask: {best_ask}")

        if best_bid and best_ask:
            mid_price = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
            self.log.info(f"Mid Price: {mid_price:.2f}, Spread: {spread:.2f}")

        # Optional: Print full order book depth
        self.log.info("\nFull Order Book:")
        # self.log.info("\n" + snapshot.pprint(num_levels=5))  # Show top 5 levels
        self.log.info("\n" + snapshot.pprint(num_levels=10))  # Show top 10 levels


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
    for i in range(10)
]
engine.add_data(order_book_snapshots)

# Add the strategy
strategy = SimpleOrderBookStrategy()
engine.add_strategy(strategy=strategy)

# Step 5: Run the backtest
engine.run(start=datetime(2025, 3, 12, 12, 0, 0), end=datetime(2025, 3, 12, 12, 1, 0))
