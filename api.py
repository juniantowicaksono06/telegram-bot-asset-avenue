from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

from config.db import query

app = Flask(__name__)

@app.route('/api/scores/leaderboard', methods=['GET'])
def api_endpoint():
    group_id = request.args.get('group_id', '')
    
    if group_id == '' or group_id is None:
        return jsonify({"message": "Group ID is required."})
    
    username = request.args.get('username', '')

    if username is None or username == '':
        data = query(
            "SELECT u.username, COALESCE(SUM(s.score), 0) as total_points, `date` FROM users u "
            "LEFT JOIN scores s ON u.id = s.user_id"
            " WHERE group_id = %s"
            " GROUP BY u.user_id ORDER BY total_points DESC, `date` DESC", params=(group_id,), single=False
        )
    else:
        data = query(
            "SELECT u.username, COALESCE(SUM(s.score), 0) as total_points, `date` FROM users u "
            "LEFT JOIN scores s ON u.id = s.user_id"
            " WHERE group_id = %s AND username = %s"
            " GROUP BY u.user_id ORDER BY total_points DESC, `date` DESC", params=(group_id, username), single=False
        )
    
    return jsonify({
        "status": 200,
        "data": data
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)