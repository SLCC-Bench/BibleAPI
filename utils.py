# ...move all helper functions here, e.g.:
import bcrypt
import random
import string
import os

BASE_URL = "https://bibleapi-uswk.onrender.com"

def generate_registration_key(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ...other helpers: send_professional_email, send_email_verification, get_users, post_user, etc.
