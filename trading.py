
import ccxt
import pandas as pd
import numpy as np
import time
import logging

# Configure Logging
logging.basicConfig(filename='trading_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Configure API for Tokocrypto
exchange = ccxt.tokocrypto({
    'apiKey': '7165c7F9C775FC2AA9F49957A532Fe1BYq5PapHYxx34N8Ujuk7HMd8F0Uc1tGNY',
    'secret': '19F6aC8fF30c1CDAF4945Bde4073cA2BJpE5bOHwRRPZhsnp8UGgVlpbbmUWrla7',
    'enableRateLimit': True
})

# Fetch market data
def fetch_data(symbol, timeframe='1h', limit=200):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Calculate technical indicators
def calculate_indicators(df):
    df['SMA20'] = df['close'].rolling(window=20).mean()
    df['SMA50'] = df['close'].rolling(window=50).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['RSI'] = compute_rsi(df['close'], 14)
    return df

# RSI calculation
def compute_rsi(series, period=14):
    delta = series.diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Trading strategy with trailing stop loss
def trading_strategy(df, max_profit_tracker, initial_stop_loss=-0.4, trailing=True):
    current_profit = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
    if trailing and current_profit > max_profit_tracker[0]:
        max_profit_tracker[0] = current_profit
    trailing_stop = max((1 + initial_stop_loss) * (1 + max_profit_tracker[0]) - 1, initial_stop_loss)

    buy_signal = (df['SMA20'].iloc[-2] < df['SMA50'].iloc[-2] and df['SMA20'].iloc[-1] > df['SMA50'].iloc[-1] and 
                  df['RSI'].iloc[-1] < 70 and df['EMA20'].iloc[-1] > df['SMA20'].iloc[-1])
    sell_signal = (df['SMA20'].iloc[-2] > df['SMA50'].iloc[-2] and df['SMA20'].iloc[-1] < df['SMA50'].iloc[-1] and 
                   df['RSI'].iloc[-1] > 30 and df['EMA20'].iloc[-1] < df['SMA20'].iloc[-1] and 
                   current_profit < trailing_stop)

    return buy_signal, sell_signal

# Execute trades
def execute_trade(symbol, buy, sell, grid_percentage=0.1, max_grid_count=10):
    balance = exchange.fetch_balance()
    usdt_balance = balance['total'].get('USDT', 0)
    grid_size = usdt_balance * grid_percentage / max_grid_count
    
    if buy and usdt_balance >= grid_size:
        logging.info(f"Buying {grid_size} USDT worth of {symbol}")
        # exchange.create_market_buy_order(symbol, grid_size)
        
    elif sell and balance['free'].get(symbol.split('/')[0], 0) >= grid_size:
        logging.info(f"Selling {grid_size} of {symbol}")
        # exchange.create_market_sell_order(symbol, grid_size)

# Running the bot
symbol = 'BNB/USDT'
max_profit_tracker = [0]  # Keeps track of the highest profit reached

while True:
    df = fetch_data(symbol)
    df = calculate_indicators(df)
    buy, sell = trading_strategy(df, max_profit_tracker)
    execute_trade(symbol, buy, sell)
    
    time.sleep(3600)  # Run every hour
