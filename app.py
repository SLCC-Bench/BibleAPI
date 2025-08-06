from flask import Flask
from routes.users import users_bp
from routes.auth import auth_bp
from routes.bible import bible_bp
from routes.registration import registration_bp
from routes.password import password_bp
from routes.uploadBible import upload_bible_bp
from routes.updateBible import update_bible_bp
import os

app = Flask(__name__, static_folder="static")

# Register blueprints without url_prefix
app.register_blueprint(users_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(bible_bp)
app.register_blueprint(registration_bp)
app.register_blueprint(password_bp)
app.register_blueprint(upload_bible_bp)
app.register_blueprint(update_bible_bp)

@app.route("/", methods=["GET", "POST"])
def index():
    return "Praisehub API is running."

@app.route("/healthz", methods=["GET"])
def healthz():
    return "ok", 200

# Debug endpoint to list all routes (optional, for troubleshooting)
@app.route("/routes", methods=["GET"])
def show_routes():
    return {"routes": [str(rule) for rule in app.url_map.iter_rules()]}

if __name__ == "__main__":
    print("Registered routes:", app.url_map)  # Debug print
    # Use 0.0.0.0 for host so it works on Render.com and other cloud platforms
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)