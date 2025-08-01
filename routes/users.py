from flask import Blueprint, request, jsonify
import os
import sqlite3
from utils import get_users, post_user, put_user, delete_user, generate_registration_key, send_email_verification, BASE_URL

users_bp = Blueprint('users', __name__)

@users_bp.route('/api/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
def crud_users():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(error=f"Database file not found: {db_path}"), 404
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Ensure Users table has 'mobile' column
    cursor.execute("""
        PRAGMA table_info(Users)
    """)
    columns = [col[1] for col in cursor.fetchall()]
    if 'mobile' not in columns:
        cursor.execute("ALTER TABLE Users ADD COLUMN mobile TEXT")
        conn.commit()
    if request.method == 'GET':
        result = get_users(cursor)
        conn.close()
        return jsonify(users=result)
    elif request.method == 'POST':
        data = request.json
        email = data.get('email')
        mobile = data.get('mobile')
        # Check for duplicate email or mobile
        cursor.execute("SELECT id FROM Users WHERE email=? OR mobile=?", (email, mobile))
        duplicate_row = cursor.fetchone()
        if duplicate_row:
            conn.close()
            return jsonify(success=False, error="Email or mobile number already exists."), 409
        post_user(cursor, data)
        conn.commit()
        # Send email verification link
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
    elif request.method == 'PUT':
        data = request.json
        put_user(cursor, data)
        conn.commit()
        conn.close()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        data = request.json
        delete_user(cursor, data)
        conn.commit()
        conn.close()
        return jsonify(success=True)
