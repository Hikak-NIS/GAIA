"""Authenticated Sentinel Hub processing; reflectance indices, not calibrated chemistry."""

import math
from threading import Lock
from time import monotonic
import httpx
from fastapi import HTTPException
from ..config import settings, utcnow
from .earth_sources import bounds
from .remote import cached

_token = None
_token_until = 0
_token_lock = Lock()


def configured():
    return bool(settings.copernicus_client_id and settings.copernicus_client_secret)


def token():
    global _token, _token_until
    if not configured():
        raise HTTPException(503, "Заполните COPERNICUS_CLIENT_ID и COPERNICUS_CLIENT_SECRET в .env")
    with _token_lock:
        if _token and monotonic() < _token_until:
            return _token
        response = httpx.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.copernicus_client_id,
                "client_secret": settings.copernicus_client_secret,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        _token, _token_until = data["access_token"], monotonic() + max(1, data["expires_in"] - 60)
        return _token


def geometry(area):
    coordinates = []
    for n in range(65):
        angle = 2 * math.pi * n / 64
        coordinates.append(
            [
                area.longitude
                + area.radius_km
                / 111.32
                / max(0.09, math.cos(math.radians(area.latitude)))
                * math.cos(angle),
                area.latitude + area.radius_km / 111.32 * math.sin(angle),
            ]
        )
    if any(not -180 <= x <= 180 or not -85 <= y <= 85 for x, y in coordinates):
        raise HTTPException(422, "Область пересекает границу карты. Уменьшите радиус или переместите центр.")
    coordinates[-1] = coordinates[0]
    return {"type": "Polygon", "coordinates": [coordinates]}


def input_data(area, start, end):
    if area.radius_km > 50:
        raise HTTPException(422, "Для обработки Sentinel-2 выберите радиус не больше 50 км")
    return {
        "bounds": {
            "geometry": geometry(area),
            "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
        },
        "data": [
            {
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {"from": str(start) + "T00:00:00Z", "to": str(end) + "T23:59:59Z"},
                    "maxCloudCoverage": 40,
                    "mosaickingOrder": "leastCC",
                },
            }
        ],
    }


def stats(area, start, end, ocean=False):
    def load():
        names = (
            [
                ("ndwi", "NDWI · водный индекс"),
                ("ndci", "NDCI · индикатор хлорофилла"),
                ("red_reflectance", "Красная отражательная способность"),
            ]
            if ocean
            else [
                ("ndvi", "NDVI · растительность"),
                ("ndmi", "NDMI · влага растительности"),
                ("nbr", "NBR · состояние покрова"),
            ]
        )
        formulas = (
            ["index(s.B03,s.B08)", "index(s.B05,s.B04)", "s.B04"]
            if ocean
            else ["index(s.B08,s.B04)", "index(s.B08,s.B11)", "index(s.B08,s.B12)"]
        )
        mask = " && s.SCL===6" if ocean else " && s.SCL!==6"
        script = '//VERSION=3\nfunction setup(){return {input:["B03","B04","B05","B08","B11","B12","SCL","dataMask"],output:[{id:"indices",bands:3,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}\n'
        script += (
            "function evaluatePixel(s){let valid=s.dataMask && ![0,1,3,8,9,10,11].includes(s.SCL)"
            + mask
            + ";return {indices:["
            + ",".join(formulas)
            + "],dataMask:[valid?1:0]};}"
        )
        body = {
            "input": input_data(area, start, end),
            "aggregation": {
                "timeRange": {"from": str(start) + "T00:00:00Z", "to": str(end) + "T23:59:59Z"},
                "aggregationInterval": {"of": "P10D", "lastIntervalBehavior": "SHORTEN"},
                "width": 256,
                "height": 256,
                "evalscript": script,
            },
        }
        response = httpx.post(
            "https://sh.dataspace.copernicus.eu/api/v1/statistics",
            json=body,
            headers={"Authorization": "Bearer " + token()},
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise ValueError("Sentinel Hub processing error")
        metrics = []
        for i, (key, label) in enumerate(names):
            history = []
            for interval in data.get("data", []):
                band = (
                    interval.get("outputs", {})
                    .get("indices", {})
                    .get("bands", {})
                    .get(f"B{i}", {})
                    .get("stats", {})
                )
                count = band.get("sampleCount", 0) - band.get("noDataCount", 0)
                value = band.get("mean")
                if count > 0 and isinstance(value, (float, int)) and math.isfinite(value):
                    history.append(
                        {
                            "date": interval["interval"]["from"],
                            "end": interval["interval"]["to"],
                            "value": value,
                            "valid_samples": count,
                            "valid_fraction": count / max(1, band.get("sampleCount", 1)),
                        }
                    )
            latest = history[-1] if history else {}
            description = (
                "Среднее по маске суши, облака и тени исключены SCL; сетка 256×256, интервалы 10 дней."
            )
            if ocean:
                description = "Только пиксели воды SCL=6 без облаков. Спектральный индикатор; не концентрация хлорофилла, NTU или взвеси. Нужна локальная калибровка по пробам."
            metrics.append(
                {
                    "id": key,
                    "label": label,
                    "value": latest.get("value"),
                    "unit": "отражение" if key == "red_reflectance" else "индекс",
                    "observed_at": latest.get("date"),
                    "kind": "satellite",
                    "source": "Copernicus Sentinel-2 L2A / Sentinel Hub",
                    "description": description,
                    "history": history,
                    "quality": latest.get("valid_fraction"),
                }
            )
        return {
            "metrics": metrics,
            "fetched_at": utcnow().isoformat(),
            "geometry": geometry(area),
            "sampling": "256 × 256",
            "period": {"start": str(start), "end": str(end)},
        }

    return cached(("s2-stats", tuple(bounds(area)), str(start), str(end), ocean), load, 3600)


def image(area, start, end):
    def load():
        body = {
            "input": input_data(area, start, end),
            "output": {
                "width": 512,
                "height": 512,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            "evalscript": '//VERSION=3\nfunction setup(){return {input:["B02","B03","B04","dataMask"],output:{bands:4}};} function evaluatePixel(s){return [2.5*s.B04,2.5*s.B03,2.5*s.B02,s.dataMask];}',
        }
        response = httpx.post(
            "https://sh.dataspace.copernicus.eu/api/v1/process",
            json=body,
            headers={"Authorization": "Bearer " + token()},
            timeout=45,
        )
        response.raise_for_status()
        return response.content

    return cached(("s2-image", tuple(bounds(area)), str(start), str(end)), load, 3600)
