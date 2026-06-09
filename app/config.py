import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    JSON_AS_ASCII = False

    APP_NAME = "Soyoung Data Assistant"
    APP_VERSION = "0.1.0"

    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
