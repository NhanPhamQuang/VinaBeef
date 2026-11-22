import os
from pathlib import Path
from dotenv import load_dotenv

# Root .env is shared by backend and edge gateway, never embedded in source.
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)

APP_ENV = os.getenv("APP_ENV", "development").lower()

def database_url():
    raw = os.getenv("DATABASE_URL", "sqlite:///./vinabeef_dev.db")
    if raw.startswith("postgres://"):
        raw = "postgresql+psycopg://" + raw.removeprefix("postgres://")
    elif raw.startswith("postgresql://"):
        raw = "postgresql+psycopg://" + raw.removeprefix("postgresql://")
    return raw

JWT_SECRET = os.getenv("JWT_SECRET", "vinabeef-LOCAL-DEMO-ONLY-do-not-use-in-production")
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "vinabeef-local-gateway-demo-key")
DEMO_MODE = os.getenv("DEMO_MODE", "1" if APP_ENV != "production" else "0") == "1"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


def validate_environment():
    if APP_ENV == "production":
        if JWT_SECRET == "vinabeef-LOCAL-DEMO-ONLY-do-not-use-in-production" or len(JWT_SECRET) < 32:
            raise RuntimeError("Set a strong JWT_SECRET in production")
        if GATEWAY_API_KEY == "vinabeef-local-gateway-demo-key" or len(GATEWAY_API_KEY) < 24:
            raise RuntimeError("Set a strong GATEWAY_API_KEY in production")
        if "sqlite" in database_url():
            raise RuntimeError("Configure external PostgreSQL DATABASE_URL for production")
        if DEMO_MODE:
            raise RuntimeError("Disable DEMO_MODE in production")
