"""Load settings from environment variables. Secrets are not stored in source code."""

import os
from pathlib import Path

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")


def env(name, default=""):
    return os.environ.get(name, default).strip()


def env_flag(name, default="0"):
    return env(name, default).lower() in ("1", "true", "yes", "on")


SECRET_KEY = env("SECRET_KEY")
ADMIN_EMAIL = env("ADMIN_EMAIL", "admin@internmatch.local").lower()
ADMIN_PASSWORD = env("ADMIN_PASSWORD")
DEMO_STUDENT_EMAIL = env("DEMO_STUDENT_EMAIL", "demo.student@internmatch.local").lower()
DEMO_STUDENT_PASSWORD = env("DEMO_STUDENT_PASSWORD")
DEBUG = env_flag("FLASK_DEBUG", "0")
IS_PRODUCTION = env("FLASK_ENV").lower() == "production"

DB_FOLDER = _BASE_DIR / "database"
_DEFAULT_DB = DB_FOLDER / "internmatch.db"
DATABASE_URI = env("DATABASE_URI") or ("sqlite:///" + str(_DEFAULT_DB).replace("\\", "/"))


def validate_settings():
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is missing. Copy .env.example to .env and set a secret key."
        )
    if IS_PRODUCTION and not ADMIN_PASSWORD:
        raise RuntimeError("ADMIN_PASSWORD must be set in the environment for production.")
    if IS_PRODUCTION and not DEMO_STUDENT_PASSWORD:
        raise RuntimeError(
            "DEMO_STUDENT_PASSWORD must be set in the environment for production."
        )
