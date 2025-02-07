from dotenv import load_dotenv
load_dotenv()

from config.db import connect_to_mysql, command, query

def seed_config():
    conn = connect_to_mysql()
    if conn is None: 
        return None
    rows = query("SELECT * FROM bot_config", dictionary=True)
    if rows:
        return
    command("INSERT INTO bot_config (MESSAGE_POINTS, MEDIA_POINTS, MAX_MESSAGE_POINTS, MAX_MEDIA_POINTS, REFERRED_MIN_ACTIVATION, REFERRAL_ACTIVE_DAYS, REFERRAL_POINTS, REFERRAL_LINK_ACTIVE_DAYS) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (100, 200, 700, 400 ,3, 3, 200, 3))

if __name__ == "__main__":
    seed_config()