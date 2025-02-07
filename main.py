from dotenv import load_dotenv
from config.db import connect_to_mysql, command, query
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ChatJoinRequestHandler
import os
import pandas as pd

import openpyxl
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
import datetime
from utils import ordinal, plural_number
load_dotenv()

# Aturan poin
MESSAGE_POINTS = 100
MEDIA_POINTS = 200
MAX_MESSAGE_POINTS = 700
MAX_MEDIA_POINTS = 400
REFERRAL_ACTIVE_DAYS = 10
REFERRED_MIN_ACTIVATION = 3
REFERRAL_POINTS = 200
REFERRAL_LINK_ACTIVE_DAYS = 3

def register_user(user_id, username, first_name, last_name, group_id):
    # Register user if not exists
    data = query("SELECT user_id FROM users WHERE user_id = %s", (user_id,), single=True)
    if(data) is None:
        result = command("INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s)", (user_id, username, first_name, last_name)) 
        if result is not None:
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            data_user = query("SELECT id FROM users WHERE user_id = %s", (user_id,), single=True)
            print(data_user['id'], 0, 'registration', 100, current_date, group_id)
            command("INSERT INTO scores (user_id, message_id, activity_type, score, date, group_id) VALUES (%s, %s, %s, %s, %s, %s)", (data_user['id'], 0, 'registration', 100, current_date, group_id))

        
    return True

def get_daily_points(user_id, activity_type, group_id):
    """Hitung total poin harian pengguna berdasarkan jenis aktivitas."""
    data = query("SELECT COALESCE(SUM(score), 0) as score FROM scores LEFT JOIN users ON scores.user_id = users.id WHERE users.user_id = %s AND activity_type = %s AND DATE(`date`) = CURDATE()", (user_id, activity_type), single=True)
    print(data)
    return data['score']

def add_points(update: Update, user_id, message_id, group_id, activity_type, points, max_points):
    """Tambahkan poin ke database dengan batas maksimal per hari."""
    current_points = int(get_daily_points(user_id, activity_type, update.message.chat_id))
    # Check if user is already referred
    referred = query("SELECT id, status, referrer_id, expire_date FROM referrals WHERE referred_id = %s AND status = 0", (user_id,), single=True)
    # For referral
    current_date_now = datetime.datetime.now()
    if referred is not None:
        id = referred['id']
        referrer_id = referred['referrer_id']
        referred_expire_date = referred['expire_date']
        referred_details = query("SELECT COUNT(referral_details.id) as total_data FROM referrals LEFT JOIN referral_details ON referrals.id = referral_details.referral_id WHERE referrals.id = %s", (id,), single=True)
        if referred_details is None:
            command("INSERT INTO referral_details (referral_id) VALUES(%s)", (id,))
        elif current_date_now > referred_expire_date  and referred_details['total_data'] < REFERRED_MIN_ACTIVATION:
            command("UPDATE referrals SET status = %s WHERE referrer_id = %s", (2, referrer_id))
        else:
            print("KE SINI")
            insert_referral_detail = command("INSERT INTO referral_details (referral_id) VALUES(%s)", (id,))
            if referred_details['total_data'] + 1 >= REFERRED_MIN_ACTIVATION and insert_referral_detail is not None:
                command("UPDATE referrals SET status = %s WHERE referrer_id = %s", (1, referrer_id))
                data_referrer = query("SELECT id, username FROM users WHERE user_id = %s", (referrer_id,), single=True)
                print((data_referrer['id'], 0, 'referral', REFERRAL_POINTS, current_date_now.strftime("%Y-%m-%d %H:%M:%S"), group_id))
                command("INSERT INTO scores (user_id, message_id, activity_type, score, date, group_id) VALUES (%s, %s, %s, %s, %s, %s)", (data_referrer['id'], 0, 'referral', REFERRAL_POINTS, current_date_now.strftime("%Y-%m-%d %H:%M:%S"), group_id))
                update.message.reply_text(f"{data_referrer['username']} earned {REFERRAL_POINTS} points.")
                
    if current_points is not None:
        if current_points < max_points:
            new_points = min(points, max_points - current_points)
            current_date = current_date_now.strftime("%Y-%m-%d")
            data_user = query("SELECT id FROM users WHERE user_id = %s", (user_id,), single=True)
            command("INSERT INTO scores (user_id, message_id, activity_type, score, date, group_id) VALUES (%s, %s, %s, %s, %s, %s)", (data_user['id'], message_id, activity_type, new_points, current_date, group_id))

