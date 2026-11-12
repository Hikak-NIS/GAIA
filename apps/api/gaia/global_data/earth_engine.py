from .base import PlannedProvider


class EarthEngineProvider(PlannedProvider):
    key = "earth_engine"
    name = "Google Earth Engine"
    url = "https://developers.google.com/earth-engine/guides/access"
    requirements = "Зарегистрированный Cloud project, включённый API, роли и авторизация. Для некоммерческого доступа требуется подтверждение; коммерческий доступ использует платный план."
    products = ("Масштабная геообработка", "Исторические композиты", "Сравнение территорий")
