from ..config import utcnow
from . import copernicus_live, gee_live, earth_sources
from .environment import environment
from .remote import gather


def analyze(body):
    area = body.area
    tasks = {
        "weather": lambda: environment(area.latitude, area.longitude, "weather"),
        "air": lambda: environment(area.latitude, area.longitude, "air"),
        "sentinel_catalog": lambda: earth_sources.scenes(area, body.start, body.end),
        "nasa_catalog": lambda: earth_sources.nasa_catalog(area, body.start, body.end),
    }
    if body.ocean:
        tasks["marine"] = lambda: environment(area.latitude, area.longitude, "marine")
    if body.satellite and copernicus_live.configured():
        tasks["sentinel_statistics"] = lambda: copernicus_live.stats(area, body.start, body.end, body.ocean)
    if body.earth_engine and gee_live.configured():
        tasks["earth_engine"] = lambda: gee_live.regional(area, body.ocean)
    sources = gather(tasks)
    if body.satellite and not copernicus_live.configured():
        sources["sentinel_statistics"] = {
            "status": "needs_configuration",
            "message": "Для расчёта индексов заполните COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET. Каталог сцен доступен без ключа.",
        }
    if body.earth_engine and not gee_live.configured():
        sources["earth_engine"] = {
            "status": "needs_configuration",
            "message": "Настройте проект и сервисный аккаунт Google Earth Engine.",
        }
    metrics = [m for source in sources.values() for m in source.get("data", {}).get("metrics", [])]
    recommendations = [
        {
            "title": "План полевого обследования",
            "detail": "Сопоставьте спутниковые и модельные данные с измерениями на месте. Укажите биом, сезон, тип почвы и известные источники нагрузки.",
            "priority": "Базовый",
            "basis": "Различия масштаба и метода наблюдения",
        }
    ]
    values = {m["id"]: m["value"] for m in metrics if m.get("value") is not None}
    if values.get("soil_moisture_0_to_1cm", 1) < 0.1:
        recommendations.append(
            {
                "title": "Проверить дефицит влаги",
                "detail": "Модель показывает низкую объёмную влажность верхнего слоя. Проверьте влажность в корневой зоне датчиком и водный баланс; назначать полив только по этой ячейке нельзя.",
                "priority": "Проверить",
                "basis": "Модельная влажность 0–1 см < 0,1 м³/м³",
            }
        )
    if values.get("pm2_5", 0) >= 25:
        recommendations.append(
            {
                "title": "Проверить эпизод загрязнения воздуха",
                "detail": "Сравните CAMS с ближайшими станциями и локальными источниками. Этот рабочий порог не является оценкой соблюдения санитарных нормативов.",
                "priority": "Проверить",
                "basis": "CAMS PM₂.₅ ≥ 25 мкг/м³ в выбранный час",
            }
        )
    if values.get("tree_cover_loss", 0) and values["tree_cover_loss"] > 0:
        recommendations.append(
            {
                "title": "Установить причины потери древесного покрова",
                "detail": "Сопоставьте год потери с пожарами, хозяйственной деятельностью и полевыми материалами. Причина изменения этим продуктом не определяется.",
                "priority": "Обследовать",
                "basis": "UMD Hansen: ненулевая площадь потерь",
            }
        )
    if body.ocean:
        recommendations.append(
            {
                "title": "Отбор проб воды",
                "detail": "Для проверки мутности, хлорофилла-а и микропластика нужны синхронные пробы с координатами, глубиной, методом анализа и контролем качества. Спектральные индексы помогают выбирать точки отбора.",
                "priority": "Полевые данные",
                "basis": "Ограничения дистанционных наблюдений",
            }
        )
    return {
        "area": area.model_dump(),
        "data_kind": "observations",
        "ocean": body.ocean,
        "period": {"start": str(body.start), "end": str(body.end)},
        "generated_at": utcnow().isoformat(),
        "metrics": metrics,
        "sources": sources,
        "recommendations": recommendations,
        "assessment": {
            "score": None,
            "status": "requires_validation",
            "explanation": "Единый балл состояния не рассчитывается без проверенной модели для данного биома и достаточных измерений. Отсутствие данных не означает хорошее состояние.",
        },
        "coverage_note": "Метео-, воздушные и морские модели: последние 7 дней, ближайшая ячейка к центру. Спутниковая обработка: выбранный период и круг. Глобальные выводы по одной точке не делаются.",
    }
