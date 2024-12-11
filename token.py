import requests
from solana.rpc.api import Client
import logging
import time

# Konfigurasi API
RPC_URL = "https://api.mainnet-beta.solana.com"
SOLSCAN_API_URL = "https://api.solscan.io"
JUPITER_API_URL = "https://api.jup.ag/v1/price"
RUGDOC_API_URL = "https://api.rugdoc.io"
TELEGRAM_BOT_TOKEN = "masukkan_token_telegram_anda"
TELEGRAM_CHAT_ID = "masukkan_chat_id_anda"
TWITTER_BEARER_TOKEN = "masukkan_twitter_bearer_token_anda"

# Klien Solana
solana_client = Client(RPC_URL)

# Logging
logging.basicConfig(filename="token_analysis.log", level=logging.INFO)

def send_telegram_message(message):
    """
    Mengirim pesan ke Telegram.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        logging.error(f"Gagal mengirim pesan Telegram: {e}")

def get_new_tokens():
    """
    Mengambil daftar token baru dari Solscan.
    """
    try:
        response = requests.get(f"{SOLSCAN_API_URL}/token/new")
        if response.status_code == 200:
            tokens = response.json().get("data", [])
            return tokens
        else:
            logging.error("Gagal mengambil token baru dari Solscan.")
            return []
    except Exception as e:
        logging.error(f"Error fetching new tokens: {e}")
        return []

def check_liquidity_locked(token_address):
    """
    Periksa apakah likuiditas token terkunci.
    """
    try:
        response = requests.get(f"{SOLSCAN_API_URL}/token/holders?token={token_address}")
        if response.status_code == 200:
            holders = response.json().get("data", {}).get("holders", [])
            locked_wallets = [holder for holder in holders if "locked" in holder.get("tag", "").lower()]
            return len(locked_wallets) > 0
        return False
    except Exception as e:
        logging.error(f"Error checking liquidity: {e}")
        return False

def check_honeypot(token_address):
    """
    Periksa apakah token memiliki fungsi honeypot.
    """
    try:
        response = requests.get(f"{RUGDOC_API_URL}/honeypotCheck/{token_address}")
        if response.status_code == 200:
            data = response.json()
            return data.get("is_honeypot", True) == False
        return False
    except Exception as e:
        logging.error(f"Error checking honeypot: {e}")
        return False

def check_distribution(token_address):
    """
    Analisis distribusi token untuk mendeteksi risiko pump and dump.
    """
    try:
        response = requests.get(f"{SOLSCAN_API_URL}/token/holders?token={token_address}")
        if response.status_code == 200:
            holders = response.json().get("data", {}).get("holders", [])
            total_supply = sum(holder["amount"] for holder in holders)
            largest_holder = holders[0]["amount"] / total_supply if holders else 0
            return largest_holder < 0.2
        return False
    except Exception as e:
        logging.error(f"Error checking distribution: {e}")
        return False

def check_audit(token_address):
    """
    Periksa apakah token telah diaudit.
    """
    try:
        response = requests.get(f"{RUGDOC_API_URL}/audit/{token_address}")
        if response.status_code == 200:
            data = response.json()
            return data.get("auditScore", 0) > 70
        return False
    except Exception as e:
        logging.error(f"Error checking audit: {e}")
        return False

def check_liquidity(token_address):
    """
    Periksa likuiditas token di Jupiter Aggregator.
    """
    try:
        response = requests.get(f"{JUPITER_API_URL}?ids={token_address}")
        data = response.json()
        if token_address in data:
            liquidity = data[token_address].get("liquidity", 0)
            return liquidity > 50000  # Likuiditas minimum $50.000
        return False
    except Exception as e:
        logging.error(f"Error checking liquidity: {e}")
        return False

def check_token_metadata(token_address):
    """
    Periksa metadata token (nama, simbol, dan distribusi).
    """
    try:
        response = solana_client.get_account_info(token_address)
        if response["result"]["value"]:
            metadata = response["result"]["value"]["data"]
            if metadata:
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking token metadata: {e}")
        return False

def analyze_social_sentiment(token_symbol):
    """
    Analisis sentimen sosial menggunakan Twitter API.
    """
    url = f"https://api.twitter.com/2/tweets/search/recent?query={token_symbol}&tweet.fields=public_metrics"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tweets = response.json().get("data", [])
            positive_tweets = [tweet for tweet in tweets if tweet["public_metrics"]["like_count"] > 10]
            return len(positive_tweets) > 5
        else:
            logging.error("Gagal mengambil data sentimen dari Twitter.")
            return False
    except Exception as e:
        logging.error(f"Error analyzing social sentiment: {e}")
        return False

def analyze_tokens(tokens):
    """
    Analisis token baru untuk mendeteksi potensi.
    """
    potential_tokens = []
    for token in tokens:
        print(f"Menganalisis token: {token['symbol']} ({token['address']})...")
        has_liquidity = check_liquidity(token["address"])
        valid_metadata = check_token_metadata(token["address"])
        positive_sentiment = analyze_social_sentiment(token["symbol"])
        locked_liquidity = check_liquidity_locked(token["address"])
        no_honeypot = check_honeypot(token["address"])
        fair_distribution = check_distribution(token["address"])
        audited = check_audit(token["address"])

        if (
            has_liquidity
            and valid_metadata
            and positive_sentiment
            and locked_liquidity
            and no_honeypot
            and fair_distribution
            and audited
        ):
            potential_tokens.append(token)
            send_telegram_message(
                f"Token baru ditemukan: {token['symbol']} ({token['address']})\n"
                f"Likuiditas: $50k+\nSentimen sosial: Positif\n"
                f"Likuiditas Terkunci: Ya\nAudit: Ya\n"
            )
        else:
            logging.info(f"Token {token['symbol']} tidak memenuhi kriteria.")
    return potential_tokens

def main():
    while True:
        print("Mengambil token baru dari Solscan...")
        new_tokens = get_new_tokens()
        print(f"Token baru ditemukan: {len(new_tokens)}")

        print("\nMenganalisis token untuk potensi...")
        potential_tokens = analyze_tokens(new_tokens)

        print("\nToken dengan potensi besar:")
        for token in potential_tokens:
            print(f"{token['symbol']} - Alamat: {token['address']}")
        time.sleep(600)

if __name__ == "__main__":
    main()
