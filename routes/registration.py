from flask import Blueprint, request, jsonify
import os
import sqlite3
import bcrypt
from utils import post_registration, put_registration, delete_registration, get_registrations, send_email_verification, generate_registration_key, BASE_URL

registration_bp = Blueprint('registration', __name__)

@registration_bp.route('/api/registrations', methods=['GET', 'POST', 'PUT', 'DELETE'])
def crud_registrations():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(error=f"Database file not found: {db_path}"), 404
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if request.method == 'GET':
        result = get_registrations(cursor)
        conn.close()
        return jsonify(registrations=result)
    elif request.method == 'POST':
        data = request.json
        post_registration(cursor, data)
        conn.commit()
        conn.close()
        return jsonify(success=True)
    elif request.method == 'PUT':
        data = request.json
        put_registration(cursor, data)
        conn.commit()
        conn.close()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        data = request.json
        delete_registration(cursor, data)
        conn.commit()
        conn.close()
        return jsonify(success=True)

@registration_bp.route('/api/register', methods=['POST'])
def register():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(success=False, error=f"Database file not found: {db_path}"), 404
    data = request.json
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # ...existing code for post_user and commit...
    # Send email verification link
    email = data.get('email')
    cursor.execute("SELECT id FROM Users WHERE email=?", (email,))
    user_row = cursor.fetchone()
    if user_row:
        user_id = user_row[0]
        verification_token = generate_registration_key(32)
        # Save token in Registration table
        cursor.execute("UPDATE Registration SET registrationkey=? WHERE userid=?", (verification_token, user_id))
        conn.commit()
        verification_link = f"{BASE_URL}/api/verify-email?email={email}&token={verification_token}"
        send_email_verification(email, verification_link)
    conn.close()
    return jsonify(success=True)

@registration_bp.route('/api/verify-email', methods=['GET'])
def verify_email():
    email = request.args.get('email')
    token = request.args.get('token')
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    html_path = os.path.join(os.path.dirname(__file__), 'static', 'praisehub.html')
    if not os.path.exists(db_path):
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'Database file not found.'), 200, {'Content-Type': 'text/html'}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, isEmailVerified FROM Users WHERE email=?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'User not found.'), 200, {'Content-Type': 'text/html'}
    user_id, is_verified = user_row
    if is_verified:
        conn.close()
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'Email already verified. You may close this page.'), 200, {'Content-Type': 'text/html'}
    cursor.execute("SELECT registrationkey FROM Registration WHERE userid=?", (user_id,))
    reg_row = cursor.fetchone()
    if not reg_row or reg_row[0] != token:
        conn.close()
        return open(html_path, encoding="utf-8").read().replace('{MESSAGE}', 'Invalid verification link.'), 200, {'Content-Type': 'text/html'}
    cursor.execute("UPDATE Users SET isEmailVerified=1 WHERE id=?", (user_id,))
    conn.commit()
    # Send registration key email
    registration_key = generate_registration_key(32)
    hashed_registration_key = bcrypt.hashpw(registration_key.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("UPDATE Registration SET registrationkey=? WHERE userid=?", (hashed_registration_key, user_id))
    conn.commit()
    from utils import send_professional_email
    send_professional_email(
        email,
        'Welcome to Praisehub',
        'Registration Key',
        f"Your registration key is: <b>{registration_key}</b>",
        '',
        ''
    )
    conn.close()
    html = open(html_path, encoding="utf-8").read()
    html = html.replace('{MESSAGE}', 'Email verified and registration key sent. You may close this page.')
    return html, 200, {'Content-Type': 'text/html'}
