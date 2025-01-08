# Nautilus Trader Example

## Getting Started

Python 3.11+

```bash
pip install -r requirements.txt
pip install -r submodules/binance-public-data/python/requirements.txt
```

Data

```bash
# NOTE: Pandas can load csv from zip directly
python submodules/binance-public-data/python/download-trade.py -d 2025-01-01 -s ETHUSDT -t spot
# unzip submodules/binance-public-data/python/data/spot/daily/trades/ETHUSDT/ETHUSDT-trades-2025-01-01.zip -d submodules/binance-public-data/python/data/spot/daily/trades/ETHUSDT/

python submodules/binance-public-data/python/download-kline.py -d 2025-01-01 -s ETHUSDT -t spot -i 1s
# unzip submodules/binance-public-data/python/data/spot/daily/klines/ETHUSDT/1s/ETHUSDT-1s-2025-01-01.zip -d submodules/binance-public-data/python/data/spot/daily/klines/ETHUSDT/1s/
```

## Todo

- [ ] Able to load Binance Public Data into Nautilus Trader
  - [ ] Bar
  - [ ] TradeTick
- [ ] Basic strategy backtesting using pre-defined data
- [ ] Custom data backtesting

## Resources

### Nautilus Trader

- [NautilusTrader](https://nautilustrader.io/)
  - [nautechsystems/nautilus_trader: A high-performance algorithmic trading platform and event-driven backtester](https://github.com/nautechsystems/nautilus_trader)
  - [nautechsystems/nautilus_data: Example data for use with NautilusTrader](https://github.com/nautechsystems/nautilus_data/)
  - [Discord](https://discord.com/invite/AUWVs3XaCS)
  - [Home · Loren1166/NautilusTrader- Wiki](https://github.com/Loren1166/NautilusTrader-/wiki) (Chinese documents)

Example

- Order Book Imbalance
  - [nautilus_trader/examples/backtest/crypto_orderbook_imbalance.py at develop · nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader/blob/develop/examples/backtest/crypto_orderbook_imbalance.py) - Use `BacktestEngine` ([low-level API](https://nautilustrader.io/docs/latest/getting_started/backtest_low_level/))
  - [Backtest: Binance OrderBook data | NautilusTrader Documentation](https://nautilustrader.io/docs/latest/tutorials/backtest_binance_orderbook) - Use `ImportableStrategyConfig` and `BacktestNode` ([high-level API](https://nautilustrader.io/docs/latest/getting_started/backtest_high_level/))
- Signal Strategy
  - [nautilus_trader/nautilus_trader/examples/strategies/signal_strategy.py at develop · nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader/blob/develop/nautilus_trader/examples/strategies/signal_strategy.py)

### Data

- Binance
  - [How to Download Historical Market Data on Binance? | Binance Support](https://www.binance.com/en/support/faq/how-to-download-historical-market-data-on-binance-5810ae42176b4770b880ce1f14932262)
  - [binance/binance-public-data: Details on how to get Binance public data](https://github.com/binance/binance-public-data)
    - [Binance Data Collection](https://data.binance.vision/?prefix=data/spot/daily/trades/BTCUSDT/)