def handle_message(update: Update, context: CallbackContext):
    # Add points when users send a message in group
    user = update.message.from_user
    chat_id = update.message.chat_id  # ID Group or Chat
    message_id = update.message.message_id

    # Make sure only able to run on group
    if chat_id > 0:
        return  

    res = register_user(user.id, user.username, user.first_name, user.last_name, chat_id)
    if res is None:
        print("Failed to register user!")
        return

    if update.message.photo or update.message.video or update.message.animation or update.message.document:
        add_points(update, user.id, message_id, chat_id, "media", MEDIA_POINTS, MAX_MEDIA_POINTS)
    else:
        add_points(update, user.id, message_id, chat_id, "message", MESSAGE_POINTS, MAX_MESSAGE_POINTS)

def myscore(update: Update, context: CallbackContext):
    # Command to show users score
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    user_id = update.message.from_user.id
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    data = query("SELECT COALESCE(SUM(score), 0) as score, first_name, last_name FROM scores LEFT JOIN users ON scores.user_id = users.id WHERE users.user_id = %s AND scores.date = %s AND group_id = %s", (user_id, date, chat_id), single=True)
    
    data_leaderboard = query(
        "SELECT u.username, COALESCE(SUM(s.score), 0) as total_points, u.user_id FROM users u "
        "LEFT JOIN scores s ON u.id = s.user_id "
        "WHERE group_id = %s AND s.date = %s"
        "GROUP BY u.user_id ORDER BY total_points DESC", params=(update.message.chat_id, date), single=False
    )

    rank = 0
    for i, row in enumerate(data_leaderboard, start=1):
        if row['user_id'] == user_id:
            rank = i

    total_score = data['score']
    msg = f"Your score: {plural_number(total_score, 'point')}\n\nRank: {ordinal(rank)}"
    update.message.reply_text(msg)

def leaderboard(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    # Command to show leaderboard
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    data = query(
        "SELECT u.username, COALESCE(SUM(s.score), 0) as total_points FROM users u "
        "LEFT JOIN scores s ON u.id = s.user_id"
        " WHERE group_id = %s"
        " GROUP BY u.user_id ORDER BY total_points DESC, `date` DESC", params=(update.message.chat_id,), single=False
    )
    leaderboard_text = "🏆 **Leaderboard Group** 🏆\n\n"
    if data is None:
        update.message.reply_text("Leaderboard is empty.")
    for i, row in enumerate(data, start=1):
        total_point = row['total_points']
        username = row['username'] if row['username'] else "Unknown"
        if total_point > 1:
            leaderboard_text += f"{i}. {username} - {total_point} points\n"
        else:
            leaderboard_text += f"{i}. {username} - {total_point} point\n"
    update.message.reply_text(leaderboard_text, parse_mode="Markdown")

def handle_start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    update.message.reply_text(f"Hello {update.message.from_user.username}!")

def export_scores(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, chat_id)
    message_id = update.message.message_id
    chat_id = update.message.chat_id
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    data = query(
        "SELECT u.username, first_name, last_name, COALESCE(SUM(s.score), 0) as total_points FROM users u "
        "LEFT JOIN scores s ON u.id = s.user_id "
        " WHERE group_id = %s"
        " GROUP BY u.user_id ORDER BY total_points DESC, `date` DESC", dictionary=False, params=(update.message.chat_id,), single=False
    )

    if(not data):
        update.message.reply_text("No data found!")
        return
    
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"User Scores {date}"
    headers = ["Username", "First Name", "Last Name", "Score"]

    ws.append(headers)

    # Add data to worksheet
    for row in data:
        ws.append(row)


    # Buat border untuk semua sel
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for row in ws.iter_rows():
        for cell in row:
            cell.border = thin_border  # Add borders to all cells

    # Atur lebar kolom otomatis
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)  # get all column letters
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = max_length + 2  # add margin


    if not os.path.exists("export_xls"):
        os.mkdir("export_xls")
    filename = f"export_xls/score_{chat_id}_{message_id}.xlsx"
    # Save the excel file
    wb.save(filename)

    update.message.reply_document(document=open(filename, 'rb'))

