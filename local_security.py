"""Authentication for the loopback desktop API; hosted configuration is separate."""
from datetime import timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from threading import Lock
import time
from urllib.parse import urlsplit

from flask import jsonify, redirect, request, session
from werkzeug.security import check_password_hash


def install_local_security(app):
    credentials = json.loads((Path(__file__).parent / 'admin_credentials.json').read_text(encoding='utf-8'))
    if not credentials.get('username_hash') or not credentials.get('password_hash'):
        raise RuntimeError('Hashed local admin credentials are required.')
    app.config.update(
        SECRET_KEY=secrets.token_hex(32), SESSION_COOKIE_NAME='bibleapi_admin',
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=5),
        MAX_CONTENT_LENGTH=64 * 1024 * 1024,
    )
    runtime_token = os.environ.get('BIBLEAPI_APP_TOKEN', '')
    attempts = []
    attempt_lock = Lock()
    public_paths = {'/login', '/auth/session', '/auth/login', '/static/login.js', '/static/login.css'}

    def csrf_valid():
        supplied = request.headers.get('X-CSRF-Token', '')
        expected = session.get('csrf', '')
        return bool(expected and hmac.compare_digest(supplied.encode(), expected.encode()))

    def runtime_access():
        supplied = request.headers.get('X-Praisehub-Token', '')
        if not runtime_token or not hmac.compare_digest(supplied.encode(), runtime_token.encode()):
            return False
        if request.method == 'GET':
            return (request.path in {'/healthz', '/readyz', '/api/translations', '/api/languages',
                                     '/api/books', '/api/songs', '/api/download/bible/zip',
                                     '/static/db/bible.SQLite3', '/api/registration-codes/events'}
                    or request.path.startswith(('/api/verses/', '/api/books/', '/api/book-structure/', '/api/songs/')))
        return request.method == 'POST' and request.path in {
            '/api/registration-codes/check', '/api/registration-codes/redeem', '/api/songs',
        }

    @app.before_request
    def require_local_authentication():
        # Reject LAN access and DNS rebinding even if a forged Host reaches loopback.
        if request.remote_addr not in ('127.0.0.1', '::1') or request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
            return jsonify(error='Local access only.'), 403
        origin = request.headers.get('Origin')
        if origin and origin != 'null' and urlsplit(origin).netloc != request.host:
            return jsonify(error='Origin not allowed.'), 403
        if request.method == 'OPTIONS':
            return '', 204
        if request.path in public_paths:
            return None
        if runtime_access():
            return None
        if session.get('admin') is True:
            if request.method not in ('GET', 'HEAD') and not csrf_valid():
                return jsonify(error='Invalid CSRF token.'), 403
            return None
        if request.path.startswith('/api/') or request.path in ('/healthz', '/readyz', '/auth/logout'):
            return jsonify(error='Authentication required.'), 401
        return redirect('/login')

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        if request.path in ('/login', '/static/login.js', '/static/login.css'):
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.get('/login')
    def local_login_page():
        if session.get('admin'):
            return redirect('/static/admin.html')
        return app.send_static_file('login.html')

    @app.get('/auth/session')
    def local_admin_session():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_hex(32)
        return jsonify(authenticated=session.get('admin') is True, csrf=session['csrf'])

    @app.post('/auth/login')
    def local_admin_login():
        if not csrf_valid():
            return jsonify(error='Reload the login page and try again.'), 403
        data = request.get_json(silent=True) or {}
        username, password = data.get('username'), data.get('password')
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 256 or len(password) > 1024:
            return jsonify(error='Invalid credentials.'), 401
        now = time.monotonic()
        with attempt_lock:
            attempts[:] = [stamp for stamp in attempts if now - stamp < 60]
            if len(attempts) >= 5:
                return jsonify(error='Too many attempts. Try again in one minute.'), 429
            attempts.append(now)
        username_ok = hmac.compare_digest(hashlib.sha256(username.encode()).hexdigest(), credentials['username_hash'])
        password_ok = check_password_hash(credentials['password_hash'], password)
        if not username_ok or not password_ok:
            return jsonify(error='Invalid credentials.'), 401
        session.clear()
        session.permanent = True
        session.update(admin=True, csrf=secrets.token_hex(32))
        return jsonify(success=True)

    @app.post('/auth/logout')
    def local_admin_logout():
        session.clear()
        return jsonify(success=True)
