"""Application settings, read once from the environment (and backend/.env)."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "HireScout"

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
RESUME_DIR = DATA_DIR / "resumes"
INDEX_DIR = DATA_DIR / "index"


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{DATA_DIR / 'hirescout.db'}"
    # Heroku/Railway/Neon style URLs use "postgres://", which SQLAlchemy rejects.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _database_url()

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    # Fine for local tinkering; tokens just stop working after a restart.
    SECRET_KEY = secrets.token_urlsafe(48)
    print("WARNING: SECRET_KEY is not set - using a random key for this process.")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
