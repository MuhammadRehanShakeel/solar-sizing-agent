"""
config.py - ALL settings for SolarSaathi live here.

Secrets (database, API keys) come from backend/.env. Prices are NOT here: they live in the
database (Prices table) so the installer can change them from the admin page without coding.
"""
import os

from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))


def _env(name: str, default=None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise RuntimeError(f"Missing setting '{name}' in backend/.env. "
                           f"Copy backend/.env.example to backend/.env and fill it in.")
    return value


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


# ---------------------------------------------------------------------------
# 1. Database - SolarSaathi has its OWN database on your SQL Server
# ---------------------------------------------------------------------------
DB_SERVER = _env("DB_SERVER", required=True)          # e.g. REHAN\VE_SERVER
DB_NAME = _env("DB_NAME", "SolarSaathi")
DB_AUTH = _env("DB_AUTH", "windows").lower()          # "windows" or "sql"
DB_USER = _env("DB_USER", "")
DB_PASSWORD = _env("DB_PASSWORD", "")
DB_DRIVER = _env("DB_DRIVER", "ODBC Driver 17 for SQL Server")

# ---------------------------------------------------------------------------
# 2. Free AI models (keys from .env - never put keys in code or chat)
# ---------------------------------------------------------------------------
GROQ_API_KEY = _env("GROQ_API_KEY", "")               # https://console.groq.com/keys
GEMINI_API_KEY = _env("GEMINI_API_KEY", "")           # https://aistudio.google.com/apikey
GROQ_MODEL = _env("GROQ_MODEL", "openai/gpt-oss-120b")          # chat + tool calling (fast)
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-3.8-flash")          # bill photos + backup chat
WHISPER_MODEL = _env("WHISPER_MODEL", "whisper-large-v3-turbo")  # voice -> text (Groq)
LLM_TEMPERATURE = 0.2
LLM_TIMEOUT_SECONDS = 40

# ---------------------------------------------------------------------------
# 3. Agent guard rails (protect the free quota and keep chats on topic)
# ---------------------------------------------------------------------------
MAX_MESSAGE_CHARS = 1000
MAX_TURNS_PER_SESSION = 40
HISTORY_MESSAGES = 16                                 # how many earlier messages the AI sees
MAX_AGENT_STEPS = 8                                   # tool calls + answers per user message
MAX_BILL_MB = 6
MAX_AUDIO_MB = 3
BILL_TYPES = {"image/jpeg", "image/png", "image/webp"}

# ---------------------------------------------------------------------------
# 4. Login & security (staff only - customers never need an account)
# ---------------------------------------------------------------------------
JWT_SECRET = _env("JWT_SECRET", required=True)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = _env_int("JWT_EXPIRE_MINUTES", 240)
ROLES = ("admin", "sales")                            # admin: prices + users; sales: leads
PASSWORD_MIN_LENGTH = 8
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCK_MINUTES = 15

RATE_LIMIT_LOGIN = (10, 60)                           # (requests, per seconds) per IP
RATE_LIMIT_CHAT = (20, 60)
RATE_LIMIT_BILL = (6, 600)
RATE_LIMIT_VOICE = (20, 600)
RATE_LIMIT_DEFAULT = (300, 60)

API_HOST = _env("API_HOST", "127.0.0.1")              # 0.0.0.0 to use the phone app on your Wi-Fi
API_PORT = _env_int("API_PORT", 5002)                 # 5000 FYP, 5001 RoadGuard, 5002 SolarSaathi
CORS_ORIGINS = [o.strip() for o in _env(
    "CORS_ORIGINS", "http://localhost:5175,http://127.0.0.1:5175,capacitor://localhost,http://localhost"
).split(",") if o.strip()]

# ---------------------------------------------------------------------------
# 5. Quotation
# ---------------------------------------------------------------------------
INSTALLER_NAME = _env("INSTALLER_NAME", "SolarSaathi Demo Installers")
INSTALLER_PHONE = _env("INSTALLER_PHONE", "0300-0000000")
PUBLIC_BASE_URL = _env("PUBLIC_BASE_URL", "http://localhost:5175")
QUOTE_VALID_DAYS = 7

# ---------------------------------------------------------------------------
# 6. Sunlight data, packages and financing
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(BACKEND_DIR, "data")          # cache files (git-ignored)
USE_NASA_SUNLIGHT = _env("USE_NASA_SUNLIGHT", "1") == "1"
NASA_TIMEOUT_SECONDS = 8
DAYLIGHT_HOURS = (8, 17)                              # when panels make useful power (8 am - 5 pm)
INSTALMENT_MONTHS = (12, 24, 36)
