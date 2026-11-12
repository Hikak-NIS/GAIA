"""Numerical model products with timestamps and provenance; never substitute synthetic readings."""

from ..config import utcnow, settings
from .remote import cached, fetch, gather


def meteo_url(service):
    host = {"weather": "api", "air": "air-quality-api", "marine": "marine-api"}[service]
    path = {"weather": "forecast", "air": "air-quality", "marine": "marine"}[service]
    if settings.openmeteo_api_key:
        host = {
            "weather": "customer-api",
            "air": "customer-air-quality-api",
            "marine": "customer-marine-api",
        }[service]
    return f"https://{host}.open-meteo.com/v1/{path}"


VARIABLES = {
    "weather": [
        ("temperature_2m", "Температура воздуха", "Температура на высоте 2 м; не спутниковая LST."),
        ("precipitation", "Осадки за час", "Расчёт погодной модели для ближайшей ячейки."),
        (
            "soil_moisture_0_to_1cm",
            "Влажность верхнего слоя почвы",
            "Объёмная доля воды в слое 0–1 см; не показание полевого датчика.",
        ),
        ("soil_temperature_0cm", "Температура почвы", "Расчётная температура поверхности почвы."),
        (
            "et0_fao_evapotranspiration",
            "Эвапотранспирация ET₀",
            "Эталонная испаряемость FAO; требует поправки на культуру для расчёта полива.",
        ),
    ],
    "air": [
        ("pm2_5", "PM₂.₅", "Модель CAMS; не локальная станция мониторинга."),
        ("pm10", "PM₁₀", "Модельная концентрация взвешенных частиц."),
        ("nitrogen_dioxide", "Диоксид азота", "Приземная концентрация по модели CAMS."),
        ("ozone", "Озон", "Приземный озон по модели CAMS."),
    ],
    "marine": [
        (
            "sea_surface_temperature",
            "Температура поверхности моря",
            "Морской модельный продукт. Внутренние водоёмы могут не покрываться.",
        ),
        ("wave_height", "Высота волн", "Значительная высота волн; не максимальная отдельная волна."),
        ("ocean_current_velocity", "Скорость течения", "Расчёт морской модели для выбранной ячейки."),
    ],
}


def environment(latitude, longitude, service="weather"):
    def load():
        variables = VARIABLES[service]
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(x[0] for x in variables),
            "past_days": 7,
            "forecast_days": 1,
            "timezone": "GMT",
        }
        if service == "marine":
            params["cell_selection"] = "sea"
        if settings.openmeteo_api_key:
            params["apikey"] = settings.openmeteo_api_key
        data = fetch(meteo_url(service), params=params)
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        now = utcnow().isoformat()[:16]
        metrics = []
        for key, label, explanation in variables:
            values = hourly.get(key, [])
            series = [
                {"date": t + "Z", "value": v}
                for t, v in zip(times, values, strict=False)
                if t <= now and v is not None
            ]
            latest = series[-1] if series else {}
            metrics.append(
                {
                    "id": key,
                    "label": label,
                    "value": latest.get("value"),
                    "observed_at": latest.get("date"),
                    "unit": data.get("hourly_units", {}).get(key, ""),
                    "kind": "model",
                    "source": "Open-Meteo" + (" / CAMS" if service == "air" else ""),
                    "description": explanation,
                    "history": series[::3] + (series[-1:] if len(series) % 3 != 1 else []),
                }
            )
        return {
            "metrics": metrics,
            "grid": {"latitude": data.get("latitude"), "longitude": data.get("longitude")},
            "fetched_at": utcnow().isoformat(),
            "source_url": {
                "weather": "https://open-meteo.com/en/docs",
                "air": "https://open-meteo.com/en/docs/air-quality-api",
                "marine": "https://open-meteo.com/en/docs/marine-weather-api",
            }[service],
        }

    return cached((service, round(latitude, 4), round(longitude, 4)), load, 1800)


def local_environment(latitude, longitude, ocean=False):
    names = ("marine", "air") if ocean else ("weather", "air")
    return gather({key: lambda key=key: environment(latitude, longitude, key) for key in names})
