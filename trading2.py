import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
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

# Fungsi untuk konversi seed phrase ke private key
def get_private_key_from_seed(seed_phrase):
    if not seed_phrase:
        raise ValueError("Seed phrase tidak valid atau kosong.")
    try:
        mnemo = Mnemonic("english")
        seed = mnemo.to_seed(seed_phrase)
        master_key = BIP32Key.fromEntropy(seed)
        child_key = master_key.ChildKey(44 + BIP32Key.HARDEN).ChildKey(118 + BIP32Key.HARDEN).ChildKey(0 + BIP32Key.HARDEN).ChildKey(0).ChildKey(0)
        return child_key.PrivateKey().hex()
    except Exception as e:
        raise ValueError(f"Kesalahan saat memproses seed phrase: {e}")

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

def send_transaction(from_address, to_address, amount, seed_phrase):
    try:
        private_key = get_private_key_from_seed(seed_phrase)
        payload = {
            "from": from_address,
            "to": to_address,
            "amount": int(amount * 1e6),
            "private_key": private_key,
        }
        url = f"{AXIOME_NODE_URL}/transaction/send"
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Transaksi berhasil: {response.json()}")
        return response.json()
    except Exception as e:
        logging.error(f"Kesalahan saat mengirim transaksi: {e}")
        raise

# Fungsi untuk mendapatkan harga AXM secara real-time
def get_axm_price():
    try:
        response = requests.get(AXM_PRICE_API_URL)
        response.raise_for_status()
        data = response.json()
        return data["axiome"]["usd"]
    except Exception as e:
        logging.error(f"Gagal mendapatkan harga AXM: {e}")
        raise

# Handlers Bot
def start(update: Update, context: CallbackContext):
    # Inline keyboard (default)
    inline_keyboard = [
        [InlineKeyboardButton("Saldo", callback_data="balance")],
        [InlineKeyboardButton("Deposit", callback_data="deposit")],
        [InlineKeyboardButton("Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("Beli AXM", callback_data="buy")],
        [InlineKeyboardButton("Jual AXM", callback_data="sell")],
    ]
    inline_reply_markup = InlineKeyboardMarkup(inline_keyboard)

    # Reply keyboard (gantikan keyboard fisik)
    reply_keyboard = [
        ["💎 Transaksi", "📤 Deposit", "💰 Saldo"],
        ["💱 Tukar Poin", "👤 Profil", "📱 Nomor Seri"],
        ["💌 Referral", "💬 Customer Care", "ℹ️ Informasi"],
        ["🎉 Fitur Tambahan", "✅ Absent"]
    ]
    reply_reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    # Kirim pesan dengan dua opsi keyboard
    update.message.reply_text(
        "Selamat datang di bot jual/beli AXM!\nPilih menu di bawah (Inline Keyboard) atau gunakan Reply Keyboard.",
        reply_markup=inline_reply_markup  # Tetap gunakan Inline Keyboard
    )
    update.message.reply_text(
        "Berikut adalah menu utama Anda:",
        reply_markup=reply_reply_markup  # Tambahkan Reply Keyboard
    )

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

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text

    if text == "💎 Transaksi":
        update.message.reply_text("Anda memilih menu Transaksi. Silakan lanjutkan.")
    elif text == "📤 Deposit":
        update.message.reply_text(f"Silakan kirim AXM ke alamat berikut:\n{OWNER_WALLET_ADDRESS}")
    elif text == "💰 Saldo":
        balance = get_wallet_balance(OWNER_WALLET_ADDRESS)
        update.message.reply_text(f"Saldo Anda: {balance:.2f} AXM")
    elif text == "✅ Absent":
        update.message.reply_text("Anda telah absen hari ini. Terima kasih!")
    else:
        update.message.reply_text("Pilihan tidak valid. Silakan pilih menu yang tersedia.")


def confirm_transaction(update: Update, context: CallbackContext):
    try:
        transaction_id = int(context.args[0])
        transaction = pending_transactions.get(transaction_id)

        if not transaction or transaction["status"] != "pending":
            update.message.reply_text("Transaksi tidak ditemukan atau sudah diproses.")
            return

        # Eksekusi transaksi
        send_transaction(
            OWNER_WALLET_ADDRESS,
            transaction["user_id"],
            transaction["axm_amount"],
            SEED_PHRASE
        )
        transaction["status"] = "confirmed"

        update.message.reply_text(f"Transaksi ID {transaction_id} telah dikonfirmasi.")
        context.bot.send_message(
            chat_id=transaction["user_id"],
            text=f"Transaksi pembelian Anda (ID: {transaction_id}) telah dikonfirmasi. Anda menerima {transaction['axm_amount']:.2f} AXM."
        )
    except (IndexError, ValueError):
        update.message.reply_text("Gunakan format: /confirm <id>")

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

# Main Function
def main():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("buy", buy))
    dispatcher.add_handler(CommandHandler("confirm", confirm_transaction))
    dispatcher.add_handler(CommandHandler("reject", reject_transaction))
    
    # Inline keyboard handler
    dispatcher.add_handler(CallbackQueryHandler(menu_handler))

    # Reply keyboard handler (menangani teks)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
