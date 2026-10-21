import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    database: str = os.getenv("MONGO_DB", "survey_lab")
    secret: str = os.getenv("SECRET_KEY", "")
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    origins: tuple = tuple(
        os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000,http://localhost:8000",
        ).split(",")
    )


settings = Settings()
