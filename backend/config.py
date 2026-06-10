import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
    MICROSOFT_REDIRECT_URI = os.getenv(
        "MICROSOFT_REDIRECT_URI", "http://localhost:5000/auth/callback"
    )
    MICROSOFT_AUTHORITY = (
        f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}"
    )
    MICROSOFT_SCOPE = ["User.Read", "Files.Read", "offline_access", "Files.ReadWrite", "User.ReadBasic.All"]
    ONEDRIVE_ROOT_PATH = os.getenv("ONEDRIVE_ROOT_PATH", "/Timesheets")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

    GPTBOTS_API_KEY = os.getenv("GPTBOTS_API_KEY", "")
    GPTBOTS_ENDPOINT = os.getenv("GPTBOTS_ENDPOINT", "")
