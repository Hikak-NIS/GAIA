"""Public Earth observation catalogues and time-aware satellite layers."""

from datetime import timedelta
import math
import xml.etree.ElementTree as ET
from ..config import utcnow, settings
from .remote import cached, fetch

GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
LAYERS = {
    "MODIS_Terra_CorrectedReflectance_TrueColor": ("Земля · естественные цвета", "imagery"),
    "MODIS_Aqua_L2_Chlorophyll_A": ("Океан · хлорофилл-а", "ocean"),
    "GHRSST_L4_MUR_Sea_Surface_Temperature": ("Океан · температура поверхности", "ocean"),
    "GHRSST_L4_MUR_Sea_Surface_Temperature_Anomalies": ("Океан · температурная аномалия", "ocean"),
    "MODIS_Terra_L3_NDVI_Monthly": ("Растительность · NDVI", "vegetation"),
    "MODIS_Terra_Aerosol_Optical_Depth_3km": ("Атмосфера · оптическая толщина аэрозоля", "atmosphere"),
    "OMI_Aura_L3_NO2_Tropospheric_Column": ("Атмосфера · NO₂", "atmosphere"),
    "MODIS_Terra_Thermal_Anomalies_All": ("Тепловые аномалии и пожары", "fires"),
    "VIIRS_SNPP_Thermal_Anomalies_375m_All": ("Пожары · VIIRS", "fires"),
    "AMSRU2_Sea_Ice_Concentration_12km": ("Полярные моря · концентрация льда", "ice"),
    "MODIS_Terra_L3_NDSI_Snow_Cover_Daily": ("Снег и ледники · снежный покров", "ice"),
}


def layers():
    def load():
        root = ET.fromstring(fetch(GIBS + "/1.0.0/WMTSCapabilities.xml", as_text=True))
        ns = {
            "w": "http://www.opengis.net/wmts/1.0",
            "o": "http://www.opengis.net/ows/1.1",
            "x": "http://www.w3.org/1999/xlink",
        }
        result = []
        for row in root.findall(".//w:Contents/w:Layer", ns):
            key = row.findtext("o:Identifier", namespaces=ns)
            if key not in LAYERS:
                continue
            matrix = row.findtext("w:TileMatrixSetLink/w:TileMatrixSet", namespaces=ns)
            fmt = row.findtext("w:Format", namespaces=ns)
            dimension = row.find("w:Dimension", ns)
            default = dimension.findtext("w:Default", namespaces=ns) if dimension is not None else "default"
            times = [n.text for n in dimension.findall("w:Value", ns)] if dimension is not None else []
            legend = row.find("w:Style/w:LegendURL", ns)
            result.append(
                {
                    "id": key,
                    "name": LAYERS[key][0],
                    "category": LAYERS[key][1],
                    "matrix": matrix,
                    "max_zoom": int(matrix.split("Level")[-1]),
                    "extension": "jpg" if fmt == "image/jpeg" else "png",
                    "default_date": default,
                    "time_ranges": times,
                    "legend": legend.get("{http://www.w3.org/1999/xlink}href")
                    if legend is not None
                    else None,
                    "source": "NASA GIBS / Earthdata",
                    "source_url": "https://worldview.earthdata.nasa.gov/",
                }
            )
        return {
            "items": result,
            "fetched_at": utcnow().isoformat(),
            "projection": "EPSG:3857",
            "polar_limit": 85.05,
        }

    return cached("gibs-layers", load, 21600)


def bounds(area):
    dy = area.radius_km / 111.32
    dx = dy / max(0.09, math.cos(math.radians(area.latitude)))
    return [
        max(-180, area.longitude - dx),
        max(-85, area.latitude - dy),
        min(180, area.longitude + dx),
        min(85, area.latitude + dy),
    ]


def scenes(area, start, end):
    box = bounds(area)

    def load():
        data = fetch(
            "https://stac.dataspace.copernicus.eu/v1/search",
            params={
                "collections": "sentinel-2-l2a",
                "bbox": ",".join(map(str, box)),
                "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
                "limit": 12,
                "sortby": "-datetime",
            },
        )
        result = []
        for item in data.get("features", []):
            props = item.get("properties", {})
            preview = next(
                (
                    v["href"]
                    for v in item.get("assets", {}).values()
                    if ("thumbnail" in v.get("roles", []) or "overview" in v.get("roles", []))
                    and v.get("href", "").startswith("https://")
                ),
                None,
            )
            result.append(
                {
                    "id": item["id"],
                    "datetime": props.get("datetime") or props.get("start_datetime"),
                    "cloud_cover": props.get("eo:cloud_cover"),
                    "geometry": item.get("geometry"),
                    "preview": preview,
                    "url": next((x["href"] for x in item["links"] if x["rel"] == "self"), None),
                }
            )
        return {
            "items": result,
            "source": "Copernicus Data Space · Sentinel-2 L2A",
            "fetched_at": utcnow().isoformat(),
            "note": "Список сцен пересекающих область, до 12 результатов. Облачность указана для всей сцены.",
        }

    return cached(("scenes", tuple(box), str(start), str(end)), load, 1800)


def events():
    def load():
        data = fetch(
            "https://eonet.gsfc.nasa.gov/api/v3/events", params={"status": "open", "days": 30, "limit": 500}
        )
        items = []
        for event in data.get("events", []):
            points = [g for g in event.get("geometry", []) if g.get("type") == "Point"]
            if not points:
                continue
            point = sorted(points, key=lambda g: g["date"])[-1]
            items.append(
                {
                    "id": event["id"],
                    "name": event["title"],
                    "categories": event["categories"],
                    "longitude": point["coordinates"][0],
                    "latitude": point["coordinates"][1],
                    "date": point["date"],
                    "sources": event.get("sources", []),
                }
            )
        return {
            "items": items,
            "fetched_at": utcnow().isoformat(),
            "source": "NASA EONET",
            "note": "Открытые события за 30 дней, до 500. Это каталог зарегистрированных событий, а не все пожары планеты.",
        }

    return cached("eonet", load, 900)


def nasa_catalog(area, start, end):
    headers = {"Authorization": "Bearer " + settings.earthdata_token} if settings.earthdata_token else None
    data = fetch(
        "https://cmr.earthdata.nasa.gov/search/granules.json",
        params={
            "short_name": "MOD09GA",
            "version": "061",
            "page_size": 8,
            "bounding_box": ",".join(map(str, bounds(area))),
            "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
            "sort_key": "-start_date",
        },
        headers=headers,
    )
    return {
        "items": [
            {
                "id": x["id"],
                "name": x.get("title"),
                "date": x.get("time_start"),
                "links": [
                    {"href": link["href"], "title": link.get("title", "Данные NASA")}
                    for link in x.get("links", [])
                    if link.get("href", "").startswith("https://")
                ][:4],
            }
            for x in data.get("feed", {}).get("entry", [])
        ],
        "source": "NASA CMR · MOD09GA.061",
    }


def recent_dates(days=30):
    end = utcnow().date() - timedelta(days=1)
    return end - timedelta(days=days), end
