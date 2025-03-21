# Nautilus Trader Example

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> - Recommend use PyCharm to edit Nautilus Trader's code for better auto-completion of Cython modules
> - I use [`uv`](https://github.com/astral-sh/uv) to manage Python version and manage packages at once. (Which is recommend [officially](https://nautilustrader.io/docs/latest/developer_guide/environment_setup))
> - ~~I use [`mamba`](https://github.com/mamba-org/mamba) (a faster `conda`) to manage Python version, and manage packages using `pip`~~
> - If you use Cursor, I recommend adding `https://nautilustrader.io/docs/latest/` to [Docs](https://docs.cursor.com/context/@-symbols/@-docs#manage-custom-docs). I generate some [`.cursor/rules`](./.cursor/rules/) using [`requirements.txt`](requirements.txt) with [cursor.directory](https://cursor.directory/generate).

## Getting Started

```bash
uv venv
uv install
```

> Python 3.11+
>
> ```bash
> pip install -r requirements.txt
> pip install -r submodules/binance-public-data/python/requirements.txt
> ```

Data

```bash
# NOTE: Pandas can load csv from zip directly
python submodules/binance-public-data/python/download-aggTrade.py -d 2025-01-01 -s ETHUSDT -t spot
# unzip submodules/binance-public-data/python/data/spot/daily/aggTrades/ETHUSDT/ETHUSDT-aggTrades-2025-01-01.zip -d submodules/binance-public-data/python/data/spot/daily/aggTrades/ETHUSDT/

python submodules/binance-public-data/python/download-kline.py -d 2025-01-01 -s ETHUSDT -t spot -i 1s
# unzip submodules/binance-public-data/python/data/spot/daily/klines/ETHUSDT/1s/ETHUSDT-1s-2025-01-01.zip -d submodules/binance-public-data/python/data/spot/daily/klines/ETHUSDT/1s/

python submodules/binance-public-data/python/download-trade.py -d 2025-01-01 -s ETHUSDT -t spot
# unzip submodules/binance-public-data/python/data/spot/daily/trades/ETHUSDT/ETHUSDT-trades-2025-01-01.zip -d submodules/binance-public-data/python/data/spot/daily/trades/ETHUSDT/
```

Examples

```bash
python -m data.binance_loader
python -m examples.backtest_eurusd_bar_low_level_api
python -m examples.backtest_eurusd_trade_high_level_api

python examples/mock_orderbook.py
python examples/mock_orderbook_depth.py

python examples/order_book_snapshot.py
python examples/evaluate_orders_report_with_vectorbt.py
```

## Todo

- [X] Able to load Binance Public Data into Nautilus Trader
  - [X] Bar
  - [X] TradeTick
- [X] Basic strategy backtesting using pre-defined data
- [X] Manually construct order book snapshot and backtest
- [ ] Try level 2 or higher order book data (Venue) => understand how the matching mechanism works (for different order types)
  - [ ] `L2_MBP`
  - [ ] `L3_MBO`
- [ ] Custom data backtesting => generate limit orders report is enough?!
- [ ] Unify and use better column names (currently following binance-public-data repository's README)
- [ ] Follow the refactor of Cython to PyO3

## Resources

### Nautilus Trader

- [NautilusTrader](https://nautilustrader.io/)
  - [nautechsystems/nautilus_trader: A high-performance algorithmic trading platform and event-driven backtester](https://github.com/nautechsystems/nautilus_trader)
    - [Roadmap](https://github.com/nautechsystems/nautilus_trader/blob/develop/ROADMAP.md)
    - [Kanban](https://github.com/orgs/nautechsystems/projects/3)
  - [nautechsystems/nautilus_data: Example data for use with NautilusTrader](https://github.com/nautechsystems/nautilus_data/)
  - [Discord](https://discord.com/invite/AUWVs3XaCS)
  - [Home · Loren1166/NautilusTrader- Wiki](https://github.com/Loren1166/NautilusTrader-/wiki) (Chinese documents)

Example

- Order Book Imbalance with limit order
  - [nautilus_trader/examples/backtest/crypto_orderbook_imbalance.py at develop · nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/crypto_orderbook_imbalance.py) - Use `BacktestEngine` ([low-level API](https://nautilustrader.io/docs/latest/getting_started/backtest_low_level/))
  - [nautilus_trader/nautilus_trader/examples/strategies/orderbook_imbalance.py at develop · nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader/blob/develop/nautilus_trader/examples/strategies/orderbook_imbalance.py#L78)
  - [Backtest: Binance OrderBook data | NautilusTrader Documentation](https://nautilustrader.io/docs/latest/tutorials/backtest_binance_orderbook) - Use `ImportableStrategyConfig` and `BacktestNode` ([high-level API](https://nautilustrader.io/docs/latest/getting_started/backtest_high_level/))
- Signal Strategy
  - [nautilus_trader/nautilus_trader/examples/strategies/signal_strategy.py at develop · nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader/blob/develop/nautilus_trader/examples/strategies/signal_strategy.py)
- Bar Strategy with market order (minimal reproducible example)
  - [nautilus_trader/examples/other/minimal_reproducible_example at develop · nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader/tree/develop/examples/other/minimal_reproducible_example)

### Data

- Binance
  - [How to Download Historical Market Data on Binance? | Binance Support](https://www.binance.com/en/support/faq/how-to-download-historical-market-data-on-binance-5810ae42176b4770b880ce1f14932262)
  - [binance/binance-public-data: Details on how to get Binance public data](https://github.com/binance/binance-public-data)
    - [Binance Data Collection](https://data.binance.vision/?prefix=data/spot/daily/trades/BTCUSDT/)
  - [Binance API Management](https://www.binance.com/en/my/settings/api-management): to get the API Key and Secret Key
  - Nautilus
    - [Binance Integration | NautilusTrader Documentation](https://nautilustrader.io/docs/latest/integrations/binance)
    - [Binance Adapter | NautilusTrader Documentation](https://nautilustrader.io/docs/latest/api_reference/adapters/binance/)
    - [#python #nautilus-trader #backtest #data #future #binance #orderbook #kline](https://gist.github.com/seongs1024/237ed08e9dae5b55bdd5c7a320c9c477)
- FX
  - [Download Free Forex Historical Data – HistData.com](https://www.histdata.com/download-free-forex-historical-data/?/ascii/tick-data-quotes/)
