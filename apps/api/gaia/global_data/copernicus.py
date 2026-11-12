from .base import PlannedProvider


class CopernicusProvider(PlannedProvider):
    key = "copernicus"
    name = "Copernicus · Sentinel-2"
    url = "https://documentation.dataspace.copernicus.eu/APIs/STAC.html"
    catalog_url = "https://stac.dataspace.copernicus.eu/v1"
    requirements = "STAC для поиска сцен; учётная запись и авторизация для нужного сервиса загрузки/обработки. Учитывать квоты, облачность и качество пикселей."
    products = ("Sentinel-2 L2A", "NDVI по B08/B04", "Изменение растительного покрова")
