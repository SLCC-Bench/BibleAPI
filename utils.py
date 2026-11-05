import bcrypt

def get_users(cursor):
    cursor.execute("SELECT id, firstname, lastname, username, orgname, mobile, isRegistered, created, updated FROM Users")
    rows = cursor.fetchall()
    return [{
        "id": row[0],
        "firstname": row[1],
        "lastname": row[2],
        "username": row[3],
        "orgname": row[4],
        "mobile": row[5],
        "isRegistered": row[6],
        "created": row[7],
        "updated": row[8]
    } for row in rows]

def post_user(cursor, data):
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    username = data.get('username')
    password = data.get('password')
    orgname = data.get('orgname')
    mobile = data.get('mobile')
    isRegistered = data.get('isRegistered', 0)
    created = data.get('created')
    updated = data.get('updated')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO Users (firstname, lastname, username, password, orgname, mobile, isRegistered, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (firstname, lastname, username, hashed_password, orgname, mobile, isRegistered, created, updated)
    )
    return {"success": True}

def put_user(cursor, data):
    user_id = data.get('id')
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    username = data.get('username')
    password = data.get('password')
    orgname = data.get('orgname')
    mobile = data.get('mobile')
    isRegistered = data.get('isRegistered', 0)
    updated = data.get('updated')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()) if password else None
    if hashed_password:
        cursor.execute("UPDATE Users SET firstname=?, lastname=?, username=?, password=?, orgname=?, mobile=?, isRegistered=?, updated=? WHERE id=?", (firstname, lastname, username, hashed_password, orgname, mobile, isRegistered, updated, user_id))
    else:
        cursor.execute("UPDATE Users SET firstname=?, lastname=?, username=?, orgname=?, mobile=?, isRegistered=?, updated=? WHERE id=?", (firstname, lastname, username, orgname, mobile, isRegistered, updated, user_id))

def delete_user(cursor, data):
    user_id = data.get('id')
    cursor.execute("DELETE FROM Users WHERE id=?", (user_id,))
