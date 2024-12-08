import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters, CallbackQueryHandler
from config import BOT_TOKEN, ADMIN_TELEGRAM_ID, USDT_BEP20_ADDRESS, PAYPAL_ADDRESS, AXM_PRICE_API_URL

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Penyimpanan saldo pengguna dan transaksi
user_balances = {}  # {user_id: {"idr_balance": 0, "axm_balance": 0}}
pending_transactions = {}

# Mendapatkan harga AXM
def get_axm_price():
    try:
        response = requests.get(AXM_PRICE_API_URL)
        response.raise_for_status()
        data = response.json()
        return data["axiome"]["usd"]
    except Exception as e:
        logging.error(f"Gagal mendapatkan harga AXM: {e}")
        return 0.0

# Mulai bot
def start(update: Update, context: CallbackContext):
    reply_keyboard = [
        ["💰 Saldo", "📤 Deposit"],
        ["📥 Withdraw", "🛒 Beli AXM"]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    update.message.reply_text(
        "Selamat datang di bot jual/beli AXM! Pilih menu di bawah ini untuk melanjutkan.",
        reply_markup=reply_markup
    )

# 💰 Saldo
def check_balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    balance = user_balances.get(user_id, {"idr_balance": 0, "axm_balance": 0})

    reply_keyboard = [["🛒 Beli AXM", "Batalkan"]]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    update.message.reply_text(
        f"ℹ Kamu memiliki saldo sebesar Rp {balance['idr_balance']} dan {balance['axm_balance']} AXM.",
        reply_markup=reply_markup
    )

# 📤 Deposit
def deposit(update: Update, context: CallbackContext):
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Via USDT", callback_data='deposit_usdt')],
        [InlineKeyboardButton("PayPal", callback_data='deposit_paypal')]
    ])
    update.message.reply_text("Silahkan pilih metode pembayaran di bawah ini:", reply_markup=reply_markup)

def handle_deposit_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id

    if query.data == 'deposit_usdt':
        query.edit_message_text("Silahkan masukkan nominal USD yang akan didepositkan:")
        context.user_data['method'] = 'usdt'
    elif query.data == 'deposit_paypal':
        query.edit_message_text("Silahkan masukkan nominal USD yang akan didepositkan:")
        context.user_data['method'] = 'paypal'

def process_deposit(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    try:
        nominal = float(user_input)
        if nominal <= 0:
            raise ValueError("Nominal harus lebih besar dari 0.")
    except ValueError:
        update.message.reply_text("Input tidak valid. Masukkan nominal dalam angka, misalnya: 50.")
        return

    method = context.user_data.get('method')
    transaction_id = len(pending_transactions) + 1
    fee = nominal * 0.012  # Contoh fee 1.2%
    unique_code = int(str(user_id)[-3:])  # 3 digit unik
    total_payment = nominal + fee + (unique_code / 1000)

    pending_transactions[transaction_id] = {
        "user_id": user_id,
        "amount": nominal,
        "fee": fee,
        "unique_code": unique_code,
        "method": method,
        "status": "waiting"
    }

    payment_info = ""
    if method == 'usdt':
        payment_info = f"Kirim {total_payment:.3f} USDT ke alamat berikut (BEP20):\n\n{USDT_BEP20_ADDRESS}\n\n"
    elif method == 'paypal':
        payment_info = f"Kirim {total_payment:.3f} USD ke alamat PayPal berikut:\n\n{PAYPAL_ADDRESS}\n\n"

    context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=f"Konfirmasi Deposit:\nID Transaksi: {transaction_id}\nUser: {user_id}\nJumlah: {nominal:.2f} USD\nMetode: {method}\n\n/confirm {transaction_id} untuk konfirmasi\n/reject {transaction_id} untuk menolak"
    )

    update.message.reply_text(
        f"Permintaan Deposit Anda telah dikonfirmasi. {payment_info}"
        f"Pastikan Anda mengirim jumlah dengan kode unik {unique_code} untuk mempermudah identifikasi."
    )

