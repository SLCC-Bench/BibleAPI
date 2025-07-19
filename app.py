from flask import Flask, jsonify, Response, request
import sqlite3
import os
import re
import json
import bcrypt
import random
import string
import smtplib
from email.message import EmailMessage
import threading
import time
import requests

app = Flask(__name__)

def generate_otp(length=6):
    return random.randint(100000, 999999)

def generate_registration_key(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/api/translations')
def list_translations():
    db_folder = os.path.join(os.path.dirname(__file__), 'db', 'bibles')
    if not os.path.exists(db_folder):
        # Folder does not exist, return empty list
        return Response(json.dumps({"translations": []}, ensure_ascii=False), mimetype='application/json')
    files = [f for f in os.listdir(db_folder) if f.endswith('.SQLite3')]
    translations = []
    for f in files:
        translation_name = f.replace('.SQLite3', '')
        db_path = os.path.join(db_folder, f)
        language = None
        try:
            conn = sqlite3.connect(db_path)
            print(f"Successfully connected to database: {db_path}")
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM info WHERE name='language' LIMIT 1")
            row = cursor.fetchone()
            print(f"Row fetched from info table (language): {row}")
            if row and row[0]:
                language = row[0]
            conn.close()
        except Exception as e:
            print(f"Exception for {translation_name}: {e}")
            language = None
        print(f"Translation: {translation_name}, Language: {language}")
        translations.append({
            "name": translation_name,
            "language": language
        })
    return Response(json.dumps({"translations": translations}, ensure_ascii=False), mimetype='application/json')

@app.route('/api/verses/<translation>')
def load_data(translation):
    db_folder = os.path.join(os.path.dirname(__file__), 'db', 'bibles')
    db_path = os.path.join(db_folder, f"{translation}.SQLite3")
    print(f"Requested translation: {translation}")
    print(f"Database path: {db_path}")
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return jsonify(error=f"Database file not found: {db_path}"), 404
    language = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM info WHERE name='language' LIMIT 1")
        row = cursor.fetchone()
        if row and row[0]:
            language = row[0]
        # Query verses
        query = """
            SELECT
                ? AS Translation,
                books.long_name || ' ' || verses.chapter || ':' || verses.verse AS Reference,
                verses.text AS Verse
            FROM verses
            JOIN books ON verses.book_number = books.book_number
            ORDER BY verses.book_number, verses.chapter, verses.verse
        """
        cursor.execute(query, (translation,))
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Exception opening or querying database: {e}")
        return jsonify(error=str(e)), 500
    cleaned_rows = []
    for row in rows:
        verse_text = row[2]
        if verse_text is None:
            verse_text = ''
        # Remove <S> tags with Strong's numbers
        verse_text = re.sub(r'<S>[\d\s,]+<\/S>', '', verse_text)
        # Remove <p ...> tags (including <p> and <p ...>)
        verse_text = re.sub(r'<p[^>]*>', '', verse_text, flags=re.IGNORECASE)
        verse_text = re.sub(r'</p>', '', verse_text, flags=re.IGNORECASE)
        verse_text = re.sub(r'<p[^\s>]*?', '', verse_text, flags=re.IGNORECASE)
        # Remove <pb/> tags
        verse_text = re.sub(r'<pb\s*\/>', '', verse_text, flags=re.IGNORECASE)
        # Remove <i> and </i> tags (including <i ...>)
        verse_text = re.sub(r'</?i[^>]*>', '', verse_text, flags=re.IGNORECASE)
        # Remove custom footnote tags like <f>[7†]</f>
        verse_text = re.sub(r'<f>.*?<\/f>', '', verse_text, flags=re.IGNORECASE)
        # Remove any remaining HTML tags
        verse_text = re.sub(r'<[^>]+>', '', verse_text)
        # Remove leftover raw footnote markers like [7], [8], [10a], [ 11 ]
        verse_text = re.sub(r'\[\s*\d+[a-zA-Z]?†?\s*\]', '', verse_text)
        # Remove unwanted symbols but keep punctuation and letters
        verse_text = re.sub(r'[^\w\s.,;:\'\"!?()\-\–—\[\]{}<>\/]', '', verse_text)
        # Collapse excess whitespace
        verse_text = re.sub(r'\s{2,}', ' ', verse_text)
        cleaned_rows.append({
            "Translation": row[0],
            "Reference": row[1],
            "Verse": verse_text.strip(),
            "Language": language
        })
    # Return JSON with ensure_ascii=False for Unicode
    return Response(json.dumps({"verses": cleaned_rows}, ensure_ascii=False), mimetype='application/json')

def get_users(cursor):
    cursor.execute("SELECT id, firstname, lastname, username, email, orgname, mobile, isEmailVerified, isRegistered, created, updated FROM Users")
    rows = cursor.fetchall()
    return [{
        "id": row[0],
        "firstname": row[1],
        "lastname": row[2],
        "username": row[3],
        "email": row[4],
        "orgname": row[5],
        "mobile": row[6],
        "isEmailVerified": row[7],
        "isRegistered": row[8],
        "created": row[9],
        "updated": row[10]
    } for row in rows]

def post_user(cursor, data):
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    orgname = data.get('orgname')
    mobile = data.get('mobile')
    isEmailVerified = data.get('isEmailVerified', 0)
    isRegistered = data.get('isRegistered', 0)
    created = data.get('created')
    updated = data.get('updated')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO Users (firstname, lastname, username, password, email, orgname, mobile, isEmailVerified, isRegistered, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (firstname, lastname, username, hashed_password, email, orgname, mobile, isEmailVerified, isRegistered, created, updated)
    )
    user_id = cursor.lastrowid
    registration_key = generate_registration_key()
    hashed_registration_key = bcrypt.hashpw(registration_key.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO Registration (userid, registrationkey, created, updated) VALUES (?, ?, ?, ?)",
        (user_id, hashed_registration_key, created, updated)
    )
    return {"success": True}

def put_user(cursor, data):
    user_id = data.get('id')
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    orgname = data.get('orgname')
    mobile = data.get('mobile')
    isEmailVerified = data.get('isEmailVerified', 0)
    isRegistered = data.get('isRegistered', 0)
    updated = data.get('updated')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()) if password else None
    if hashed_password:
        cursor.execute("UPDATE Users SET firstname=?, lastname=?, username=?, password=?, email=?, orgname=?, mobile=?, isEmailVerified=?, isRegistered=?, updated=? WHERE id=?", (firstname, lastname, username, hashed_password, email, orgname, mobile, isEmailVerified, isRegistered, updated, user_id))
    else:
        cursor.execute("UPDATE Users SET firstname=?, lastname=?, username=?, email=?, orgname=?, mobile=?, isEmailVerified=?, isRegistered=?, updated=? WHERE id=?", (firstname, lastname, username, email, orgname, mobile, isEmailVerified, isRegistered, updated, user_id))

