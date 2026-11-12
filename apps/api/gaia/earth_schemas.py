from datetime import date, timedelta
from typing import Literal
from pydantic import Field, model_validator
from .global_schemas import Input, Area
from .config import utcnow


class EarthAnalysisIn(Input):
    area: Area
    start: date = Field(default_factory=lambda: utcnow().date() - timedelta(days=31))
    end: date = Field(default_factory=lambda: utcnow().date() - timedelta(days=1))
    ocean: bool = False
    satellite: bool = True
    earth_engine: bool = False

    @model_validator(mode="after")
    def valid_dates(self):
        if (
            not date(2000, 1, 1) <= self.start <= self.end <= utcnow().date()
            or (self.end - self.start).days > 366
        ):
            raise ValueError("Выберите период до 366 дней между 2000 годом и сегодня")
        return self


class ChatTurn(Input):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AssistantIn(Input):
    question: str = Field(min_length=1, max_length=4000)
    analysis_id: str | None = Field(default=None, max_length=36)
    territory_id: str | None = Field(default=None, max_length=36)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)


class SpeechIn(Input):
    text: str = Field(min_length=1, max_length=4000)