# 🛒 Beli AXM
def buy_axm(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    balance = user_balances.get(user_id, {"idr_balance": 0, "axm_balance": 0})

    if balance['idr_balance'] <= 0:
        update.message.reply_text("Saldo anda adalah Rp 0. Silahkan deposit terlebih dahulu.", reply_markup=ReplyKeyboardMarkup([["Batalkan"]], resize_keyboard=True))
        return

    update.message.reply_text("Silahkan masukkan nominal dalam Rp yang ingin dibelanjakan:")
    context.user_data['menu'] = 'buy_axm'

def process_buy_axm(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    try:
        nominal = float(user_input)
        if nominal <= 0:
            raise ValueError("Nominal harus lebih besar dari 0.")
    except ValueError:
        update.message.reply_text("Input tidak valid. Masukkan nominal dalam angka, misalnya: 100000.")
        return

    axm_price = get_axm_price() * 15000  # Konversi ke IDR
    axm_amount = nominal / axm_price
    fee = axm_amount * 0.01
    total_axm = axm_amount - fee

    balance = user_balances.get(user_id, {"idr_balance": 0, "axm_balance": 0})
    if balance['idr_balance'] < nominal:
        update.message.reply_text("Saldo IDR Anda tidak mencukupi untuk transaksi ini.")
        return

    balance['idr_balance'] -= nominal
    balance['axm_balance'] += total_axm
    user_balances[user_id] = balance

    update.message.reply_text(f"Pembelian berhasil! Anda menerima {total_axm:.2f} AXM.")

# 📥 Withdraw
def withdraw(update: Update, context: CallbackContext):
    update.message.reply_text("Silahkan masukkan nominal AXM yang akan ditarik:")
    context.user_data['menu'] = 'withdraw'

def process_withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    try:
        nominal = float(user_input)
        if nominal <= 0:
            raise ValueError("Nominal harus lebih besar dari 0.")
    except ValueError:
        update.message.reply_text("Input tidak valid. Masukkan nominal dalam angka, misalnya: 10.")
        return

    update.message.reply_text("Masukkan alamat AXM Anda:")
    context.user_data['withdraw_amount'] = nominal

def finalize_withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    wallet_address = update.message.text.strip()
    nominal = context.user_data.get('withdraw_amount')

    # Kirim notifikasi ke admin
    context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=f"Konfirmasi Withdraw:\nUser: {user_id}\nJumlah: {nominal} AXM\nAlamat: {wallet_address}\n\n"
             f"/confirmwd {user_id} untuk konfirmasi\n/rejectwd {user_id} untuk menolak"
    )
    update.message.reply_text(
        "Permintaan withdraw Anda telah diteruskan ke admin. Silakan tunggu konfirmasi lebih lanjut."
    )

def confirm_withdraw(update: Update, context: CallbackContext):
    try:
        user_id = int(context.args[0])
        txn_hash = context.args[1]  # Hash transaksi yang diberikan admin
        nominal = context.user_data.get("withdraw_amount")

        # Perbarui saldo pengguna
        balance = user_balances.get(user_id, {"idr_balance": 0, "axm_balance": 0})
        if balance["axm_balance"] < nominal:
            update.message.reply_text("Saldo AXM pengguna tidak mencukupi untuk transaksi ini.")
            return

        balance["axm_balance"] -= nominal
        user_balances[user_id] = balance

        # Kirim notifikasi ke pengguna
        context.bot.send_message(
            chat_id=user_id,
            text=f"Withdraw sebesar {nominal} AXM telah berhasil dikirim. Bukti transaksi:\n\n{txn_hash}"
        )
        update.message.reply_text(f"Withdraw untuk pengguna {user_id} telah berhasil dikonfirmasi.")
    except (IndexError, ValueError):
        update.message.reply_text("Gunakan format: /confirmwd <user_id> <txn_hash>")

def reject_withdraw(update: Update, context: CallbackContext):
    try:
        user_id = int(context.args[0])

        # Kirim notifikasi ke pengguna
        context.bot.send_message(
            chat_id=user_id,
            text="Permintaan withdraw Anda telah ditolak oleh admin."
        )
        update.message.reply_text(f"Withdraw untuk pengguna {user_id} telah ditolak.")
    except (IndexError, ValueError):
        update.message.reply_text("Gunakan format: /rejectwd <user_id>")

def main():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("buy", buy_axm))
    dispatcher.add_handler(CommandHandler("deposit", deposit))
    dispatcher.add_handler(CommandHandler("confirmwd", confirm_withdraw))
    dispatcher.add_handler(CommandHandler("rejectwd", reject_withdraw))

    # Callback query handler untuk deposit
    dispatcher.add_handler(CallbackQueryHandler(handle_deposit_callback))

    # Message handlers
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_buy_axm))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_deposit))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_withdraw))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, finalize_withdraw))

    updater.start_polling()
    updater.idle()
