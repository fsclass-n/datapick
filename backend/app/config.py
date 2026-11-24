import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


class Settings:
    app_env = os.getenv("APP_ENV", "local")
    secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
    # 운영 관리자 계정 (비우면 운영 관리자 로그인 비활성)
    admin_email = os.getenv("ADMIN_EMAIL", "operator@dataquill.io").lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

    database_url = os.getenv("DATABASE_URL", "sqlite:///./storage/dataquill.db")
    db_ssl = _bool("DB_SSL")
    db_ssl_ca = os.getenv("DB_SSL_CA", "")

    storage_dir = _path(os.getenv("STORAGE_DIR", "./storage/uploads"))
    seed_test_accounts = _bool("SEED_TEST_ACCOUNTS", True)

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,https://dataquill.onrender.com").split(",") if o.strip()]

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    oauth = {
        "google": (os.getenv("GOOGLE_CLIENT_ID", ""), os.getenv("GOOGLE_CLIENT_SECRET", "")),
        "naver": (os.getenv("NAVER_CLIENT_ID", ""), os.getenv("NAVER_CLIENT_SECRET", "")),
        "kakao": (os.getenv("KAKAO_CLIENT_ID", ""), os.getenv("KAKAO_CLIENT_SECRET", "")),
    }


settings = Settings()
