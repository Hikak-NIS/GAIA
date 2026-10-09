import uuid
from sqlalchemy import String, Float, Boolean, ForeignKey, JSON, Integer, Text, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from .config import Base, utcnow
from .utc_types import UTCDateTime


def uid():
    return str(uuid.uuid4())


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)


class User(Identity, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)


class AuthSession(Identity, Base):
    __tablename__ = "auth_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[object] = mapped_column(UTCDateTime())


class LoginAttempt(Identity, Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow, index=True)


class Territory(Identity, Base):
    __tablename__ = "territories"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    polygon: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    area: Mapped[float] = mapped_column(Float, default=100)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Almaty")
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class TerritoryChild(Identity):
    territory_id: Mapped[str] = mapped_column(ForeignKey("territories.id", ondelete="CASCADE"), index=True)


class Sensor(TerritoryChild, Base):
    __tablename__ = "sensors"

    name: Mapped[str] = mapped_column(String(100), default="Виртуальная станция")
    source: Mapped[str] = mapped_column(String(20), default="simulated")
    credential_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)


class SensorReading(TerritoryChild, Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (UniqueConstraint("sensor_id", "timestamp", name="uq_sensor_readings_sensor_timestamp"),)
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensors.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[object] = mapped_column(UTCDateTime(), index=True)
    received_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    source: Mapped[str] = mapped_column(String(20))
    air_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_moisture_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_lux: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_hpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[str] = mapped_column(String(20), default="valid")
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class SimulationSession(TerritoryChild, Base):
    __tablename__ = "simulation_sessions"
    __table_args__ = (UniqueConstraint("territory_id"),)
    status: Mapped[str] = mapped_column(String(20), default="stopped")
    scenario: Mapped[str] = mapped_column(String(30), default="normal")
    seed: Mapped[int] = mapped_column(Integer, default=42)
    speed: Mapped[int] = mapped_column(Integer, default=60)
    tick_index: Mapped[int] = mapped_column(Integer, default=0)
    clock: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    soil: Mapped[float] = mapped_column(Float, default=34)
    reservoir_l: Mapped[float] = mapped_column(Float, default=100)
    total_water_l: Mapped[float] = mapped_column(Float, default=0)


class IrrigationZone(TerritoryChild, Base):
    __tablename__ = "irrigation_zones"
    __table_args__ = (UniqueConstraint("territory_id"),)
    name: Mapped[str] = mapped_column(String(100), default="Основная зона")
    pump_on: Mapped[bool] = mapped_column(Boolean, default=False)
    emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    stopped_at: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    deadline: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    run_water_l: Mapped[float] = mapped_column(Float, default=0)
    daily_water_l: Mapped[float] = mapped_column(Float, default=0)
    water_day: Mapped[str] = mapped_column(String(10), default="")


class IrrigationRule(TerritoryChild, Base):
    __tablename__ = "irrigation_rules"
    __table_args__ = (UniqueConstraint("territory_id"),)
    mode: Mapped[str] = mapped_column(String(20), default="off")
    trigger_pct: Mapped[float] = mapped_column(Float, default=30)
    target_pct: Mapped[float] = mapped_column(Float, default=45)
    max_duration_s: Mapped[int] = mapped_column(Integer, default=1200)
    cooldown_s: Mapped[int] = mapped_column(Integer, default=1800)
    daily_limit_l: Mapped[float] = mapped_column(Float, default=30)
    min_reservoir_l: Mapped[float] = mapped_column(Float, default=5)
    block_rain: Mapped[bool] = mapped_column(Boolean, default=False)
    rain_threshold_pct: Mapped[float] = mapped_column(Float, default=60)


class IrrigationEvent(TerritoryChild, Base):
    __tablename__ = "irrigation_events"
    timestamp: Mapped[object] = mapped_column(UTCDateTime(), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)
    trigger_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value: Mapped[float] = mapped_column(Float)
    duration_s: Mapped[float] = mapped_column(Float, default=0)
    estimated_water_l: Mapped[float] = mapped_column(Float, default=0)
    actor: Mapped[str] = mapped_column(String(20))


class Observation(TerritoryChild, Base):
    __tablename__ = "observations"
    source: Mapped[str] = mapped_column(String(20), default="manual")
    category: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[object] = mapped_column(UTCDateTime())
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    photo_path: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Alert(TerritoryChild, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "uq_alerts_active_code",
            "territory_id",
            "code",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )
    code: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")
    title: Mapped[str] = mapped_column(String(200))
    explanation: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(UTCDateTime())
    resolved_at: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)


class WeatherSnapshot(TerritoryChild, Base):
    __tablename__ = "weather_snapshots"
    source: Mapped[str] = mapped_column(String(20), default="weather")
    fetched_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    data: Mapped[dict] = mapped_column(JSON)


class SatelliteLayerMetadata(TerritoryChild, Base):
    __tablename__ = "satellite_layers"
    source: Mapped[str] = mapped_column(String(20), default="satellite")
    provider: Mapped[str] = mapped_column(String(50), default="NASA GIBS")
    layer: Mapped[str] = mapped_column(String(100), default="MODIS_Terra_CorrectedReflectance_TrueColor")
    resolution_m: Mapped[int] = mapped_column(Integer, default=250)


class DailyReport(TerritoryChild, Base):
    __tablename__ = "daily_reports"
    period_start: Mapped[object] = mapped_column(UTCDateTime())
    period_end: Mapped[object] = mapped_column(UTCDateTime())
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    data: Mapped[dict] = mapped_column(JSON)


# Register inventory models for Alembic and test metadata.
from . import foundation_models as foundation_models  # noqa: E402,F401
