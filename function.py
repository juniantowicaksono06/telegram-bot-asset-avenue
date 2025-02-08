from config.db import command, query
import os

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