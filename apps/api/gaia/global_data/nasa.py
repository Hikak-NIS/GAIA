from .base import PlannedProvider


class NasaProvider(PlannedProvider):
    key = "nasa"
    name = "NASA Earthdata"
    url = "https://www.earthdata.nasa.gov/"
    catalog_url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    requirements = "CMR для поиска продуктов; Earthdata Login для защищённых загрузок. Проверять QA, разрешение и временную агрегацию каждого продукта. GIBS — только визуальная подложка."
    products = ("MODIS LST", "GPM осадки", "SMAP влажность почвы")
