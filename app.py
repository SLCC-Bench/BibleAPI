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
    cursor.execute("SELECT id, firstname, lastname, username, email, orgname, isEmailVerified, isRegistered, created, updated FROM Users")
    rows = cursor.fetchall()
    return [{
        "id": row[0],
        "firstname": row[1],
        "lastname": row[2],
        "username": row[3],
        "email": row[4],
        "orgname": row[5],
        "isEmailVerified": row[6],
        "isRegistered": row[7],
        "created": row[8],
        "updated": row[9]
    } for row in rows]

def post_user(cursor, data):
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    orgname = data.get('orgname')
    isEmailVerified = data.get('isEmailVerified', 0)
    isRegistered = data.get('isRegistered', 0)
    created = data.get('created')
    updated = data.get('updated')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO Users (firstname, lastname, username, password, email, orgname, isEmailVerified, isRegistered, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (firstname, lastname, username, hashed_password, email, orgname, isEmailVerified, isRegistered, created, updated)
    )
    user_id = cursor.lastrowid
    otp = generate_otp()
    registration_key = generate_registration_key()
    hashed_registration_key = bcrypt.hashpw(registration_key.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO Registration (userid, emailOTP, registrationkey, created, updated) VALUES (?, ?, ?, ?, ?)",
        (user_id, otp, hashed_registration_key, created, updated)
    )
    send_registration_email(email, otp, registration_key)
    return {"success": True}

def put_user(cursor, data):
    user_id = data.get('id')
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    orgname = data.get('orgname')
    isEmailVerified = data.get('isEmailVerified', 0)
    isRegistered = data.get('isRegistered', 0)
    updated = data.get('updated')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()) if password else None
    if hashed_password:
        cursor.execute("UPDATE Users SET firstname=?, lastname=?, username=?, password=?, email=?, orgname=?, isEmailVerified=?, isRegistered=?, updated=? WHERE id=?", (firstname, lastname, username, hashed_password, email, orgname, isEmailVerified, isRegistered, updated, user_id))
    else:
        cursor.execute("UPDATE Users SET firstname=?, lastname=?, username=?, email=?, orgname=?, isEmailVerified=?, isRegistered=?, updated=? WHERE id=?", (firstname, lastname, username, email, orgname, isEmailVerified, isRegistered, updated, user_id))

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
    if request.method == 'GET':
        result = get_users(cursor)
        conn.close()
        return jsonify(users=result)
    elif request.method == 'POST':
        data = request.json
        post_user(cursor, data)
        conn.commit()
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
    registration_key = data.get('registrationkey')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, isRegistered FROM Users WHERE username=?", (username,))
    row = cursor.fetchone()
    if row:
        user_id, hashed_password, isRegistered = row
        cursor.execute("SELECT registrationkey FROM Registration WHERE userid=?", (user_id,))
        reg_row = cursor.fetchone()
        conn.close()
        if not isRegistered:
            return jsonify(success=False, error="User is not registered"), 403
        if not reg_row or not bcrypt.checkpw(registration_key.encode('utf-8'), reg_row[0]):
            return jsonify(success=False, error="Invalid registration key"), 401
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            return jsonify(success=True, user_id=user_id)
        else:
            return jsonify(success=False, error="Invalid password"), 401
    else:
        conn.close()
        return jsonify(success=False, error="User not found"), 404

@app.route('/api/verify', methods=['POST'])
def verify_user():
    db_folder = os.path.join(os.path.dirname(__file__), 'db')
    db_path = os.path.join(db_folder, 'Praisehub.SQLite3')
    if not os.path.exists(db_path):
        return jsonify(error=f"Database file not found: {db_path}"), 404
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    registration_key = data.get('registrationkey')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users WHERE email=?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return jsonify(success=False, error="User not found"), 404
    user_id = user_row[0]
    cursor.execute("SELECT emailOTP, registrationkey FROM Registration WHERE userid=?", (user_id,))
    reg_row = cursor.fetchone()
    if not reg_row:
        conn.close()
        return jsonify(success=False, error="Registration not found"), 404
    db_otp, db_registration_key = reg_row
    if str(db_otp) == str(otp) and bcrypt.checkpw(registration_key.encode('utf-8'), db_registration_key):
        cursor.execute("UPDATE Users SET isRegistered=1, isEmailVerified=1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify(success=True)
    else:
        conn.close()
        return jsonify(success=False, error="Invalid OTP or registration key"), 401

def send_registration_email(to_email, otp, registration_key):
    # Configure your SMTP server details
    SMTP_SERVER = 'smtp.gmail.com'  # Replace with your SMTP server
    SMTP_PORT = 587
    SMTP_USERNAME = 'bengie.dulay@gmail.com'  # Replace with your email
    SMTP_PASSWORD = 'mggv tlgu wxad munf'  # Replace with your password

    msg = EmailMessage()
    msg['Subject'] = 'Welcome to SLCC Bible API - Registration Details'
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email

    # HTML email body with inline image
    html_content = f"""
    <html>
    <body style='font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;'>
        <div style='max-width: 500px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #eee; padding: 30px;'>
            <div style='text-align: center;'>
                <img src='cid:iconimage' alt='SLCC Bible API' style='width:64px;height:64px;margin-bottom:20px;'>
            </div>
            <h2 style='color: #2c3e50;'>Welcome to SLCC Bible API!</h2>
            <p>Thank you for signing up. Please use the details below to complete your registration:</p>
            <table style='width:100%;margin:20px 0;'>
                <tr><td style='font-weight:bold;'>OTP:</td><td>{otp}</td></tr>
                <tr><td style='font-weight:bold;'>Registration Key:</td><td>{registration_key}</td></tr>
            </table>
            <p>If you did not request this registration, please ignore this email.</p>
            <hr style='margin:30px 0;'>
            <p style='font-size:12px;color:#888;'>SLCC Bible API &copy; 2024</p>
        </div>
    </body>
    </html>
    """
    msg.set_content("Thank you for signing up! Your OTP and registration key are included in this email.")
    msg.add_alternative(html_content, subtype='html')

    # Attach icon.ico as inline image
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    try:
        with open(icon_path, 'rb') as img:
            msg.get_payload()[1].add_related(img.read(), 'image', 'x-icon', cid='iconimage')
    except Exception as e:
        print(f"Could not attach icon.ico: {e}")

    try:
        print(f"Connecting to SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            print("Starting TLS...")
            server.starttls()
            print("Logging in...")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print("Sending email...")
            server.send_message(msg)
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

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
    cursor.execute("SELECT firstname, lastname, email, orgname, username, password, isRegistered, isEmailVerified FROM Users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify(error="User not found"), 404
    fullname = f"{row[0]} {row[1]}"
    email = row[2]
    orgname = row[3]
    username = row[4]
    password_masked = "********"
    is_registered = row[6]
    is_email_verified = row[7]
    registration_key_masked = "********" if is_registered else ""
    profile = {
        "Fullname": fullname,
        "Email": email,
        "Organization Name": orgname,
        "Username": username,
        "Password": password_masked,
        "Registration key": registration_key_masked,
        "Email Verified": bool(is_email_verified),
        "Has Registration Key": bool(is_registered)
    }
    conn.close()
    return jsonify(profile)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
