from config.db import command, query
from function import find_user_by_tg_id
def insert_stage(user_id, group_id):
    data_user = find_user_by_tg_id(user_id)
    return command("INSERT INTO user_stage (user_id, group_id, stage) VALUES (%s, %s, %s)", (data_user['id'], group_id, 0))

def upload_stage(user_id, group_id):
    data_user = find_user_by_tg_id(user_id)
    return command("UPDATE user_stage SET stage = %s WHERE user_id = %s AND group_id = %s", (1, data_user['id'], group_id))

def finish_upload_stage(user_id, group_id):
    data_user = find_user_by_tg_id(user_id)
    return command("UPDATE user_stage SET stage = %s WHERE user_id = %s AND group_id = %s", (0, data_user['id'], group_id))

def check_stage(user_id, group_id):
    data_user = query("SELECT id FROM users WHERE user_id = %s", (user_id,), single=True)
    if data_user is not None:
        data = query("SELECT * FROM user_stage WHERE user_id = %s AND group_id = %s", (data_user['id'], group_id), single=True)
        if data is None:
            insert_stage(user_id, group_id)
        data = query("SELECT * FROM user_stage WHERE user_id = %s AND group_id = %s", (data_user['id'], group_id), single=True)
        return data['stage']
    return 0
        