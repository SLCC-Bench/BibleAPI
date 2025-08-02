from flask import Blueprint, request, jsonify
import os
import sqlite3
import bcrypt
import datetime
from utils import send_password_reset_email, generate_registration_key, BASE_URL

password_bp = Blueprint('password', __name__)

# Ensure this route is present and matches the frontend request
@password_bp.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.json
    email = data.get('email')
    # Fix db_folder to use parent directory, not current file
    db_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(success=False, error=f"Database file not found: {db_path}"), 404
    if not email:
        return jsonify(success=False, error="Email is required"), 400
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Ensure PasswordReset table has 'used' column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PasswordReset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid INTEGER,
            email TEXT,
            token TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            used INTEGER DEFAULT 0
        )
    """)
    cursor.execute("SELECT id FROM Users WHERE email=?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return jsonify(success=False, error="Email not found"), 404
    user_id = user_row[0]
    # Generate a secure token
    reset_token = generate_registration_key(48)
    hashed_token = bcrypt.hashpw(reset_token.encode('utf-8'), bcrypt.gensalt())
    # Save token
    cursor.execute("INSERT INTO PasswordReset (userid, email, token, used) VALUES (?, ?, ?, 0)", (user_id, email, hashed_token))
    conn.commit()
    conn.close()
    # Send email with reset link (use /static/)
    reset_link = f"{BASE_URL}/static/praisehub.html?email={email}&token={reset_token}"
    send_password_reset_email(email, reset_link)
    return jsonify(success=True)

@password_bp.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    token = data.get('token')
    new_password = data.get('new_password')
    db_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(success=False, error=f"Database file not found: {db_path}"), 404
    if not email or not token or not new_password:
        return jsonify(success=False, error="Missing required fields"), 400
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Ensure PasswordReset table has 'used' column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PasswordReset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid INTEGER,
            email TEXT,
            token TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            used INTEGER DEFAULT 0
        )
    """)
    # Validate token from PasswordReset table (get most recent, not used, not expired)
    cursor.execute("""
        SELECT id, userid, token, created, used FROM PasswordReset
        WHERE email=? AND used=0
        ORDER BY created DESC LIMIT 1
    """, (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify(success=False, error="User or token not found or already used"), 404
    reset_id, user_id, db_token, created, used = row
    # Check expiration (5 minutes)
    created_time = datetime.datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
    if (datetime.datetime.utcnow() - created_time).total_seconds() > 300:
        conn.close()
        return jsonify(success=False, error="Reset link expired"), 400
    if not bcrypt.checkpw(token.encode('utf-8'), db_token):
        conn.close()
        return jsonify(success=False, error="Invalid token"), 401
    # Update password
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("UPDATE Users SET password=? WHERE id=?", (hashed_password, user_id))
    # Mark token as used
    cursor.execute("UPDATE PasswordReset SET used=1 WHERE id=?", (reset_id,))
    conn.commit()
    conn.close()
    return jsonify(success=True)

@password_bp.route('/api/check-reset-token', methods=['POST'])
def check_reset_token():
    data = request.json
    email = data.get('email')
    token = data.get('token')
    db_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(success=False, error="Database file not found"), 404
    if not email or not token:
        return jsonify(success=False, error="Missing required fields"), 400
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, token, created, used FROM PasswordReset
        WHERE email=? ORDER BY created DESC LIMIT 1
    """, (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify(success=False, error="Token not found"), 404
    reset_id, db_token, created, used = row
    created_time = datetime.datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
    expired = (datetime.datetime.utcnow() - created_time).total_seconds() > 300
    if used == 1:
        conn.close()
        return jsonify(success=False, error="This reset link has already been used.", used=True, expired=expired)
    if expired:
        conn.close()
        return jsonify(success=False, error="This reset link has expired.", expired=True, used=used)
    if not bcrypt.checkpw(token.encode('utf-8'), db_token):
        conn.close()
        return jsonify(success=False, error="Invalid reset link.", invalid=True, used=used, expired=expired)
    conn.close()
    return jsonify(success=True, used=used, expired=expired)

@password_bp.route('/reset-password', methods=['GET'])
def reset_password_page():
    email = request.args.get('email')
    token = request.args.get('token')
    db_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    html_path = os.path.join(os.path.dirname(__file__), 'static', 'praisehub.html')
    if not os.path.exists(db_path):
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'Database file not found.'), 200, {'Content-Type': 'text/html'}
    if not email or not token:
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'Invalid or missing reset link.'), 200, {'Content-Type': 'text/html'}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, token, created, used FROM PasswordReset
        WHERE email=? ORDER BY created DESC LIMIT 1
    """, (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'Reset link not found or already used.'), 200, {'Content-Type': 'text/html'}
    reset_id, db_token, created, used = row
    created_time = datetime.datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
    expired = (datetime.datetime.utcnow() - created_time).total_seconds() > 300
    if used == 1:
        conn.close()
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'This reset link has already been used.'), 200, {'Content-Type': 'text/html'}
    if expired:
        conn.close()
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'This reset link has expired.'), 200, {'Content-Type': 'text/html'}
    if not bcrypt.checkpw(token.encode('utf-8'), db_token):
        conn.close()
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'Invalid reset link.'), 200, {'Content-Type': 'text/html'}
    conn.close()
    # Valid link, show reset form (leave {MESSAGE} for JS)
    return open(html_path).read(), 200, {'Content-Type': 'text/html'}
