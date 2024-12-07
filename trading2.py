import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from mnemonic import Mnemonic
from bip32utils import BIP32Key
from config import BOT_TOKEN, SEED_PHRASE, AXIOME_NODE_URL, OWNER_WALLET_ADDRESS, ADMIN_TELEGRAM_ID, AXM_PRICE_API_URL, TRANSACTION_FEE_PERCENTAGE

# Logging konfigurasi
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Validasi awal: cek seed phrase
if SEED_PHRASE is None:
    raise ValueError("SEED_PHRASE tidak ditemukan. Pastikan variabel lingkungan sudah disetel.")

# Penyimpanan transaksi pending
pending_transactions = {}

# Fungsi API Blockchain
def get_wallet_balance(wallet_address):
    try:
        url = f"{AXIOME_NODE_URL}/cosmos/bank/v1beta1/balances/{wallet_address}"
        response = requests.get(url)
        response.raise_for_status()
        balances = response.json().get("balances", [])
        for balance in balances:
            if balance["denom"] == "uaxiome":
                return float(balance["amount"]) / 1e6
        return 0.0
    except Exception as e:
        logging.error(f"Gagal mendapatkan saldo wallet: {e}")
        return 0.0

def get_axm_price():
    try:
        response = requests.get(AXM_PRICE_API_URL)
        response.raise_for_status()
        data = response.json()
        return data["axiome"]["usd"]
    except Exception as e:
        logging.error(f"Gagal mendapatkan harga AXM: {e}")
        raise

# Fungsi untuk memulai bot
def start(update: Update, context: CallbackContext):
    reply_keyboard = [
        ["💰 Saldo", "📤 Deposit"],
        ["📥 Withdraw", "🛒 Beli AXM", "💱 Jual AXM"]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    update.message.reply_text(
        "Selamat datang di bot jual/beli AXM! Pilih menu di bawah ini untuk melanjutkan.",
        reply_markup=reply_markup
    )

# Fungsi untuk menangani pembelian AXM
def buy(update: Update, context: CallbackContext):
    try:
        usd_amount = float(context.args[0])
        if usd_amount <= 0:
            update.message.reply_text("Jumlah harus lebih besar dari 0.")
            return

        axm_price = get_axm_price()
        axm_amount = usd_amount / axm_price
        fee = axm_amount * (TRANSACTION_FEE_PERCENTAGE / 100)
        total_axm = axm_amount - fee
        user_id = update.effective_user.id

        # Simpan transaksi ke daftar pending
        transaction_id = len(pending_transactions) + 1
        pending_transactions[transaction_id] = {
            "user_id": user_id,
            "usd_amount": usd_amount,
            "axm_amount": total_axm,
            "fee": fee,
            "status": "pending"
        }

        update.message.reply_text(f"Transaksi Anda sedang menunggu konfirmasi admin.")
        context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=(
                f"Konfirmasi Pembelian AXM:\n"
                f"ID Transaksi: {transaction_id}\n"
                f"User: {user_id}\n"
                f"Jumlah: {total_axm:.2f} AXM (USD: {usd_amount:.2f}, Fee: {fee:.2f})\n\n"
                f"/confirm {transaction_id} untuk konfirmasi\n"
                f"/reject {transaction_id} untuk menolak"
            )
        )
    except (IndexError, ValueError):
        update.message.reply_text("Gunakan format: /buy <jumlah_usd>")

# Fungsi untuk menangani teks dari Reply Keyboard
def handle_text(update: Update, context: CallbackContext):
    text = update.message.text

    if text == "💰 Saldo":
        balance = get_wallet_balance(OWNER_WALLET_ADDRESS)
        update.message.reply_text(f"Saldo Anda: {balance:.2f} AXM")
    elif text == "📤 Deposit":
        update.message.reply_text(f"Silakan kirim AXM ke alamat berikut:\n{OWNER_WALLET_ADDRESS}")
    elif text == "📥 Withdraw":
        update.message.reply_text("Untuk penarikan, hubungi admin dengan format: /withdraw <jumlah>")
    elif text == "🛒 Beli AXM":
        update.message.reply_text("Gunakan perintah: /buy <jumlah_usd> untuk membeli AXM.")
    elif text == "💱 Jual AXM":
        update.message.reply_text("Untuk menjual AXM, hubungi admin dengan format: /sell <jumlah>")
    else:
        update.message.reply_text("Pilihan tidak valid. Silakan pilih menu yang tersedia.")

# Fungsi konfirmasi transaksi
def confirm_transaction(update: Update, context: CallbackContext):
    try:
        transaction_id = int(context.args[0])
        transaction = pending_transactions.get(transaction_id)

        if not transaction or transaction["status"] != "pending":
            update.message.reply_text("Transaksi tidak ditemukan atau sudah diproses.")
            return

        # Eksekusi transaksi
        transaction["status"] = "confirmed"

        update.message.reply_text(f"Transaksi ID {transaction_id} telah dikonfirmasi.")
        context.bot.send_message(
            chat_id=transaction["user_id"],
            text=f"Transaksi pembelian Anda (ID: {transaction_id}) telah dikonfirmasi. Anda menerima {transaction['axm_amount']:.2f} AXM."
        )
    except (IndexError, ValueError):
        update.message.reply_text("Gunakan format: /confirm <id>")

# Fungsi menolak transaksi
def reject_transaction(update: Update, context: CallbackContext):
    try:
        transaction_id = int(context.args[0])
        transaction = pending_transactions.get(transaction_id)

        if not transaction or transaction["status"] != "pending":
            update.message.reply_text("Transaksi tidak ditemukan atau sudah diproses.")
            return

        transaction["status"] = "rejected"
        update.message.reply_text(f"Transaksi ID {transaction_id} telah ditolak.")
        context.bot.send_message(
            chat_id=transaction["user_id"],
            text=f"Transaksi pembelian Anda (ID: {transaction_id}) telah ditolak oleh admin."
        )
    except (IndexError, ValueError):
        update.message.reply_text("Gunakan format: /reject <id>")

# Fungsi utama untuk menjalankan bot
def main():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("buy", buy))
    dispatcher.add_handler(CommandHandler("confirm", confirm_transaction))
    dispatcher.add_handler(CommandHandler("reject", reject_transaction))

    # Reply keyboard handler
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
