import os
import logging
import time
from tokocrypto import TokoCryptoAPI  # Pastikan Anda memiliki wrapper API untuk Tokocrypto
from dotenv import load_dotenv

# Memuat variabel lingkungan dari file .env
load_dotenv()

# Konfigurasi API dan Secret Key menggunakan variabel lingkungan
API_KEY = os.getenv('TOKOCRYPTO_API_KEY')
SECRET_KEY = os.getenv('TOKOCRYPTO_SECRET_KEY')

# Verifikasi apakah API key dan Secret key berhasil diambil
if not API_KEY or not SECRET_KEY:
    logging.error("API Key atau Secret Key tidak ditemukan!")
    exit()

# Inisialisasi API Tokocrypto
api = TokoCryptoAPI(API_KEY, SECRET_KEY)

# Konfigurasi Grid
MIN_ORDER = 6  # Minimal order dalam USDT
PROFIT_TARGET = 0.01  # Take profit target 1%
TRAILING_STOP_PERCENT = 0.005  # Trailing stop 0.5%
GRID_LEVELS = 10  # Jumlah grid
GRID_STEP_PERCENT = 0.01  # Setiap grid step adalah 1% dari harga pasar
ORDER_SIZE = 6  # Ukuran order dalam USDT

def get_balance():
    """Ambil saldo akun"""
    balance = api.get_balance()
    return balance['USDT']

def get_price(pair='USDT/USDT'):
    """Ambil harga terkini untuk pair tertentu"""
    price = api.get_price(pair)
    return price

def calculate_grid_levels(price, grid_levels=GRID_LEVELS, grid_step_percent=GRID_STEP_PERCENT):
    """Hitung grid level berdasarkan harga pasar"""
    grid_step = price * grid_step_percent  # Jarak antar grid
    grid_prices = [price - (grid_step * i) for i in range(grid_levels//2, 0, -1)]
    grid_prices.extend([price + (grid_step * i) for i in range(1, grid_levels//2 + 1)])
    return grid_prices

def place_order(price, amount, side='buy'):
    """Tempatkan order beli atau jual"""
    if side == 'buy':
        api.create_order('buy', price, amount)
    elif side == 'sell':
        api.create_order('sell', price, amount)

def execute_grid_trading():
    """Eksekusi trading grid otomatis"""
    balance = get_balance()
    if balance < MIN_ORDER:
        logging.info(f"Saldo kurang dari {MIN_ORDER} USDT, tidak dapat membuka posisi.")
        return
    
    price = get_price()  # Ambil harga pasar terkini
    grid_prices = calculate_grid_levels(price)

    # Tentukan jumlah grid berdasarkan saldo yang ada
    grid_amount = balance / GRID_LEVELS
    grid_amount = round(grid_amount, 2)  # Pembulatan agar sesuai dengan minimal order

    # Tempatkan order beli di harga grid
    for buy_price in grid_prices:
        if buy_price < price:  # Tempatkan order beli hanya pada harga lebih rendah dari harga pasar
            place_order(buy_price, grid_amount, side='buy')
            logging.info(f"Order beli ditempatkan di {buy_price} USDT.")
    
    # Tempatkan order jual di harga grid
    for sell_price in grid_prices:
        if sell_price > price:  # Tempatkan order jual hanya pada harga lebih tinggi dari harga pasar
            place_order(sell_price, grid_amount, side='sell')
            logging.info(f"Order jual ditempatkan di {sell_price} USDT.")
    
    # Periksa take profit dan trailing stop
    while True:
        time.sleep(10)  # Tunggu 10 detik sebelum periksa lagi
        price = get_price()  # Harga terkini
        for sell_price in grid_prices:
            if price >= sell_price * (1 + PROFIT_TARGET):  # Cek take profit
                place_order(sell_price, grid_amount, side='sell')
                logging.info(f"Take profit tercapai di {sell_price} USDT.")
                break

            # Trailing Stop Logic
            if price <= sell_price * (1 - TRAILING_STOP_PERCENT):  # Cek trailing stop loss
                place_order(sell_price, grid_amount, side='sell')
                logging.info(f"Trailing stop tercapai di {sell_price} USDT.")
                break

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    execute_grid_trading()
