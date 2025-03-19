from pathlib import Path
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.core.nautilus_pyo3 import (
    OrderBookDepth10,
    InstrumentId,
    BookOrder,
    OrderSide,
    Price,
    Quantity,
)
from decimal import Decimal
import time


# Step 1: Generate mock OrderBookDepth10 data for demonstration
def generate_mock_orderbook_data(num_updates: int = 5) -> list[OrderBookDepth10]:
    instrument_id = InstrumentId.from_str("BTC-USDT.BINANCE")
    orderbook_updates = []
    sequence = 1
    base_price = 40000.0

    for i in range(num_updates):
        # Generate mock prices around the base price
        bid_prices = [base_price * (1 - 0.001 * (level + 1)) for level in range(10)]
        ask_prices = [base_price * (1 + 0.001 * (level + 1)) for level in range(10)]

        # Generate mock sizes
        bid_sizes = [1.0 + level * 0.5 for level in range(10)]
        ask_sizes = [1.0 + level * 0.5 for level in range(10)]

        # Create BookOrder objects for bids and asks
        bids = [
            BookOrder(
                side=OrderSide.BUY,
                price=Price(Decimal(str(price)), 3),
                size=Quantity(Decimal(str(size)), 1),
                order_id=i * 1000 + idx,
            )
            for idx, (price, size) in enumerate(zip(bid_prices, bid_sizes))
        ]

        asks = [
            BookOrder(
                side=OrderSide.SELL,
                price=Price(Decimal(str(price)), 3),
                size=Quantity(Decimal(str(size)), 1),
                order_id=(i * 1000 + idx + 500),
            )
            for idx, (price, size) in enumerate(zip(ask_prices, ask_sizes))
        ]

        # Mock order counts
        bid_counts = [5, 4, 4, 3, 3, 2, 2, 1, 1, 1]
        ask_counts = [5, 4, 4, 3, 3, 2, 2, 1, 1, 1]

        # Create timestamp in nanoseconds
        ts_now = int(time.time() * 1e9)

        # Create the depth update using regular OrderBookDepth10
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

        orderbook_updates.append(depth)
        sequence += 1
        base_price *= 1 + (0.0002 * (-1 if i % 2 == 0 else 1))

    return orderbook_updates


# Step 2: Create a function to store OrderBookDepth10 data using ParquetDataCatalog
def store_orderbook_depth_data(
    orderbook_updates: list[OrderBookDepth10],
) -> ParquetDataCatalog:
    # Define the catalog path
    catalog_path = Path.cwd() / "catalog"

    # Create a catalog instance
    catalog = ParquetDataCatalog(catalog_path)

    # First, store the instrument to the catalog
    # Ensure you have the actual instrument registered in the catalog
    from nautilus_trader.test_kit.providers import TestInstrumentProvider

    instrument = TestInstrumentProvider().btcusdt_binance()
    catalog.write_data([instrument])

    # Write the PyO3 OrderBookDepth10 data to the catalog
    catalog.write_data(orderbook_updates)

    print(
        f"Successfully stored {len(orderbook_updates)} OrderBookDepth10 updates to {catalog_path}"
    )
    return catalog


# Step 3: Reading the data back
def read_orderbook_depth_data(
    catalog: ParquetDataCatalog, instrument_id: InstrumentId
) -> list[OrderBookDepth10]:
    # Query the catalog for OrderBookDepth10 data
    data = catalog.order_book_depth10(
        instrument_ids=[instrument_id.value],
    )

    print(f"Retrieved {len(data)} OrderBookDepth10 records")
    return data


# Main execution
if __name__ == "__main__":
    # Generate some mock OrderBookDepth10 data
    orderbook_updates = generate_mock_orderbook_data(num_updates=10)

    # Store the data
    catalog = store_orderbook_depth_data(orderbook_updates)

    # Read the data back
    instrument_id = InstrumentId.from_str("BTC-USDT.BINANCE")
    retrieved_data = read_orderbook_depth_data(catalog, instrument_id)

    # Display a sample of the data
    if retrieved_data:
        sample = retrieved_data[0]
        print("\nSample OrderBookDepth10 data:")
        print(f"Instrument: {sample.instrument_id}")
        print(f"Sequence: {sample.sequence}")
        print(f"Timestamp: {sample.ts_event}")
        print(
            f"Best bid: ${sample.bids[0].price.as_double():.2f} @ {sample.bids[0].size.as_double():.4f}"
        )
        print(
            f"Best ask: ${sample.asks[0].price.as_double():.2f} @ {sample.asks[0].size.as_double():.4f}"
        )