def make_referral(update: Update, context: CallbackContext):
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    invite_link = context.bot.create_chat_invite_link(chat_id=update.message.chat_id, creates_join_request=True)
    referral_message = f"Here is your referral link: {invite_link.invite_link}\n"
    current_date = datetime.datetime.now()
    expire_date = current_date + datetime.timedelta(days=REFERRAL_LINK_ACTIVE_DAYS)
    expire_date = expire_date.strftime("%Y-%m-%d %H:%M:%S")
    data = query("SELECT id FROM users WHERE user_id = %s", (update.message.from_user.id,), single=True)
    if command("INSERT INTO referral_links (user_id, link, group_id, expire_date) VALUES (%s, %s, %s, %s)", (data['id'], invite_link.invite_link, update.message.chat_id, expire_date)) is not None:
        update.message.reply_text(referral_message, parse_mode="Markdown")
    else:
        update.message.reply_text("Failed to create referral link.")

def handle_join_request(update: Update, context: CallbackContext):
    join_request = update.chat_join_request
    register_user(join_request.from_user.id, join_request.from_user.username, join_request.from_user.first_name, join_request.from_user.last_name, join_request.chat.id)
    user = join_request.from_user
    invite_link = join_request.invite_link.invite_link
    current_date = datetime.datetime.now()
    expire_date = current_date + datetime.timedelta(days=REFERRAL_ACTIVE_DAYS)
    expire_date = expire_date.strftime("%Y-%m-%d %H:%M:%S")
    data = query("SELECT referral_links.id, users.user_id, is_used FROM referral_links LEFT JOIN users ON referral_links.user_id = users.id WHERE link = %s and group_id = %s", (invite_link, join_request.chat.id), single=True)
    print(data)
    if data is not None:
        if(data['is_used'] == 0):
            print("Join with referrer link")
            print((data['user_id'], user.id, data['id'], expire_date))
            command("INSERT INTO referrals (referrer_id, referred_id, link_id, expire_date) VALUES (%s, %s, %s, %s)", (data['user_id'], user.id, data['id'], expire_date)) # Join with referrer link
            command("UPDATE referral_links SET is_used = 1 WHERE id = %s", (data['id'],))
            join_request.approve()
        else:
            join_request.decline()
    else:
        join_request.approve()

def main():
    global MESSAGE_POINTS, MEDIA_POINTS, MAX_MESSAGE_POINTS, MAX_MEDIA_POINTS, REFERRAL_ACTIVE_DAYS, REFERRED_MIN_ACTIVATION, REFERRAL_POINTS, REFERRAL_LINK_ACTIVE_DAYS
    updater = Updater(token=os.getenv("TELEGRAM_BOT_TOKEN"), use_context=True)
    dp = updater.dispatcher

    bot_config = query("SELECT * FROM bot_config", dictionary=True, single=True)
    if(bot_config):
        MESSAGE_POINTS = int(bot_config['MESSAGE_POINTS'])
        MEDIA_POINTS = int(bot_config['MEDIA_POINTS'])
        MAX_MESSAGE_POINTS = int(bot_config['MAX_MESSAGE_POINTS'])
        MAX_MEDIA_POINTS = int(bot_config['MAX_MEDIA_POINTS'])
        REFERRAL_ACTIVE_DAYS = int(bot_config['REFERRAL_ACTIVE_DAYS'])
        REFERRED_MIN_ACTIVATION = int(bot_config['REFERRED_MIN_ACTIVATION'])
        REFERRAL_POINTS = int(bot_config['REFERRAL_POINTS'])
        REFERRAL_LINK_ACTIVE_DAYS = int(bot_config['REFERRAL_LINK_ACTIVE_DAYS'])

    dp.add_handler(CommandHandler("start", handle_start))
    dp.add_handler(CommandHandler("myscore", myscore))
    dp.add_handler(CommandHandler("leaderboard", leaderboard))
    dp.add_handler(CommandHandler("export_scores", export_scores))
    dp.add_handler(CommandHandler("make_referral", make_referral))
    dp.add_handler(ChatJoinRequestHandler(handle_join_request))
    dp.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.video | Filters.animation | Filters.document, handle_message))
    print("Running bot!")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()