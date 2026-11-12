"""Shared administrative workspace; access is enforced for every request."""

from sqlalchemy import ForeignKey, JSON, String, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .config import Base, utcnow
from .models import Identity
from .utc_types import UTCDateTime


class GlobalAnalysis(Identity, Base):
    __tablename__ = "global_analyses"
    creator_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), default="demo")
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)


class GlobalMarker(Identity, Base):
    __tablename__ = "global_markers"
    creator_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)


class GlobalSettings(Base):
    __tablename__ = "global_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    weights: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class AdminAudit(Identity, Base):
    __tablename__ = "admin_audit"
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    target_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), default=utcnow)
