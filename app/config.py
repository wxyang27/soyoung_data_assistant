import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    JSON_AS_ASCII = False

    APP_NAME = "Soyoung Data Assistant"
    APP_VERSION = "0.1.0"

    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
    APP_DB_PATH = os.getenv("APP_DB_PATH", str(PROJECT_ROOT / "instance" / "soyoung_data_assistant.db"))
