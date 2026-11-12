"""GEHI v0.1: an explainable, explicitly non-validated demonstration model."""

import math
from ..global_schemas import Weights

MODEL_VERSION = "GEHI-concept-0.1"


def clamp(value):
    return max(0, min(100, value))


def health_level(score):
    if score <= 20:
        return "critical", "Критическое состояние"
    if score <= 40:
        return "severe", "Сильная деградация"
    if score <= 60:
        return "moderate", "Умеренная деградация"
    if score <= 80:
        return "satisfactory", "Удовлетворительное состояние"
    return "good", "Хорошее экологическое состояние"


def evaluate(observation, weights: Weights, revision: int):
    v = observation["values"]
    baseline = observation["demo_baselines"]
    # Explicit, editable weights; climate-dependent thresholds are demo assumptions only.
    factors = [
        (
            "vegetation",
            "Растительность",
            clamp(v["ndvi"] / 0.8 * 100),
            f"NDVI {v['ndvi']:.3f}; демонстрационный ориентир 0,8",
            "clamp(NDVI / 0.8 × 100)",
        ),
        (
            "moisture",
            "Влажность почвы",
            clamp(v["soil_moisture"] / 45 * 100),
            f"Влажность {v['soil_moisture']}%; демонстрационный ориентир 45%",
            "clamp(soil_moisture / 45 × 100)",
        ),
        (
            "temperature",
            "Температурная аномалия",
            clamp(100 - abs(v["temperature_anomaly"]) * 10),
            f"Отклонение LST {v['temperature_anomaly']:+.1f} °C от DEMO-базы 24 °C",
            "clamp(100 − abs(LST − 24) × 10)",
        ),
        (
            "change",
            "Динамика покрова",
            clamp(70 + 3 * v["vegetation_change"]),
            f"Изменение покрова {v['vegetation_change']:+.1f} п.п. за 12 DEMO-точек",
            "clamp(70 + change_pp × 3)",
        ),
        (
            "precipitation",
            "Обеспеченность осадками",
            clamp(v["precipitation"] / baseline["precipitation_mm_30d"] * 100),
            f"Осадки {v['precipitation']} мм / 30 дней; DEMO-база 60 мм",
            "clamp(rain_mm_30d / 60 × 100)",
        ),
    ]
    weight_values = weights.model_dump()
    contributions = [
        {
            "id": key,
            "name": name,
            "score": round(value, 2),
            "weight": weight_values[key],
            "contribution": round(value * weight_values[key] / 100, 2),
            "explanation": explanation,
            "formula": formula,
        }
        for key, name, value, explanation, formula in factors
    ]
    # Round once; the displayed integer maps unambiguously to the requested intervals.
    score = math.floor(sum(value * weight_values[key] / 100 for key, _, value, _, _ in factors) + 0.5)
    level, label = health_level(score)
    metrics = [
        (
            "ndvi",
            "NDVI",
            v["ndvi"],
            "индекс",
            -1,
            1,
            "Индекс растительности от −1 до 1. Здесь задан сценарной моделью, не рассчитан по снимку.",
        ),
        (
            "lst",
            "Температура поверхности",
            v["lst"],
            "°C",
            -20,
            65,
            "LST поверхности земли, не температура воздуха. DEMO-база аномалии: 24 °C.",
        ),
        (
            "precipitation",
            "Осадки за 30 дней",
            v["precipitation"],
            "мм",
            0,
            120,
            "Сумма DEMO-осадков за условное 30-дневное окно.",
        ),
        (
            "soil_moisture",
            "Влажность почвы",
            v["soil_moisture"],
            "% об.",
            0,
            60,
            "Демонстрационная объёмная влажность верхнего слоя; глубина и сенсор не определены.",
        ),
        (
            "vegetation_cover",
            "Растительный покров",
            v["vegetation_cover"],
            "% площади",
            0,
            100,
            "Условная доля площади с растительностью; не классификация спутникового снимка.",
        ),
        (
            "degradation",
            "Условная деградация",
            100 - score,
            "/ 100",
            0,
            100,
            "Производный показатель 100 − GEHI, не независимое измерение деградации.",
        ),
        (
            "vegetation_change",
            "Изменение покрова",
            v["vegetation_change"],
            "п.п. / 12 мес.",
            -30,
            30,
            "Разность последней и первой точки DEMO-истории; не процент относительного изменения.",
        ),
    ]
    return {
        "gehi": {
            "score": score,
            "level": level,
            "label": label,
            "factors": contributions,
            "model_version": MODEL_VERSION,
            "weights_revision": revision,
            "weights": weight_values,
            "notice": "Концептуальная модель на DEMO-данных. Индекс научно не валидирован; пороги требуют настройки под биом и сезон.",
        },
        "metrics": [
            {
                "id": key,
                "name": name,
                "value": value,
                "unit": unit,
                "min": low,
                "max": high,
                "explanation": description,
                "source": observation["source"],
                "provider": observation["provider"],
                "updated_at": observation["as_of"],
            }
            for key, name, value, unit, low, high, description in metrics
        ],
        "recommendations": recommendations(v),
        "history": observation["history"],
        "observation": observation,
    }


