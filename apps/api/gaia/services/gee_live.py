"""Earth Engine regional summaries. Service credentials stay on the server."""

from threading import RLock
from fastapi import HTTPException
from ..config import settings, utcnow
from .remote import cached

_lock = RLock()
_initialized = False


def configured():
    return bool(settings.gee_project and settings.gee_service_account and settings.gee_key_file)


def client():
    global _initialized
    if not configured():
        raise HTTPException(503, "Заполните GEE_PROJECT, GEE_SERVICE_ACCOUNT и GEE_KEY_FILE в .env")
    import ee

    with _lock:
        if not _initialized:
            credentials = ee.ServiceAccountCredentials(settings.gee_service_account, settings.gee_key_file)
            ee.Initialize(credentials=credentials, project=settings.gee_project)
            ee.data.setDeadline(45000)
            _initialized = True
    return ee


def regional(area, ocean=False):
    if area.radius_km > 50:
        raise HTTPException(422, "Для численного анализа Earth Engine выберите радиус до 50 км")

    def load():
        ee = client()
        region = ee.Geometry.Point([area.longitude, area.latitude]).buffer(area.radius_km * 1000)
        pixel_area = ee.Image.pixelArea().divide(1_000_000)
        if ocean:
            # Deliberately fixed published release: never relabel 2021 as current water extent.
            collection = ee.ImageCollection("JRC/GSW1_4/YearlyHistory")
            bands = []
            for year in range(2012, 2022):
                image = ee.Image(collection.filter(ee.Filter.eq("year", year)).first()).select("waterClass")
                bands.append(pixel_area.updateMask(image.gte(2)).rename(f"water_{year}"))
            values = (
                ee.Image.cat(bands)
                .reduceRegion(ee.Reducer.sum(), region, 30, maxPixels=40_000_000, tileScale=4)
                .getInfo()
            )
            history = [
                {"date": f"{year}-12-31", "value": values.get(f"water_{year}")} for year in range(2012, 2022)
            ]
            metric = {
                "id": "water_area",
                "label": "Площадь сезонной и постоянной воды",
                "unit": "км²",
                "kind": "satellite",
                "value": history[-1]["value"],
                "observed_at": "2021-12-31",
                "source": "JRC Global Surface Water 1.4 / Earth Engine",
                "description": "Годовая история 2012–2021, 30 м. Архивный продукт, не площадь водоёма сегодня. Нет данных не означает нулевую площадь.",
                "history": history,
            }
        else:
            image = ee.Image("UMD/hansen/global_forest_change_2025_v1_13")
            tree_mask = image.select("treecover2000").gte(30)
            bands = [
                pixel_area.updateMask(image.select("lossyear").eq(year).And(tree_mask)).rename(
                    f"loss_{2000 + year}"
                )
                for year in range(1, 26)
            ]
            values = (
                ee.Image.cat(bands)
                .reduceRegion(ee.Reducer.sum(), region, 30, maxPixels=40_000_000, tileScale=4)
                .getInfo()
            )
            history = [
                {"date": f"{year}-12-31", "value": values.get(f"loss_{year}")} for year in range(2001, 2026)
            ]
            metric = {
                "id": "tree_cover_loss",
                "label": "Потеря древесного покрова за год",
                "unit": "км²",
                "kind": "satellite",
                "value": history[-1]["value"],
                "observed_at": "2025-12-31",
                "source": "UMD Hansen GFC 2025 v1.13 / Earth Engine",
                "description": "30 м; исходный древесный покров ≥30% в 2000 году. Потеря покрова не тождественна вырубке: причины включают пожары и другие нарушения.",
                "history": history,
            }
        return {"metrics": [metric], "fetched_at": utcnow().isoformat()}

    return cached(("gee", area.latitude, area.longitude, area.radius_km, ocean), load, 86400)


def forest_map():
    ee = client()
    image = ee.Image("UMD/hansen/global_forest_change_2025_v1_13").select("lossyear")
    result = image.updateMask(image.gt(0)).getMapId(
        {"min": 1, "max": 25, "palette": ["ffff00", "ff8800", "ff0000"]}
    )
    return {
        "url": result["tile_fetcher"].url_format,
        "name": "Потери древесного покрова 2001–2025",
        "source": "UMD Hansen / Google Earth Engine",
        "note": "Цвет обозначает год потери; это не карта только незаконной вырубки.",
    }
