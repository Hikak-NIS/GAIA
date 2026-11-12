from datetime import datetime, timezone
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "sqlite:///" + (ROOT / "data" / "gaia.db").as_posix()
    environment: str = "development"
    web_origin: str = "http://localhost:5173"
    background_enabled: bool = True
    session_days: int = 7
    legacy_simulation_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_security: str = "starttls"
    openai_api_key: str = ""
    openai_text_model: str = "gpt-4.1-mini"
    openai_transcribe_model: str = "gpt-transcribe"
    openai_speech_model: str = "gpt-4o-mini-tts"
    openai_voice: str = "coral"
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""
    earthdata_token: str = ""
    firms_map_key: str = ""
    gee_project: str = ""
    gee_service_account: str = ""
    gee_key_file: str = ""
    openmeteo_api_key: str = ""


settings = Settings()
if settings.environment == "production" and not settings.web_origin.startswith("https://"):
    raise RuntimeError("Production requires HTTPS WEB_ORIGIN")


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_setup(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")


SessionLocal = sessionmaker(engine, expire_on_commit=False)
