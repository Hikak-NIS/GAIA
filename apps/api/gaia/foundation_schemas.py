from datetime import date, datetime
from typing import Literal
from pydantic import ConfigDict, Field, model_validator
from .schemas import Schema

Source = Literal["REAL", "SIMULATED"]
Stage = Literal["seedling", "vegetative", "flowering", "fruiting", "mature"]
DeviceType = Literal["SENSOR", "ACTUATOR", "CAMERA", "CONTROLLER"]


class Input(Schema):
    model_config = ConfigDict(
        from_attributes=True, extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )


class ZoneIn(Input):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)


class ZoneOut(ZoneIn):
    id: str
    territory_id: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class Requirements(Input):
    soil_moisture_min: float | None = Field(default=None, ge=0, le=100)
    soil_moisture_max: float | None = Field(default=None, ge=0, le=100)
    temperature_min: float | None = Field(default=None, ge=-60, le=70)
    temperature_max: float | None = Field(default=None, ge=-60, le=70)
    humidity_min: float | None = Field(default=None, ge=0, le=100)
    humidity_max: float | None = Field(default=None, ge=0, le=100)
    ph_min: float | None = Field(default=None, ge=0, le=14)
    ph_max: float | None = Field(default=None, ge=0, le=14)
    light_requirements: str = Field(default="", max_length=3000)
    irrigation_requirements: str = Field(default="", max_length=3000)
    nutrient_requirements: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def valid_ranges(self):
        for field in ("soil_moisture", "temperature", "humidity", "ph"):
            low, high = getattr(self, field + "_min"), getattr(self, field + "_max")
            if (low is None) != (high is None):
                raise ValueError(f"{field}: заполните обе границы диапазона или оставьте обе пустыми")
            if low is not None and low > high:
                raise ValueError(f"{field}: минимум не может превышать максимум")
        return self


class ProfileIn(Requirements):
    common_name: str = Field(min_length=1, max_length=100)
    scientific_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    common_diseases: list[str] = Field(default_factory=list, max_length=50)
    stage_requirements: dict[Stage, Requirements] = Field(default_factory=dict)

    @model_validator(mode="after")
    def bounded_diseases(self):
        if any(not name.strip() or len(name) > 200 for name in self.common_diseases):
            raise ValueError("Название заболевания должно содержать от 1 до 200 символов")
        return self


class ProfileOut(ProfileIn):
    id: str
    created_at: datetime
    updated_at: datetime


class DeviceIn(Input):
    name: str = Field(min_length=1, max_length=100)
    zone_id: str
    device_type: DeviceType = "SENSOR"
    source: Source = "REAL"
    actuator_type: Literal["PUMP", "VALVE", "FAN", "LIGHT", "DOSER"] | None = None

    @model_validator(mode="after")
    def actuator_metadata(self):
        if (self.device_type == "ACTUATOR") != (self.actuator_type is not None):
            raise ValueError("Укажите тип привода только для ACTUATOR")
        return self


class DeviceUpdate(Input):
    name: str = Field(min_length=1, max_length=100)
    zone_id: str
    active: bool = True


class Calibration(Input):
    scale: float = Field(default=1, gt=0, le=1000)
    offset: float = Field(default=0, ge=-100000, le=100000)
    notes: str = Field(default="", max_length=1000)


class ChannelOut(Schema):
    id: str
    device_id: str
    sensor_type: str
    unit: str
    calibration: dict
    source: Source
    current_value: float | None
    timestamp: datetime | None
    received_at: datetime | None
    quality: str
    availability: Literal["CURRENT", "STALE", "DISABLED", "MISSING", "HISTORICAL"]


class DeviceOut(Schema):
    id: str
    territory_id: str
    zone_id: str
    name: str
    device_type: DeviceType
    source: Source
    active: bool
    status: Literal["ONLINE", "OFFLINE", "WARNING", "ERROR", "SIMULATED"]
    last_seen: datetime | None
    created_at: datetime
    updated_at: datetime
    sensor_id: str | None
    channels: list[ChannelOut]
    actuator_type: str | None
    actuator_state: str | None
    safety_status: str | None
    last_action: datetime | None


class PlantIn(Input):
    name: str = Field(min_length=1, max_length=100)
    profile_id: str
    zone_id: str
    planted_on: date | None = None
    growth_stage: Stage = "vegetative"
    camera_device_id: str | None = None
    sensor_channel_ids: list[str] = Field(default_factory=list, max_length=100)


class PlantOut(PlantIn):
    id: str
    territory_id: str
    health_status: Literal["UNKNOWN"]
    created_at: datetime
    updated_at: datetime


class CredentialOut(Schema):
    device_id: str
    sensor_id: str
    api_key: str
    explanation: str
