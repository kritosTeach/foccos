from flask import Flask, request, jsonify, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import os, json

app = Flask(__name__, static_folder='.', static_url_path='')

# Session secret for Flask (placeholder). Replace for production.
app.secret_key = os.environ.get('FOCUSFLOW_SESSION_SECRET', 'FOCUSFLOW_CHANGE_ME')

DATA_FILE = os.environ.get('FOCUSFLOW_USERS_JSON', 'users.json')

DEFAULT_USER = {
    "name": "",
    "email": "",
    "password_hash": "",
    "provider": "email",
    "createdAt": None,
    "lastLogin": None,
    "joinDate": None,
    "avatarInitials": "ST",
    "isPremium": False,
    "accent": "#c084fc",

    # Progress
    "xp": 340,
    "streak": 7,
    "sessionsCompleted": 0,
    "totalStudyMins": 135,
    "todayPomodoros": 0,
    "targetMins": 240,
    "goals": [
        {"id": 1, "name": "Math Homework", "emoji": "📒", "targetMins": 60, "doneMins": 45},
        {"id": 2, "name": "React Course", "emoji": "⚙️", "targetMins": 90, "doneMins": 90},
        {"id": 3, "name": "English Essay", "emoji": "✍️", "targetMins": 45, "doneMins": 10}
    ],
    "settings": {"notifications": True, "autoBreak": True, "sound": False, "vibration": True},
    "adPomodoroCount": 0,

    # Admin
    "isAdmin": False
}


def utc_iso():
    return datetime.now(timezone.utc).isoformat()


