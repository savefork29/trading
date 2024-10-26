
import logging
import time
import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logging.info("Memulai bot trading...")

class TradingBot:
    def __init__(self, client, symbol, grid_buy_orders, grid_sell_orders, take_profit=0.01, trailing_stop_loss_percent=0.02):
        self.client = client
        self.symbol = symbol
        self.grid_buy_orders = grid_buy_orders
        self.grid_sell_orders = grid_sell_orders
        self.take_profit = take_profit
        self.trailing_stop_loss_percent = trailing_stop_loss_percent
        self.highest_price = 0
        self.trailing_stop_loss = None
        self.indicator_data = []

    def check_balance(self):
        balance = self.client.get_balance("USDT")
        if balance < 10:
            logging.info(f"Saldo USDT tidak mencukupi: {balance} USDT. Tambahkan saldo untuk memulai trading.")
            return False
        return True

    def fetch_price(self):
        response = requests.get(f'https://api.tokocrypto.com/v1/market/trades?symbol={self.symbol}')
        return float(response.json()['price'])

    def update_indicators(self, price):
        self.indicator_data.append(price)
        if len(self.indicator_data) > 20:
            self.indicator_data.pop(0)
        sma = sum(self.indicator_data) / len(self.indicator_data) if len(self.indicator_data) > 0 else 0
        rsi = self.calculate_rsi()
        logging.info(f"Indikator: SMA={sma}, RSI={rsi}")

    def calculate_rsi(self, period=14):
        if len(self.indicator_data) < period:
            return None
        gains = [self.indicator_data[i] - self.indicator_data[i - 1] for i in range(1, period) if self.indicator_data[i] > self.indicator_data[i - 1]]
        losses = [-self.indicator_data[i] + self.indicator_data[i - 1] for i in range(1, period) if self.indicator_data[i] < self.indicator_data[i - 1]]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 1
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def place_order(self, side, quantity):
        logging.info(f"Menempatkan order {side} sebanyak {quantity} {self.symbol}.")

    def update_trailing_stop_loss(self, current_price):
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.trailing_stop_loss = self.highest_price * (1 - self.trailing_stop_loss_percent)
            logging.info(f"Update trailing stop loss ke: {self.trailing_stop_loss}")

    def should_sell(self, current_price):
        if self.trailing_stop_loss is not None and current_price <= self.trailing_stop_loss:
            logging.info(f"Harga mencapai trailing stop loss: {current_price}. Menjual...")
            return True
        return False

    def start_trading(self):
        if not self.check_balance():
            return

        while True:
            current_price = self.fetch_price()
            self.update_indicators(current_price)
            self.update_trailing_stop_loss(current_price)

            if self.should_sell(current_price):
                self.place_order("sell", quantity=1)
                self.trailing_stop_loss = None

            time.sleep(10)

class TokocryptoClient:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def get_balance(self, asset):
        # Simulasi panggilan ke endpoint API saldo Tokocrypto
        # Sesuaikan endpoint sebenarnya jika Anda mengakses API langsung
        logging.info(f"Mengambil saldo {asset}.")
        # Contoh saldo
        return 100  # Angka ini bisa Anda ubah sesuai saldo di akun Anda

# Masukkan API Key dan Secret Key
api_key = "YOUR_API_KEY"
secret_key = "YOUR_SECRET_KEY"

# Inisialisasi client dan bot trading
client = TokocryptoClient(api_key, secret_key)
symbol = "BNBUSDT"
bot = TradingBot(client, symbol, grid_buy_orders=5, grid_sell_orders=5, take_profit=0.01, trailing_stop_loss_percent=0.02)
bot.start_trading()
