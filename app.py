from config_loader import load_config_into_environ

# Load desktop/local config before DB init and route imports that may touch env.
_CONFIG = load_config_into_environ()

from flask import Flask, send_from_directory
from routes.users import users_bp
from routes.bible import bible_bp
from routes.uploadBible import upload_bible_bp
from routes.updateBible import update_bible_bp
from routes.webhook import webhook_bp
from routes.languages import languages_bp
from routes.songs import songs_bp
from routes.admin import admin_bp
from db import init_db
from flask_cors import CORS
import os
import sys
import threading
import urllib.request

_IS_LOCAL = os.environ.get("BIBLEAPI_LOCAL", "").lower() in ("1", "true", "yes")
_IS_FROZEN = getattr(sys, "frozen", False)
_INIT_DB_ONLY = "--init-db" in sys.argv[1:]

app = Flask(__name__, static_folder="static")

if _IS_LOCAL or _IS_FROZEN:
    from local_security import install_local_security
    install_local_security(app)

# Electron (file:// / localhost) + existing GitHub Pages admin UI
CORS(
    app,
    origins=[
        "https://slcc-bench.github.io",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "null",  # file:// origins often send Origin: null
    ],
    supports_credentials=False,
)

# Desktop clients use the deployed cloud schema; only the hosted service maintains it.
if not _IS_LOCAL and not _IS_FROZEN and not _INIT_DB_ONLY:
    try:
        init_db()
        print("MySQL tables initialized.")
    except Exception as e:
        print(f"WARNING: Could not initialize MySQL tables: {e}")

# Register blueprints without url_prefix
app.register_blueprint(users_bp)
app.register_blueprint(bible_bp)
app.register_blueprint(upload_bible_bp)
app.register_blueprint(update_bible_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(languages_bp)
app.register_blueprint(songs_bp)
app.register_blueprint(admin_bp)

@app.route("/", methods=["GET"])
def index():
    return send_from_directory(app.static_folder, "praisehub.html")

@app.route("/healthz", methods=["GET"])
def healthz():
    return "ok", 200

@app.route("/readyz", methods=["GET"])
def readyz():
    """Liveness for process is /healthz; this checks TiDB connectivity."""
    try:
        from db import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            conn.close()
        return "ok", 200
    except Exception:
        return {"ok": False, "error": "Database is not ready."}, 503

# Debug endpoint to list all routes (optional, for troubleshooting)
@app.route("/routes", methods=["GET"])
def show_routes():
    return {"routes": [str(rule) for rule in app.url_map.iter_rules()]}

def keep_alive():
    url = "https://bibleapi-uswk.onrender.com/healthz"
    while True:
        try:
            urllib.request.urlopen(url, timeout=10)
            print(f"[keep-alive] pinged {url}")
        except Exception as e:
            print(f"[keep-alive] ping failed: {e}")
        threading.Event().wait(300)  # 5 minutes

# Keep-alive is only for the hosted Render free-tier sleeper — skip in desktop/local mode.
if not _IS_LOCAL and not _IS_FROZEN and not _INIT_DB_ONLY:
    threading.Thread(target=keep_alive, daemon=True).start()
    print("[keep-alive] thread started, pinging every 5 minutes.")
else:
    print("[keep-alive] disabled (local/desktop mode).")

def main():
    if _INIT_DB_ONLY:
        init_db()
        print("MySQL tables initialized.")
        return
    port = int(os.environ.get("PORT", 5000))
    debug = (not _IS_LOCAL and not _IS_FROZEN) and os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    host = '127.0.0.1' if _IS_LOCAL or _IS_FROZEN else '0.0.0.0'
    print(f"[bibleapi] starting on {host}:{port} local={_IS_LOCAL} frozen={_IS_FROZEN} debug={debug}")
    print(f"[bibleapi] db host={_CONFIG.get('MYSQL_HOST')} db={_CONFIG.get('MYSQL_DB')}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    main()
