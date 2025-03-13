import pandas as pd

# import os
# os.environ["NUMBA_DISABLE_JIT"] = "1"
import vectorbt as vbt

# Assume you have run order_book_snapshot.py and saved the orders_report.csv
orders_report = pd.read_csv("orders_report.csv")

pf = vbt.Portfolio.from_orders(
    close=orders_report.price,
    size=orders_report.quantity * orders_report.side.map({"BUY": 1, "SELL": -1}),
    # TODO: inherit from the engine (or initial config)
    init_cash=1_000_000,
    freq="1s",
    group_by=None,
)

print(pf.stats())
pf.save("pf.pkl")
pf.plot().write_image("pf.png")
