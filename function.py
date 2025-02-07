from config.db import command, query

def find_user_by_tg_id(user_id):
    return query("SELECT * FROM users WHERE user_id = %s", (user_id,), single=True)