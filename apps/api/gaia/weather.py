from datetime import timedelta
import httpx
from sqlalchemy import select
from . import models as m
from .config import aware, utcnow

# Failure caching prevents a dashboard poll from hammering an unavailable provider.
failures: dict[str, object] = {}


def weather(db, territory):
    last = db.scalar(
        select(m.WeatherSnapshot)
        .where(m.WeatherSnapshot.territory_id == territory.id)
        .order_by(m.WeatherSnapshot.fetched_at.desc())
    )
    if last and utcnow() - aware(last.fetched_at) < timedelta(minutes=20):
        return {"status": "available", "fetched_at": last.fetched_at, "data": last.data}
    retry_at = failures.get(territory.id)
    if not retry_at or utcnow() >= retry_at:
        try:
            fields = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
            with httpx.Client(timeout=8) as client:
                response = client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": territory.latitude,
                        "longitude": territory.longitude,
                        "current": fields,
                        "hourly": fields
                        + ",precipitation_probability,shortwave_radiation,et0_fao_evapotranspiration",
                        "forecast_days": 2,
                        "timezone": "UTC",
                    },
                )
                response.raise_for_status()
                raw = response.json()
            hourly = raw["hourly"]
            now = utcnow().strftime("%Y-%m-%dT%H:00")
            indices = [i for i, t in enumerate(hourly["time"]) if t >= now][:6]
            data = {
                "current": raw["current"],
                "hourly": hourly,
                "next_6h_probability": max(
                    [hourly["precipitation_probability"][i] or 0 for i in indices], default=100
                ),
                "next_6h_precipitation_mm": sum(hourly["precipitation"][i] or 0 for i in indices),
                "provider": "Open-Meteo",
                "forecast_timezone": "UTC",
            }
            last = m.WeatherSnapshot(territory_id=territory.id, data=data)
            db.add(last)
            db.commit()
            failures.pop(territory.id, None)
            return {"status": "available", "fetched_at": last.fetched_at, "data": data}
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
            failures[territory.id] = utcnow() + timedelta(minutes=2)
    return {
        "status": "stale" if last else "unavailable",
        "fetched_at": last.fetched_at if last else None,
        "data": last.data if last else None,
        "error": "Погодный сервис недоступен. Повторный запрос через 2 минуты.",
    }
