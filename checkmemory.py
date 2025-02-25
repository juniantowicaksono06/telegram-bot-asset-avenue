import psutil
import time
import os
import requests
from dotenv import load_dotenv
load_dotenv()

MEMORY_THRESHOLD_MB = int(os.getenv("LOW_MEMORY_CHECK_THRESHOLD"))
CHECK_INTERVAL_SECONDS = int(os.getenv("LOW_MEMORY_CHECK_INTERVAL"))  # Check every 80 seconds


def send_telegram_message(message):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("USER_BOT_CHECK_ID")  # Your Telegram user ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    print("SENDING MESSAGE")
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_available_memory_mb():
    """Mengembalikan memori yang tersedia dalam MB."""
    return psutil.virtual_memory().available / (1024 * 1024)

def main():
    print("Running checking memory... Press CTRL+C to quit!")
    while True:
        available_memory = get_available_memory_mb()
        if available_memory < MEMORY_THRESHOLD_MB:
            print("MEMORY IS LOW")
            message = f"⚠️ Warning! Memory is low. Left {available_memory:.2f}MB."
            send_telegram_message(message)
        else:
            print("MEMORY IS OK!")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()