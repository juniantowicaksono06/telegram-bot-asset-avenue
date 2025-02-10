from config.db import command, query
import os
from telegram import Update
from telegram.ext import CallbackContext

def find_user_by_tg_id(user_id):
    return query("SELECT * FROM users WHERE user_id = %s", (user_id,), single=True)


def check_whitelist_user(user_id):
    data = query("SELECT * FROM whitelist_users_private WHERE user_id = %s", (user_id,), single=True)
    if data is None:
        return False
    return True

def get_all_groups():
    groups = query("SELECT * FROM `groups`")
    if groups is None:
        return None
    return groups

def is_admin(chat_id, user_id, context: CallbackContext):
    chat_member = context.bot.get_chat_member(chat_id, user_id)
    if chat_member.status in ['administrator', 'creator']:
        print("IS ADMIN")
        return True
    print("NOT ADMIN")
    return False