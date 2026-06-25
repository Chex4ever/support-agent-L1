from pathlib import Path

from dotenv import load_dotenv
import os

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)


def get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


OMNIDESK_API_KEY = get("OMNIDESK_API_KEY")
OMNIDESK_EMAIL = get("OMNIDESK_EMAIL")
OMNIDESK_PASSWORD = get("OMNIDESK_PASSWORD")
OMNIDESK_API_BASE = get("OMNIDESK_API_BASE", "https://iridi.omnidesk.ru")
HOST = get("HOST", "0.0.0.0")
PORT = int(get("PORT", "7987"))