def load_db():
    if not os.path.exists(DATA_FILE):
        return {"users": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_db(db):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def find_user_by_email(db, email):
    email = (email or '').lower().strip()
    for u in db.get('users', []):
        if (u.get('email') or '').lower().strip() == email:
            return u
    return None


def find_user_by_uid(db, uid):
    for u in db.get('users', []):
        if u.get('uid') == uid:
            return u
    return None


def make_uid(email):
    # Simple deterministic uid: email normalized + timestamp not needed for demo
    return abs(hash((email or '').lower().strip()))


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/health')
def health():
    return jsonify({"ok": True})


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(force=True) or {}
    email = (data.get('email') or '').lower().strip()
    password = data.get('password')
    name = (data.get('name') or '').strip()

    if not email or '@' not in email:
        return jsonify({"error": "Invalid email."}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if not name:
        return jsonify({"error": "Enter your name."}), 400

    db = load_db()
    if find_user_by_email(db, email):
        return jsonify({"error": "Email already registered."}), 409

    uid = make_uid(email)
    user = dict(DEFAULT_USER)
    user.update({
        "uid": str(uid),
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "provider": 'email',
        "createdAt": utc_iso(),
        "lastLogin": None,
        "joinDate": datetime.now().strftime('%Y-%m-%d'),
        "avatarInitials": (name.split()[0][:1] + (name.split()[1][:1] if len(name.split())>1 else name.split()[0][:1])).upper() or 'ST'
    })

    db['users'].append(user)
    save_db(db)

    return jsonify({"ok": True, "uid": user['uid']})


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(force=True) or {}
    email = (data.get('email') or '').lower().strip()
    password = data.get('password')

    db = load_db()
    u = find_user_by_email(db, email)
    if not u:
        return jsonify({"error": "Wrong email or password."}), 401
    if not check_password_hash(u.get('password_hash', ''), password or ''):
        return jsonify({"error": "Wrong email or password."}), 401

    u['lastLogin'] = utc_iso()
    save_db(db)

    # Create a session so the frontend doesn't need to send uid.
    session['uid'] = u.get('uid')

    # Return user profile
    profile = {k: u.get(k) for k in [
        'uid','name','email','avatarInitials','joinDate','isPremium','accent','xp','streak',
        'sessionsCompleted','totalStudyMins','todayPomodoros','targetMins','goals','settings','adPomodoroCount'
    ]}
    return jsonify({"ok": True, "user": profile})


@app.route('/api/auth/forgot', methods=['POST'])
def forgot():
    # Demo: we don't send emails. We respond success.
    data = request.get_json(force=True) or {}
    email = (data.get('email') or '').lower().strip()
    if not email or '@' not in email:
        return jsonify({"error": "Invalid email."}), 400
    return jsonify({"ok": True, "message": "Reset email sent (demo)."})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route('/api/me', methods=['GET'])
def me():
    uid = session.get('uid')
    if not uid:
        return jsonify({"error": "Not authenticated."}), 401

    db = load_db()
    u = find_user_by_uid(db, str(uid))
    if not u:
        return jsonify({"error": "User not found."}), 404

    profile = {k: u.get(k) for k in [
        'uid','name','email','avatarInitials','joinDate','isPremium','accent','xp','streak',
        'sessionsCompleted','totalStudyMins','todayPomodoros','targetMins','goals','settings','adPomodoroCount'
    ]}
    return jsonify({"ok": True, "user": profile})


@app.route('/api/user', methods=['GET'])
def get_user():
    uid = request.args.get('uid')
    db = load_db()
    u = find_user_by_uid(db, str(uid))
    if not u:
        return jsonify({"error": "User not found."}), 404

    profile = {k: u.get(k) for k in [
        'uid','name','email','avatarInitials','joinDate','isPremium','accent','xp','streak',
        'sessionsCompleted','totalStudyMins','todayPomodoros','targetMins','goals','settings','adPomodoroCount'
    ]}
    return jsonify({"ok": True, "user": profile})


@app.route('/api/user', methods=['PATCH'])
def patch_user():
    data = request.get_json(force=True) or {}
    uid = str(data.get('uid') or '')
    if not uid:
        return jsonify({"error": "Missing uid."}), 400

    db = load_db()
    u = find_user_by_uid(db, uid)
    if not u:
        return jsonify({"error": "User not found."}), 404

    # Update allowed fields
    allowed = {
        'name','isPremium','accent','xp','streak','sessionsCompleted','totalStudyMins','todayPomodoros','targetMins','goals','settings','adPomodoroCount','avatarInitials','joinDate'
    }

    for k,v in data.items():
        if k in allowed:
            u[k] = v

    save_db(db)
    return jsonify({"ok": True})


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(force=True) or {}
    email = (data.get('email') or '').lower().strip()
    password = data.get('password')

    # Demo admin credentials (not secure; for demo only)
    ADMIN_EMAIL = 'admin@focusflow.com'
    ADMIN_PASSWORD = 'Admin@2025'
    if email != ADMIN_EMAIL or password != ADMIN_PASSWORD:
        return jsonify({"error": 'Invalid admin credentials.'}), 401

    return jsonify({"ok": True})


@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    users = load_db().get('users', [])
    # Return non-sensitive fields
    out = []
    for u in users:
        out.append({
            'uid': u.get('uid'),
            'name': u.get('name'),
            'email': u.get('email'),
            'provider': u.get('provider'),
            'xp': u.get('xp'),
            'streak': u.get('streak'),
            'totalStudyMins': u.get('totalStudyMins'),
            'isPremium': bool(u.get('isPremium')),
            'joinDate': u.get('joinDate'),
            'lastLogin': u.get('lastLogin'),
        })
    return jsonify({"ok": True, "users": out})


@app.route('/api/admin/user/<uid>', methods=['GET'])
def admin_user(uid):
    db = load_db()
    u = find_user_by_uid(db, str(uid))
    if not u:
        return jsonify({"error": 'User not found'}), 404
    # Return full record (excluding password hash)
    out = dict(u)
    out.pop('password_hash', None)
    return jsonify({"ok": True, "user": out})


@app.route('/api/admin/user/<uid>/premium', methods=['POST'])
def admin_toggle_premium(uid):
    db = load_db()
    u = find_user_by_uid(db, str(uid))
    if not u:
        return jsonify({"error": 'User not found'}), 404
    u['isPremium'] = not bool(u.get('isPremium'))
    save_db(db)
    return jsonify({"ok": True, "isPremium": u['isPremium']})


@app.route('/api/admin/user/<uid>', methods=['DELETE'])
def admin_delete(uid):
    db = load_db()
    users = db.get('users', [])
    before = len(users)
    db['users'] = [u for u in users if str(u.get('uid')) != str(uid)]
    if len(db['users']) == before:
        return jsonify({"error": 'User not found'}), 404
    save_db(db)
    return jsonify({"ok": True})


if __name__ == '__main__':
    # Run: python server.py
    # then open: http://127.0.0.1:5000
    app.run(host='127.0.0.1', port=5000, debug=True)

