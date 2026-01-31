import bcrypt
import random
import string
import os

BASE_URL = "https://bibleapi-uswk.onrender.com"
# BASE_URL = "http://127.0.0.1:5000"

def generate_registration_key(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

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

def send_professional_email(to_email, subject, heading, message, action_text, action_link):
    import datetime
    from email.message import EmailMessage
    import smtplib
    current_year = datetime.datetime.now().year
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'bengie.dulay@gmail.com'
    SMTP_PASSWORD = '[REDACTED]'
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
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