def recommendations(v):
    rows = []

    def add(key, priority, issue, action, effect, evidence):
        rows.append(
            {
                "id": key,
                "priority": priority,
                "problem": issue,
                "action": action,
                "expected_effect": effect,
                "evidence": evidence,
                "source": "DEMO rule-based",
            }
        )

    if v["ndvi"] < 0.4 or v["vegetation_cover"] < 40:
        add(
            "vegetation",
            "high",
            "Разреженный растительный покров в DEMO-сценарии",
            "Обследовать участок; подобрать местные виды и пилотные площадки восстановления.",
            "Возможное увеличение покрытия и устойчивости местных сообществ; эффект проверить мониторингом.",
            f"NDVI={v['ndvi']}; покров={v['vegetation_cover']}%",
        )
        add(
            "erosion",
            "high",
            "Оголение почвы может усиливать эрозию",
            "Проверить склон, почву и сток; испытать локальные противоэрозионные меры.",
            "Снижение потерь верхнего слоя почвы при подходящих местных условиях.",
            f"Покров={v['vegetation_cover']}%; DEMO-порог 40%",
        )
    if v["soil_moisture"] < 25 or v["precipitation"] < 30:
        add(
            "water",
            "high",
            "Недостаток влаги в DEMO-сценарии",
            "Оценить водный баланс и допустимые меры удержания влаги; не перенаправлять водотоки без обследования.",
            "Возможное улучшение доступности влаги и приживаемости растительности.",
            f"Влажность={v['soil_moisture']}%; осадки={v['precipitation']} мм/30 дней",
        )
    if abs(v["temperature_anomaly"]) > 4:
        add(
            "temperature",
            "medium",
            "Повышенная температурная нагрузка относительно DEMO-базы",
            "Сопоставить с локальной климатической нормой; исследовать восстановление затенения и покрова.",
            "Возможное смягчение микроклимата; не является обещанием снижения температуры.",
            f"Аномалия LST={v['temperature_anomaly']:+.1f} °C",
        )
    if v["vegetation_change"] < -5:
        add(
            "pressure",
            "high",
            "Убыль растительного покрова в DEMO-истории",
            "Исследовать причины потерь: землепользование, пожары, выпас, засуху; согласовать меры с местными участниками.",
            "Выявление устранимых причин деградации перед выбором вмешательства.",
            f"Изменение={v['vegetation_change']:+.1f} п.п.",
        )
    if v["vegetation_change"] > 5:
        add(
            "recovery",
            "medium",
            "В сценарии есть рост покрова, но его устойчивость не установлена",
            "Продолжить наблюдения и полевую проверку состава растительности, почвы и выживаемости посадок.",
            "Отделение устойчивого восстановления от сезонного озеленения.",
            f"Изменение={v['vegetation_change']:+.1f} п.п.",
        )
    add(
        "biodiversity",
        "medium" if rows else "low",
        "Биоразнообразие не определяется этими индикаторами",
        "Провести полевой учёт видов и местообитаний; защитить ценные участки до вмешательства.",
        "Основания для сохранения местных видов и выбора экологически совместимых мер.",
        "Видовой состав отсутствует в DEMO-наборе",
    )
    return rows
