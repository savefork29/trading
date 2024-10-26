
import ccxt
import pandas as pd
import numpy as np
import time
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)  # Atur level ke INFO atau DEBUG
logging.info("Memulai bot trading...")

# Koneksi ke Tokocrypto
exchange = ccxt.tokocrypto({
    'apiKey': 'API_KEY_ANDA',
    'secret': 'SECRET_KEY_ANDA',
})

symbol = 'BNB/USDT'
interval = '5m'  # Atur interval
amount_per_trade = 0.001  # Ukuran trade per grid
grid_levels = 5  # Jumlah grid
grid_size = 0.01  # Ukuran perubahan harga grid dalam %

# Fungsi untuk mengecek saldo USDT
def check_usdt_balance():
    balance = exchange.fetch_balance()
    usdt_balance = balance.get('total', {}).get('USDT', 0)
    if usdt_balance < amount_per_trade * grid_levels:
        logging.info(f"Saldo USDT tidak mencukupi: {usdt_balance} USDT. Tambahkan saldo untuk memulai trading.")
        return False
    else:
        logging.info(f"Saldo USDT mencukupi: {usdt_balance} USDT.")
        return True

# Fungsi untuk mengumpulkan data OHLCV
def fetch_data():
    ohlcv = exchange.fetch_ohlcv(symbol, interval)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Fungsi untuk menghitung indikator RSI
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Fungsi grid trading
def place_grid_orders(df):
    last_price = df['close'].iloc[-1]
    grid_prices = [last_price * (1 + grid_size * i) for i in range(-grid_levels, grid_levels + 1)]
    for price in grid_prices:
        logging.info(f"Grid order ditempatkan pada harga: {price:.4f} USDT")

# Fungsi untuk trailing stop loss
def trailing_stop_loss(current_price, entry_price, stop_loss_percent=0.02):
    stop_loss_price = entry_price * (1 - stop_loss_percent)
    if current_price <= stop_loss_price:
        logging.info(f"Trailing Stop Loss triggered at {stop_loss_price:.4f} USDT.")
        return True
    return False

# Fungsi utama
def main():
    if not check_usdt_balance():
        return

    logging.info("Memulai bot trading untuk pasangan %s", symbol)
    
    while True:
        try:
            df = fetch_data()
            df['RSI'] = calculate_rsi(df)

            last_rsi = df['RSI'].iloc[-1]
            last_price = df['close'].iloc[-1]

            if last_rsi < 30:
                logging.info(f"Membeli pada harga {last_price:.4f} USDT dengan RSI {last_rsi:.2f}")
                entry_price = last_price
                place_grid_orders(df)
            elif last_rsi > 70:
                logging.info(f"Menjual pada harga {last_price:.4f} USDT dengan RSI {last_rsi:.2f}")
            
            if trailing_stop_loss(last_price, entry_price):
                logging.info("Trailing stop loss dieksekusi. Menjual posisi.")
                entry_price = None

            time.sleep(10)  # Tunggu 10 detik sebelum iterasi berikutnya

        except ccxt.BaseError as e:
            logging.error(f"Kesalahan pada API Exchange: {str(e)}")
            time.sleep(5)  # Tunggu sebelum mencoba kembali

if __name__ == "__main__":
    main()
