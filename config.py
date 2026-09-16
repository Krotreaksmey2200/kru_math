"""
Configuration settings for Math Telegram Bot.
Loads environment variables from .env and provides application constants.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Teacher Admin IDs (can be comma-separated string)
_admin_raw = os.getenv("TEACHER_ADMIN_ID", "").strip()
TEACHER_ADMIN_IDS = set()
if _admin_raw:
    for item in _admin_raw.split(","):
        cleaned = item.strip()
        if cleaned.isdigit():
            TEACHER_ADMIN_IDS.add(int(cleaned))

# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "math_bot.db")).strip()

# Lessons JSON fallback / seed path
LESSONS_JSON_PATH = str(BASE_DIR / "lessons.json")

# Google Sheet public CSV export URL (optional for dynamic sync)
GOOGLE_SHEET_CSV_URL = os.getenv("GOOGLE_SHEET_CSV_URL", "").strip()

# Google Sheet editable view URL (for opening directly in browser)
GOOGLE_SHEET_VIEW_URL = os.getenv("GOOGLE_SHEET_VIEW_URL", "https://docs.google.com/spreadsheets").strip()


# Web server port for Render / Koyeb Web Service (default 8080)
PORT = int(os.getenv("PORT", "8080"))
ENABLE_WEB_SERVER = os.getenv("ENABLE_WEB_SERVER", "true").lower() in ("true", "1", "yes")

# Self-destruct time (seconds) for group privacy notice
GROUP_NOTICE_AUTO_DELETE_SECONDS = int(os.getenv("GROUP_NOTICE_AUTO_DELETE_SECONDS", "8"))

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger("MathBot")


def is_admin(user_id: int) -> bool:
    """Check if a given user_id belongs to the teacher / admin."""
    if not TEACHER_ADMIN_IDS:
        # If no admin is configured, allow first setup or log warning
        return False
    return user_id in TEACHER_ADMIN_IDS
