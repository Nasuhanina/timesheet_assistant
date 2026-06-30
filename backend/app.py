import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from auth.routes import auth_bp
from timesheet import timesheet_bp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, "../frontend/build")

app = Flask(__name__, static_folder=os.path.join(STATIC_FOLDER, "static"), static_url_path="/static")
app.config.from_object(Config)

if Config.IS_CLOUD_RUN:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

app.config.update(
    SECRET_KEY=Config.SECRET_KEY,
    DEBUG=Config.DEBUG,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=Config.SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_PATH="/",
)

cors_origins = [Config.FRONTEND_URL]
if not Config.IS_CLOUD_RUN:
    cors_origins.append("http://localhost:3000")
CORS(app, supports_credentials=True, origins=cors_origins)

app.register_blueprint(auth_bp)
app.register_blueprint(timesheet_bp)


@app.route("/")
def index():
    return send_from_directory(STATIC_FOLDER, "index.html")


@app.route("/<path:path>")
def static_files(path):
    full_path = os.path.join(STATIC_FOLDER, path)
    if os.path.exists(full_path):
        return send_from_directory(STATIC_FOLDER, path)
    return send_from_directory(STATIC_FOLDER, "index.html")


if __name__ == "__main__":
    app.run(debug=Config.DEBUG, port=5000, host="0.0.0.0")
