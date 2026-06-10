import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from config import Config
from auth.routes import auth_bp
from timesheet import timesheet_bp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, "../frontend/build")

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path="")
app.config.from_object(Config)

app.config.update(
    SECRET_KEY=Config.SECRET_KEY,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_PATH="/",
)

CORS(app, supports_credentials=True, origins=[Config.FRONTEND_URL])

app.register_blueprint(auth_bp)
app.register_blueprint(timesheet_bp)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    full_path = os.path.join(app.static_folder, path)
    if os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
