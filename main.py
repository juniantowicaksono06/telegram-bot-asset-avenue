from dotenv import load_dotenv
from config.db import connect_to_mysql, command, query
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ChatJoinRequestHandler, CallbackQueryHandler
import os
import pandas as pd

import openpyxl
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
import datetime
from utils import ordinal, plural_number
load_dotenv()
from stage import check_stage, upload_stage, finish_upload_stage
import re
import threading

# Aturan poin
MESSAGE_POINTS = 100
MEDIA_POINTS = 200
MAX_MESSAGE_POINTS = 700
MAX_MEDIA_POINTS = 400
REFERRAL_ACTIVE_DAYS = 10
REFERRED_MIN_ACTIVATION = 3
REFERRAL_POINTS = 200
REFERRAL_LINK_ACTIVE_DAYS = 3
MAX_LEADERBOARD_DATA_PER_PAGE = 5

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
    else:
        data = query("SELECT users.user_id FROM users LEFT JOIN scores ON users.id = scores.user_id WHERE users.user_id = %s AND activity_type = 'registration' AND group_id = %s", (user_id, group_id), single=True)
        if data is None:
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            data_user = query("SELECT id FROM users WHERE user_id = %s", (user_id,), single=True)
            print(data_user['id'], 0, 'registration', 100, current_date, group_id)
            command("INSERT INTO scores (user_id, message_id, activity_type, score, date, group_id) VALUES (%s, %s, %s, %s, %s, %s)", (data_user['id'], 0, 'registration', 100, current_date, group_id))       
    return True

def get_daily_points(user_id, activity_type, group_id):
    """Hitung total poin harian pengguna berdasarkan jenis aktivitas."""
    data = query("SELECT COALESCE(SUM(score), 0) as score FROM scores LEFT JOIN users ON scores.user_id = users.id WHERE users.user_id = %s AND activity_type = %s AND DATE(`date`) = CURDATE() AND group_id = %s", (user_id, activity_type, group_id), single=True)
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

def process_upload_points(update: Update, context: CallbackContext):
    # Process uploaded file
    document = update.message.document
    file_path = f"./uploads"
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    user = update.message.from_user
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    uploaded_filename = f"uploaded_{user.id}_{update.message.chat_id}{now}.xlsx, xls"
    file_path = os.path.join(file_path, uploaded_filename)
    document.get_file().download(file_path)
    df = pd.read_excel(file_path)
    usernames = df["username"]
    points = df["points"]
    for username, point in zip(usernames, points): 
        username = re.sub(r"^@\S+\s*", "", username)
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        data_user = query("SELECT id FROM users WHERE username = %s", (username,), single=True)
        if data_user is not None:
            command("INSERT INTO scores (user_id, message_id, activity_type, score, date, group_id) VALUES (%s, %s, %s, %s, %s, %s)", (data_user['id'], 0, 'extra point', point, current_date, update.message.chat_id))
    os.remove(file_path)
    return True
        

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
        current_stage = check_stage(update.message.from_user.id, update.message.chat.id)
        if current_stage == 1 and update.message.document:
            document = update.message.document
        
            # Get file name and MIME type
            file_name = document.file_name
            mime_type = document.mime_type
            # Check file extension
            if not file_name.endswith((".xlsx", ".xls")):
                update.message.reply_text(f"File '{file_name}' is not an Excel file based on its extension.")
                return

            if not mime_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
                update.message.reply_text(f"File '{file_name}' is not an Excel file based on its MIME type.")
                return

            # Upload file
            thread = threading.Thread(target=process_upload_points, args=(update, context))
            thread.start()
            update.message.reply_text(f"File '{file_name}' is succesfully uploaded use /finish_upload to finish the upload process.")
            # if res == True:
            #     update.message.reply_text(f"File '{file_name}' is succesfully uploaded")

        elif current_stage != 1:
            add_points(update, user.id, message_id, chat_id, "media", MEDIA_POINTS, MAX_MEDIA_POINTS)
        else:
            update.message.reply_text("The uploaded file is not an Excel file.")
            return
    else:
        if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
            update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
            return
        add_points(update, user.id, message_id, chat_id, "message", MESSAGE_POINTS, MAX_MESSAGE_POINTS)

