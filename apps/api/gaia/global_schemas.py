from datetime import datetime
from typing import Literal
from pydantic import ConfigDict, Field, model_validator
from .schemas import Schema


class Input(Schema):
    model_config = ConfigDict(
        extra="forbid", from_attributes=True, str_strip_whitespace=True, allow_inf_nan=False
    )


class Area(Input):
    name: str = Field(default="Выбранная территория", min_length=1, max_length=120)
    latitude: float = Field(ge=-85, le=85)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=25, ge=1, le=500)


class AnalysisIn(Input):
    area: Area
    source: Literal["demo", "copernicus", "nasa", "earth_engine"] = "demo"
    scenario: Literal["degraded", "recovering", "balanced"] = "degraded"


class Weights(Input):
    vegetation: float = Field(default=25, ge=0, le=100)
    moisture: float = Field(default=25, ge=0, le=100)
    temperature: float = Field(default=15, ge=0, le=100)
    change: float = Field(default=20, ge=0, le=100)
    precipitation: float = Field(default=15, ge=0, le=100)

    @model_validator(mode="after")
    def total(self):
        if abs(sum(self.model_dump().values()) - 100) > 0.001:
            raise ValueError("Сумма весов должна быть равна 100%")
        return self


class WeightsUpdate(Input):
    weights: Weights
    expected_revision: int = Field(ge=1)


class RoleUpdate(Input):
    role: Literal["user", "admin"]


class MarkerIn(Input):
    title: str = Field(min_length=1, max_length=120)
    category: Literal["vegetation", "water", "erosion", "pressure", "other"] = "other"
    note: str = Field(default="", max_length=3000)
    latitude: float = Field(ge=-85, le=85)
    longitude: float = Field(ge=-180, le=180)


class MarkerOut(MarkerIn):
    id: str
    creator_id: str
    created_at: datetime


class AnalysisSummary(Schema):
    id: str
    name: str
    latitude: float
    longitude: float
    source: str
    created_at: datetime
