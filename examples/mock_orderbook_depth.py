from nautilus_trader.model import OrderBookDepth10
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model import BookOrder
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.objects import Price, Quantity
from decimal import Decimal
import time


def generate_mock_orderbook_sequence(
    instrument_id: str = "BTC-USDT.BINANCE",
    base_price: float = 40000.0,
    num_updates: int = 5,
):
    instrument_id = InstrumentId.from_str(instrument_id)
    sequence = 1

    for i in range(num_updates):
        # Generate mock prices around the base price
        # Bids will be slightly below base_price, asks slightly above
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
                order_id=i * 1000 + idx,  # Unique order ID for each order
            )
            for idx, (price, size) in enumerate(zip(bid_prices, bid_sizes))
        ]

        asks = [
            BookOrder(
                side=OrderSide.SELL,
                price=Price(Decimal(str(price)), 3),
                size=Quantity(Decimal(str(size)), 1),
                order_id=(i * 1000 + idx + 500),  # Different range for ask order IDs
            )
            for idx, (price, size) in enumerate(zip(ask_prices, ask_sizes))
        ]

        # Mock order counts (number of orders at each level)
        bid_counts = [5, 4, 4, 3, 3, 2, 2, 1, 1, 1]  # Decreasing count with depth
        ask_counts = [5, 4, 4, 3, 3, 2, 2, 1, 1, 1]

        # Create timestamp in nanoseconds
        ts_now = int(time.time() * 1e9)

        # Create the depth update
        depth = OrderBookDepth10(
            instrument_id=instrument_id,
            bids=bids,
            asks=asks,
            bid_counts=bid_counts,
            ask_counts=ask_counts,
            flags=0,
            sequence=sequence,
            ts_event=ts_now,
            ts_init=ts_now,
        )

        # Increment sequence and slightly modify base price for next update
        sequence += 1
        # Randomly move price up or down by small amount
        base_price *= 1 + (0.0002 * (-1 if i % 2 == 0 else 1))

        yield depth


# Example usage
def print_orderbook_depth(depth: OrderBookDepth10):
    print(f"\nOrder Book Update (Sequence: {depth.sequence})")
    print("Bids".ljust(30) + "Asks")
    print("-" * 60)

    for i in range(10):
        bid = f"${depth.bids[i].price.as_double():.2f} @ {depth.bids[i].size.as_double():.4f} ({depth.bid_counts[i]})"
        ask = f"${depth.asks[i].price.as_double():.2f} @ {depth.asks[i].size.as_double():.4f} ({depth.ask_counts[i]})"
        print(f"{bid.ljust(30)}{ask}")


# Generate and print a sequence of mock updates
for depth in generate_mock_orderbook_sequence(num_updates=3):
    print_orderbook_depth(depth)
    time.sleep(0.5)  # Simulate time between updates