def delete_user(cursor, data):
    user_id = data.get('id')
    cursor.execute("DELETE FROM Users WHERE id=?", (user_id,))

def get_registrations(cursor):
    cursor.execute("SELECT id, userid, emailOTP, registrationkey, created, updated FROM Registration")
    rows = cursor.fetchall()
    return [{
        "id": row[0],
        "userid": row[1],
        "emailOTP": row[2],
        "registrationkey": row[3],
        "created": row[4],
        "updated": row[5]
    } for row in rows]

def post_registration(cursor, data):
    userid = data.get('userid')
    emailOTP = data.get('emailOTP')
    registrationkey = data.get('registrationkey')
    created = data.get('created')
    updated = data.get('updated')
    cursor.execute(
        "INSERT INTO Registration (userid, emailOTP, registrationkey, created, updated) VALUES (?, ?, ?, ?, ?)",
        (userid, emailOTP, registrationkey, created, updated)
    )

def put_registration(cursor, data):
    reg_id = data.get('id')
    userid = data.get('userid')
    emailOTP = data.get('emailOTP')
    registrationkey = data.get('registrationkey')
    updated = data.get('updated')
    cursor.execute(
        "UPDATE Registration SET userid=?, emailOTP=?, registrationkey=?, updated=? WHERE id=?",
        (userid, emailOTP, registrationkey, updated, reg_id)
    )

def delete_registration(cursor, data):
    reg_id = data.get('id')
    cursor.execute("DELETE FROM Registration WHERE id=?", (reg_id,))

