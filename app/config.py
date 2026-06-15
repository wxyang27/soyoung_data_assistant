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

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1600"))

