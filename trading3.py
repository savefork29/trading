
import time
import math
import logging
from binance.client import Client

# Configuring logging
logging.basicConfig(level=logging.INFO)
logging.info("Memulai bot trading...")

# API setup - Replace these with your actual API keys
API_KEY = 'your_api_key'
API_SECRET = 'your_secret_key'
client = Client(API_KEY, API_SECRET)

# Parameters for trading strategy
PAIR = 'BNBUSDT'
TAKE_PROFIT_PERCENT = 0.01  # 1% Take Profit
TRAILING_STOP_LOSS_PERCENT = 0.005  # 0.5% Trailing Stop Loss
GRID_INTERVAL = 0.002  # 0.2% grid interval
TRADE_AMOUNT = 0.001  # Adjust to the desired amount of BNB to trade

# Tracking variables
buy_price = None
take_profit_price = None
highest_price = None

def get_balance(asset):
    balance = client.get_asset_balance(asset=asset)
    return float(balance['free'])

def get_price():
    ticker = client.get_symbol_ticker(symbol=PAIR)
    return float(ticker['price'])

def buy():
    global buy_price, take_profit_price, highest_price
    try:
        order = client.order_market_buy(symbol=PAIR, quantity=TRADE_AMOUNT)
        buy_price = get_price()
        take_profit_price = buy_price * (1 + TAKE_PROFIT_PERCENT)
        highest_price = buy_price
        logging.info(f"Berhasil membeli di harga: {buy_price} USDT.")
    except Exception as e:
        logging.error(f"Gagal membeli: {e}")

def sell():
    global buy_price, take_profit_price, highest_price
    try:
        order = client.order_market_sell(symbol=PAIR, quantity=TRADE_AMOUNT)
        logging.info(f"Berhasil menjual di harga: {get_price()} USDT.")
        # Reset tracking variables after a successful sell
        buy_price = None
        take_profit_price = None
        highest_price = None
    except Exception as e:
        logging.error(f"Gagal menjual: {e}")

def trailing_stop_loss(current_price):
    global take_profit_price, highest_price
    if current_price > highest_price:
        highest_price = current_price
        take_profit_price = highest_price * (1 - TRAILING_STOP_LOSS_PERCENT)
        logging.info(f"Harga tertinggi baru: {highest_price} USDT. Memperbarui trailing stop loss ke: {take_profit_price} USDT.")
    elif current_price <= take_profit_price:
        logging.info(f"Harga mencapai trailing stop loss di {current_price} USDT.")
        sell()

def trade():
    if get_balance('USDT') < TRADE_AMOUNT * get_price():
        logging.info("Saldo USDT tidak mencukupi. Tambahkan saldo untuk memulai trading.")
        return

    current_price = get_price()
    logging.info(f"Harga saat ini: {current_price} USDT.")

    if not buy_price:
        buy()
    else:
        trailing_stop_loss(current_price)

if __name__ == "__main__":
    while True:
        try:
            trade()
            time.sleep(60)  # Delay between each trade check
        except Exception as e:
            logging.error(f"Error dalam loop utama: {e}")
