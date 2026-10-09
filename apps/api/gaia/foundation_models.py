"""Phase 1 inventory. SensorReading remains the single telemetry store."""

from sqlalchemy import Boolean, Date, Float, ForeignKey, JSON, String, Text, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from .config import Base, utcnow
from .models import Identity, TerritoryChild
from .utc_types import UTCDateTime


class Zone(TerritoryChild, Base):
    __tablename__ = "zones"
    __table_args__ = (
        Index(
            "uq_zones_default",
            "territory_id",
            unique=True,
            sqlite_where=text("is_default = true"),
            postgresql_where=text("is_default = true"),
        ),
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class PlantProfile(Identity, Base):
    __tablename__ = "plant_profiles"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    common_name: Mapped[str] = mapped_column(String(100))
    scientific_name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    soil_moisture_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_moisture_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    ph_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    ph_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_requirements: Mapped[str] = mapped_column(Text, default="")
    irrigation_requirements: Mapped[str] = mapped_column(Text, default="")
    nutrient_requirements: Mapped[str] = mapped_column(Text, default="")
    common_diseases: Mapped[list] = mapped_column(JSON, default=list)
    stage_requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class Device(TerritoryChild, Base):
    __tablename__ = "devices"
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    device_type: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    legacy_sensor_id: Mapped[str | None] = mapped_column(ForeignKey("sensors.id"), unique=True, nullable=True)
    legacy_irrigation_id: Mapped[str | None] = mapped_column(
        ForeignKey("irrigation_zones.id"), unique=True, nullable=True
    )
    actuator_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_seen: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class SensorChannel(Identity, Base):
    __tablename__ = "sensor_channels"
    __table_args__ = (UniqueConstraint("device_id", "sensor_type", name="uq_device_channel"),)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    sensor_type: Mapped[str] = mapped_column(String(40))
    unit: Mapped[str] = mapped_column(String(20))
    calibration: Mapped[dict] = mapped_column(JSON, default=dict)


class PlantInstance(TerritoryChild, Base):
    __tablename__ = "plant_instances"
    profile_id: Mapped[str] = mapped_column(ForeignKey("plant_profiles.id"), index=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    planted_on: Mapped[object | None] = mapped_column(Date, nullable=True)
    growth_stage: Mapped[str] = mapped_column(String(20), default="vegetative")
    health_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    camera_device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class PlantSensorLink(Base):
    __tablename__ = "plant_sensor_links"
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plant_instances.id", ondelete="CASCADE"), primary_key=True
    )
    channel_id: Mapped[str] = mapped_column(ForeignKey("sensor_channels.id"), primary_key=True)
