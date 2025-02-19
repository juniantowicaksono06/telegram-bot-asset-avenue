import mysql.connector
from mysql.connector import Error
import os
import requests
import datetime
from dotenv import load_dotenv

load_dotenv()

def send_telegram_message(message):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("USER_BOT_CHECK_ID")  # Your Telegram user ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def check_connection():
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),  # Replace with your database host
            user=os.getenv("DB_USER"),       # Replace with your database username
            password=os.getenv("DB_PASS"),  # Replace with your database password
            database=os.getenv("DB_NAME"),  # Replace with your database name
            port=os.getenv("DB_PORT")
        )

        if connection.is_connected():
            send_telegram_message(f"✅ Database is working correctly! Time on server is: {str(datetime.datetime.now())}")
    except Error as e:
        send_telegram_message(f"❌ Database is not working! Time on server is: {str(datetime.datetime.now())}")
        pass

if __name__ == "__main__":
    check_connection()