def myscore(update: Update, context: CallbackContext):
    # Command to show users score
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
        update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
        return
    user_id = update.message.from_user.id
    data = query("SELECT COALESCE(SUM(score), 0) as score, first_name, last_name FROM scores LEFT JOIN users ON scores.user_id = users.id WHERE users.user_id = %s AND group_id = %s", (user_id, chat_id), single=True)
    
    data_leaderboard = query(
        "SELECT u.username, COALESCE(SUM(s.score), 0) as total_points, u.user_id FROM users u "
        "LEFT JOIN scores s ON u.id = s.user_id "
        " WHERE group_id = %s"
        " GROUP BY u.user_id ORDER BY total_points DESC", params=(update.message.chat_id, ), single=False
    )

    rank = 0
    for i, row in enumerate(data_leaderboard, start=1):
        if row['user_id'] == user_id:
            rank = i

    total_score = data['score']
    msg = f"Your score: {plural_number(total_score, 'point')}\n\nRank: {ordinal(rank)}"
    update.message.reply_text(msg)

def leaderboard(update: Update, context: CallbackContext):
    page = 1
    cut_data = MAX_LEADERBOARD_DATA_PER_PAGE
    q = update.callback_query
    if q is not None:
        q.answer()
        q_data = q.data
        q_data = q_data.replace("callback_leaderboard_", "")
        page = int(q_data)
        cut_data = MAX_LEADERBOARD_DATA_PER_PAGE * page
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.message.chat_id
        if chat_id > 0:
            return 
        register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
        if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
            update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
            return
    # Command to show leaderboard
    data = query(
        "SELECT u.username, COALESCE(SUM(s.score), 0) as total_points, `date` FROM users u "
        "LEFT JOIN scores s ON u.id = s.user_id"
        " WHERE group_id = %s"
        " GROUP BY u.user_id ORDER BY total_points DESC, `date` DESC", params=(chat_id,), single=False
    )
    leaderboard_text = "🏆 Leaderboard Group 🏆\n\n"
    # dummy_users = [
    #     '1. oyenbarbar98 - 600 points\n', 
    #     '2. oyenbarbar98 - 600 points\n', 
    # ]
    
    leaderboard_users = []
    if data is None:
        update.message.reply_text("Leaderboard is empty.")
    for i, row in enumerate(data, start=1):
        total_point = row['total_points']
        username = row['username'] if row['username'] else "Unknown"
        leaderboard_users.append(f"{i}. {username} - {total_point} points\n")
    max_index = cut_data if len(leaderboard_users) > cut_data else len(leaderboard_users)
    cutted_data = leaderboard_users[(page-1) * MAX_LEADERBOARD_DATA_PER_PAGE:max_index]
    leaderboard_text += "".join(cutted_data)
    # Show button if the data is greater than MAX_LEADERBOARD_DATA_PER_PAGE
    if len(leaderboard_users) > MAX_LEADERBOARD_DATA_PER_PAGE and len(leaderboard_users) > cut_data:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Load More", callback_data=f"callback_leaderboard_{page + 1}"),
                ]
            ]
        )
        leaderboard_text += f"\nShow users {(page) * len(cutted_data)} of {len(leaderboard_users)}"
        # If there is still more user show load more button
        if q is not None:
            q.edit_message_reply_markup(reply_markup=None)
            context.bot.send_message(chat_id=chat_id, text=leaderboard_text, reply_markup=keyboard)
        # If not then just show the text
        else:
            update.message.reply_text(leaderboard_text, reply_markup=keyboard)
        return
    # If the event is not query callback handler
    if q is None:
        leaderboard_text += f"\nShow users {len(leaderboard_users)} of {len(leaderboard_users)}"
        update.message.reply_text(leaderboard_text)
        return
    # If the event is query callback handler
    else:   
        leaderboard_text += f"\nShow users {len(leaderboard_users)} of {len(leaderboard_users)}"
        q.edit_message_reply_markup(reply_markup=None)
        context.bot.send_message(chat_id=chat_id, text=leaderboard_text)

