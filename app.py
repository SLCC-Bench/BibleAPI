from flask import Flask
from routes.users import users_bp
from routes.auth import auth_bp
from routes.bible import bible_bp
from routes.registration import registration_bp
from routes.password import password_bp

app = Flask(__name__, static_folder="static")

# Register blueprints without url_prefix
app.register_blueprint(users_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(bible_bp)
app.register_blueprint(registration_bp)
app.register_blueprint(password_bp)

if __name__ == "__main__":
    print("Registered routes:", app.url_map)  # Debug print
    app.run(port=5000, debug=True)