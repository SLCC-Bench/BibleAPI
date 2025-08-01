from flask import Blueprint, request, jsonify
import os
import sqlite3
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(error=f"Database file not found: {db_path}"), 404
    data = request.json
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, isEmailVerified FROM Users WHERE username=? OR email=?", (username, username))
    row = cursor.fetchone()
    if row:
        user_id, hashed_password, is_email_verified = row
        if not is_email_verified:
            conn.close()
            return jsonify(success=False, error="Verification is sent to your email. Please verify."), 401
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            conn.close()
            return jsonify(success=True, user_id=user_id)
        else:
            conn.close()
            return jsonify(success=False, error="Invalid password"), 401
    else:
        conn.close()
        return jsonify(success=False, error="Username or Password is incorrect."), 404

@auth_bp.route('/api/verify', methods=['POST'])
def verify_user():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(error=f"Database file not found: {db_path}"), 404
    data = request.json
    email = data.get('email')
    registration_key = data.get('registrationkey')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users WHERE email=?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return jsonify(success=False, error="User not found"), 404
    user_id = user_row[0]
    cursor.execute("SELECT registrationkey FROM Registration WHERE userid=?", (user_id,))
    reg_row = cursor.fetchone()
    if not reg_row:
        conn.close()
        return jsonify(success=False, error="Registration not found"), 404
    db_registration_key = reg_row[0]
    if bcrypt.checkpw(registration_key.encode('utf-8'), db_registration_key):
        cursor.execute("UPDATE Users SET isRegistered=1, isEmailVerified=1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify(success=True)
    else:
        conn.close()
        return jsonify(success=False, error="Invalid registration key"), 401

@auth_bp.route('/api/profile', methods=['POST'])
def get_profile():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(error=f"Database file not found: {db_path}"), 404
    data = request.json
    user_id = data.get('user_id')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT firstname, lastname, email, orgname, username, mobile, isRegistered, isEmailVerified FROM Users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify(error="User not found"), 404
    fullname = f"{row[0]} {row[1]}"
    email = row[2]
    orgname = row[3]
    username = row[4]
    mobile = row[5]
    is_registered = row[6]
    is_email_verified = row[7]
    profile = {
        "Fullname": fullname,
        "Email": email,
        "Organization Name": orgname,
        "Username": username,
        "Mobile": mobile,
        "Email Verified": bool(is_email_verified),
        "Has Registration Key": bool(is_registered)
    }
    conn.close()
    return jsonify(profile)