@app.route('/api/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
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
            verification_link = f"http://127.0.0.1:5000/api/verify-email?email={email}&token={verification_token}"
            print(f"[DEBUG] About to call send_email_verification for {email} with link: {verification_link}")
            send_email_verification(email, verification_link)
            print(f"[DEBUG] send_email_verification finished for {email}")
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

@app.route('/api/registrations', methods=['GET', 'POST', 'PUT', 'DELETE'])
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

@app.route('/api/login', methods=['POST'])
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

@app.route('/api/verify', methods=['POST'])
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

def send_professional_email(to_email, subject, heading, message, action_text, action_link):
    import datetime
    current_year = datetime.datetime.now().year
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'bengie.dulay@gmail.com'
    SMTP_PASSWORD = 'mggv tlgu wxad munf'
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    # Only include the button if action_text and action_link are provided
    button_html = f"""
            <div style='text-align:center;margin:30px 0;'>
                <a href='{action_link}' style='background:#2980b9;color:#fff;padding:12px 24px;border-radius:5px;text-decoration:none;font-weight:bold;font-size:16px;'>{action_text}</a>
            </div>
    """ if action_text and action_link else ""
    html_content = f"""
    <html>
    <body style='font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;'>
        <div style='max-width: 500px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #eee; padding: 30px;'>
            <div style='text-align: center;'>
                <img src='cid:iconimage' alt='Praisehub' style='width:64px;height:64px;margin-bottom:20px;'>
            </div>
            <h2 style='color: #2c3e50;'>{heading}</h2>
            <p>{message}</p>
            {button_html}
            <hr style='margin:30px 0;'>
            <p style='font-size:12px;color:#888;'>Praisehub &copy; {current_year}</p>
        </div>
    </body>
    </html>
    """
    msg.set_content(f"{heading}\n{message}\n{action_text}: {action_link}")
    msg.add_alternative(html_content, subtype='html')
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    try:
        with open(icon_path, 'rb') as img:
            msg.get_payload()[1].add_related(img.read(), 'image', 'x-icon', cid='iconimage')
    except Exception as e:
        print(f"Could not attach icon.ico: {e}")
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

# Update send_registration_email to use the new function

def send_registration_email(to_email, otp, registration_key):
    registration_message = f"Thank you for signing up. Please use the details below to complete your registration:<br><br>"
    registration_message += f"<b>OTP:</b> {otp}<br><b>Registration Key:</b> {registration_key}<br><br>If you did not request this registration, please ignore this email."
    send_professional_email(
        to_email,
        'Praisehub - Registration Details',
        'Praisehub!',
        registration_message,
        'Complete Registration',
        'https://yourdomain.com/verify'  # You can update this to your actual verification page
    )

def send_email_verification(to_email, verification_link):
    verification_message = "Click the button below to verify your email address."
    send_professional_email(
        to_email,
        'Praisehub - Email Verification',
        'Verify Your Email',
        verification_message,
        'Verify Email',
        verification_link
    )

@app.route('/api/register', methods=['POST'])
def register():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(success=False, error=f"Database file not found: {db_path}"), 404
    data = request.json
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    post_user(cursor, data)
    conn.commit()
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
        verification_link = f"http://127.0.0.1:5000/api/verify-email?email={email}&token={verification_token}"
        send_email_verification(email, verification_link)
    conn.close()
    return jsonify(success=True)

@app.route('/api/verify-email', methods=['GET'])
def verify_email():
    email = request.args.get('email')
    token = request.args.get('token')
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    html_path = os.path.join(os.path.dirname(__file__), 'static', 'praisehub.html')
    if not os.path.exists(db_path):
        return open(html_path).read().replace('{MESSAGE}', 'Database file not found.'), 200, {'Content-Type': 'text/html'}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, isEmailVerified FROM Users WHERE email=?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return open(html_path).read().replace('{MESSAGE}', 'User not found.'), 200, {'Content-Type': 'text/html'}
    user_id, is_verified = user_row
    if is_verified:
        conn.close()
        return open(html_path).read().replace('{MESSAGE}', 'Email already verified. You may close this page.'), 200, {'Content-Type': 'text/html'}
    cursor.execute("SELECT registrationkey FROM Registration WHERE userid=?", (user_id,))
    reg_row = cursor.fetchone()
    if not reg_row or reg_row[0] != token:
        conn.close()
        return open(html_path).read().replace('{MESSAGE}', 'Invalid verification link.'), 200, {'Content-Type': 'text/html'}
    cursor.execute("UPDATE Users SET isEmailVerified=1 WHERE id=?", (user_id,))
    conn.commit()
    # Send registration key email
    registration_key = generate_registration_key(32)
    hashed_registration_key = bcrypt.hashpw(registration_key.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("UPDATE Registration SET registrationkey=? WHERE userid=?", (hashed_registration_key, user_id))
    conn.commit()
    send_professional_email(
        email,
        'Welcome to Praisehub',
        'Registration Key',
        f"Your registration key is: <b>{registration_key}</b>",
        '',
        ''
    )
    conn.close()
    html = open(html_path).read()
    html = html.replace('{MESSAGE}', 'Email verified and registration key sent. You may close this page.')
    return html, 200, {'Content-Type': 'text/html'}

@app.route('/api/profile', methods=['POST'])
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

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    token = data.get('token')
    new_password = data.get('new_password')
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
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
    import datetime
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

@app.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.json
    email = data.get('email')
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
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
    reset_link = f"http://127.0.0.1:5000/static/praisehub.html?email={email}&token={reset_token}"
    send_password_reset_email(email, reset_link)
    return jsonify(success=True)

# Add this helper function

def send_password_reset_email(to_email, reset_link):
    reset_message = "Click the button below to reset your password. If you did not request a password reset, please ignore this email."
    send_professional_email(
        to_email,
        'Praisehub - Password Reset Request',
        'Password Reset Request',
        reset_message,
        'Reset Password',
        reset_link
    )

@app.route('/api/check-reset-token', methods=['POST'])
def check_reset_token():
    data = request.json
    email = data.get('email')
    token = data.get('token')
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
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
    import datetime
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

@app.route('/reset-password', methods=['GET'])
def reset_password_page():
    email = request.args.get('email')
    token = request.args.get('token')
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    html_path = os.path.join(os.path.dirname(__file__), 'static', 'praisehub.html')
    if not os.path.exists(db_path):
        return open(html_path).read().replace('{MESSAGE}', 'Database file not found.'), 200, {'Content-Type': 'text/html'}
    if not email or not token:
        return open(html_path).read().replace('{MESSAGE}', 'Invalid or missing reset link.'), 200, {'Content-Type': 'text/html'}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, token, created, used FROM PasswordReset
        WHERE email=? ORDER BY created DESC LIMIT 1
    """, (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return open(html_path).read().replace('{MESSAGE}', 'Reset link not found or already used.'), 200, {'Content-Type': 'text/html'}
    reset_id, db_token, created, used = row
    import datetime
    created_time = datetime.datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
    expired = (datetime.datetime.utcnow() - created_time).total_seconds() > 300
    if used == 1:
        conn.close()
        return open(html_path).read().replace('{MESSAGE}', 'This reset link has already been used.'), 200, {'Content-Type': 'text/html'}
    if expired:
        conn.close()
        return open(html_path).read().replace('{MESSAGE}', 'This reset link has expired.'), 200, {'Content-Type': 'text/html'}
    if not bcrypt.checkpw(token.encode('utf-8'), db_token):
        conn.close()
        return open(html_path).read().replace('{MESSAGE}', 'Invalid reset link.'), 200, {'Content-Type': 'text/html'}
    conn.close()
    # Valid link, show reset form (leave {MESSAGE} for JS)
    return open(html_path).read(), 200, {'Content-Type': 'text/html'}

# Ensure 'mobile' column exists in Users table
try:
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'mobile' not in columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN mobile TEXT")
            conn.commit()
        conn.close()
except Exception as e:
    print(f"[DB MIGRATION] Could not add 'mobile' column: {e}")

@app.route('/api/refresher')
def refresher():
    return jsonify({"status": "ok", "message": "Refresher ping successful."})

def start_refresher():
    def refresher_loop():
        while True:
            try:
                # Prefer RENDER_EXTERNAL_URL, fallback to a hardcoded public URL, then localhost
                url = (
                    os.environ.get("RENDER_EXTERNAL_URL") or
                    "https://bibleapi-uswk.onrender.com"  # <-- replace with your actual Render URL
                ) + "/api/refresher"
                resp = requests.get(url, timeout=10)
                print(f"[Refresher] Pinged {url}, status: {resp.status_code}")
            except Exception as e:
                print(f"[Refresher] Exception: {e}")
            time.sleep(420)  # selfping every 7 minutes
    t = threading.Thread(target=refresher_loop, daemon=True)
    t.start()

if __name__ == "__main__":
    start_refresher()
    app.run(host="0.0.0.0", port=5000, debug=True)
