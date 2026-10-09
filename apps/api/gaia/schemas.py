import math
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class Register(Schema):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class Login(Schema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(Schema):
    id: str
    name: str
    email: str


class TerritoryIn(Schema):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    polygon: dict | None = None
    area: float = Field(default=100, gt=0, le=1_000_000)
    timezone: str = "Asia/Almaty"

    @field_validator("timezone")
    @classmethod
    def timezone_exists(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Неизвестная временная зона") from exc
        return value

    @field_validator("polygon")
    @classmethod
    def valid_polygon(cls, value):
        if value is None:
            return None
        if value.get("type") != "Polygon":
            raise ValueError("Ожидается GeoJSON Polygon")
        rings = value.get("coordinates")
        if not isinstance(rings, list) or not 1 <= len(rings) <= 10:
            raise ValueError("Некорректный полигон")
        for ring in rings:
            if not isinstance(ring, list) or not 4 <= len(ring) <= 500:
                raise ValueError("Некорректное кольцо полигона")
            if ring[0] != ring[-1]:
                raise ValueError("Кольцо должно быть замкнуто")
            for coord in ring:
                if not isinstance(coord, list) or len(coord) != 2:
                    raise ValueError("Некорректные координаты")
                longitude, latitude = coord
                values = (longitude, latitude)
                if any(isinstance(number, bool) or not isinstance(number, (int, float)) for number in values):
                    raise ValueError("Координаты должны быть числами")
                if not all(math.isfinite(float(number)) for number in values):
                    raise ValueError("Координаты должны быть конечными числами")
                if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                    raise ValueError("Некорректные координаты")
        return value


class TerritoryOut(TerritoryIn):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class Telemetry(Schema):
    sensor_id: str
    timestamp: datetime
    source: Literal["simulated", "device", "manual", "weather", "satellite"]
    air_temperature_c: float | None = Field(default=None, ge=-60, le=70)
    air_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    soil_moisture_pct: float | None = Field(default=None, ge=0, le=100)
    light_lux: float | None = Field(default=None, ge=0, le=200000)
    pressure_hpa: float | None = Field(default=None, ge=800, le=1200)
    battery_pct: float | None = Field(default=None, ge=0, le=100)
    quality: Literal["valid", "stale", "invalid"] = "valid"
    raw_metadata: dict[str, float | str | bool] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def utc_required(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Timestamp должен содержать временную зону")
        return value

    @field_validator("raw_metadata")
    @classmethod
    def safe_metadata(cls, value):
        if set(value) - {"scenario", "tick", "firmware", "model"}:
            raise ValueError("Разрешены только scenario, tick, firmware, model")
        if len(str(value)) > 1000:
            raise ValueError("Слишком много метаданных")
        return value


class ReadingOut(Telemetry):
    id: str
    territory_id: str
    received_at: datetime


class SimulationAction(Schema):
    action: Literal["start", "pause", "resume", "stop", "reset", "tick", "configure"]
    scenario: Literal["normal", "drought", "heatwave", "rain", "frost", "sensor_failure"] | None = None
    speed: Literal[1, 10, 60] | None = None
    seed: int | None = Field(default=None, ge=0, le=2147483647)


class RuleIn(Schema):
    mode: Literal["off", "manual", "automatic"] = "off"
    trigger_pct: float = Field(default=30, ge=1, le=90)
    target_pct: float = Field(default=45, ge=2, le=95)
    max_duration_s: int = Field(default=1200, ge=10, le=7200)
    cooldown_s: int = Field(default=1800, ge=0, le=86400)
    daily_limit_l: float = Field(default=30, gt=0, le=500)
    min_reservoir_l: float = Field(default=5, ge=1, le=100)
    block_rain: bool = False
    rain_threshold_pct: float = Field(default=60, ge=0, le=100)

    @model_validator(mode="after")
    def thresholds(self):
        if self.target_pct <= self.trigger_pct:
            raise ValueError("Целевая влажность должна быть выше порога")
        return self


class PumpAction(Schema):
    action: Literal["start", "stop", "emergency", "clear_emergency"]
    duration_s: int = Field(default=300, ge=10, le=7200)


class ObservationIn(Schema):
    category: Literal["vegetation", "soil", "water", "litter", "pest", "weather", "other"]
    severity: Literal["info", "warning", "critical"]
    text: str = Field(min_length=1, max_length=5000)
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    _timestamp = field_validator("timestamp")(classmethod(lambda cls, v: Telemetry.utc_required(v)))


class ObservationOut(ObservationIn):
    id: str
    territory_id: str
    source: str
    photo_path: str | None


class RuleOut(RuleIn):
    id: str
    territory_id: str


class SimulationOut(Schema):
    id: str
    territory_id: str
    status: str
    scenario: str
    seed: int
    speed: int
    tick_index: int
    clock: datetime
    soil: float
    reservoir_l: float
    total_water_l: float


class ZoneOut(Schema):
    id: str
    territory_id: str
    name: str
    pump_on: bool
    emergency: bool
    started_at: datetime | None
    stopped_at: datetime | None
    deadline: datetime | None
    run_water_l: float
    daily_water_l: float
    water_day: str


class EventOut(Schema):
    id: str
    territory_id: str
    timestamp: datetime
    mode: str
    action: str
    reason: str
    trigger_value: float | None
    target_value: float
    duration_s: float
    estimated_water_l: float
    actor: str


class AlertOut(Schema):
    id: str
    territory_id: str
    code: str
    severity: str
    status: str
    title: str
    explanation: str
    recommendation: str
    created_at: datetime
    resolved_at: datetime | None


class ReportOut(Schema):
    id: str
    territory_id: str
    period_start: datetime
    period_end: datetime
    created_at: datetime
    data: dict


class WeatherOut(Schema):
    source: str = "weather"
    status: Literal["available", "stale", "unavailable"]
    fetched_at: datetime | None = None
    data: dict | None = None
    error: str | None = None


class SatelliteOut(Schema):
    source: str = "satellite"
    provider: str = "NASA GIBS"
    resolution_m: int = 250
    date: str
    url: str
    explanation: str


class CredentialOut(Schema):
    sensor_id: str
    api_key: str
    explanation: str


class Message(Schema):
    message: str


class Dashboard(Schema):
    territory: TerritoryOut
    simulation: SimulationOut
    zone: ZoneOut
    rule: RuleOut
    reading: ReadingOut | None
    alerts: list[AlertOut]
    status: Literal["normal", "warning", "critical"]
    reasons: list[str]
