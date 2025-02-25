import psutil
import time
import os
import requests

MEMORY_THRESHOLD_MB = 150
CHECK_INTERVAL_SECONDS = 80  # Check every 80 seconds


def send_telegram_message(message):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("USER_BOT_CHECK_ID")  # Your Telegram user ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_available_memory_mb():
    """Mengembalikan memori yang tersedia dalam MB."""
    return psutil.virtual_memory().available / (1024 * 1024)

def main():
    while True:
        available_memory = get_available_memory_mb()
        if available_memory < MEMORY_THRESHOLD_MB:
            message = f"Warning! Memory is low. Left {available_memory:.2f}MB."
            send_telegram_message(message)
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()