def handle_start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
        update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
        return
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    update.message.reply_text(f"Hello {update.message.from_user.username}!")

def template_upload_points(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
        update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
        return
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    with open('excel_template/template_upload_points.xlsx', 'rb') as excel_file:
        context.bot.send_document(
            chat_id = chat_id,
            document=excel_file,
            filename="upload_points_template.xlsx",
            caption="Upload Points Template"
        )

def export_scores(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, chat_id)
    if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
        update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
        return
    message_id = update.message.message_id
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

def create_referral(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat_id)
    if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
        update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
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
            register_user(join_request.from_user.id, join_request.from_user.username, join_request.from_user.first_name, join_request.from_user.last_name, join_request.chat.id)
            print((data['user_id'], user.id, data['id'], expire_date))
            command("INSERT INTO referrals (referrer_id, referred_id, link_id, expire_date) VALUES (%s, %s, %s, %s)", (data['user_id'], user.id, data['id'], expire_date)) # Join with referrer link
            command("UPDATE referral_links SET is_used = 1 WHERE id = %s", (data['id'],))
            join_request.approve()
        else:
            join_request.decline()
    else:
        join_request.approve()

def upload_points(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat.id)
    admins = context.bot.get_chat_administrators(chat_id)
    if not any((admin.user.id == update.message.from_user.id and admin.status == "creator") or (admin.user.id == update.message.from_user.id and admin.status == "administrator") for admin in admins):
        update.message.reply_text("You are not authorized to use this command.")
        return
    if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
        update.message.reply_text("You are in the process of uploading points with excel file. Please upload xlsx, xls file format only. Use /finish_upload to cancel the process.")
        return
    else:
        user = update.message.from_user
        upload_stage(user.id, update.message.chat_id)
        update.message.reply_text("Please upload xlsx, xls file format only to add points.")
        return

def handle_query_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if q.data.startswith("callback_leaderboard_"):
        leaderboard(update, context)
        return

def finish_upload(update: Update, conext: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id > 0:
        return 
    register_user(update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, update.message.chat.id)
    
    if check_stage(update.message.from_user.id, update.message.chat.id) == 1:
        user = update.message.from_user
        update.message.reply_text("Upload file with excel format has been finished.")
        finish_upload_stage(user.id, update.message.chat.id)
        return
    else:
        update.message.reply_text("You're not in the process of uploading points with excel file.")

def main():
    global MESSAGE_POINTS, MEDIA_POINTS, MAX_MESSAGE_POINTS, MAX_MEDIA_POINTS, REFERRAL_ACTIVE_DAYS, REFERRED_MIN_ACTIVATION, REFERRAL_POINTS, REFERRAL_LINK_ACTIVE_DAYS, MAX_LEADERBOARD_DATA_PER_PAGE
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
        MAX_LEADERBOARD_DATA_PER_PAGE = int(bot_config['MAX_LEADERBOARD_DATA_PER_PAGE'])

    dp.add_handler(CommandHandler("start", handle_start))
    dp.add_handler(CommandHandler("myscore", myscore))
    dp.add_handler(CommandHandler("leaderboard", leaderboard))
    dp.add_handler(CommandHandler("export_scores", export_scores))
    dp.add_handler(CommandHandler("create_referral", create_referral))
    dp.add_handler(CommandHandler("finish_upload", finish_upload))
    dp.add_handler(CommandHandler("upload_points", upload_points))
    dp.add_handler(CommandHandler("template_upload_points", template_upload_points))
    dp.add_handler(CallbackQueryHandler(handle_query_callback))
    dp.add_handler(ChatJoinRequestHandler(handle_join_request))
    dp.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.video | Filters.animation | Filters.document, handle_message))
    print("Running bot!")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()