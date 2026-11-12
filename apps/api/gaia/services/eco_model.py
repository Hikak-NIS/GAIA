"""Portable tree model inference. JSON only: never unpickle uploaded artifacts."""

import json
import math
from ..config import ROOT

FEATURES = {
    "land": ["ndvi", "ndmi", "soil_moisture", "temperature_anomaly", "rainfall_30d", "tree_loss_fraction"],
    "microplastics": [
        "population_density",
        "distance_to_river_km",
        "wastewater_sites_10km",
        "runoff_mm",
        "current_velocity",
        "plastic_waste_kg_km2",
    ],
}


def model_path(kind):
    if kind not in FEATURES:
        raise ValueError("Unknown model kind")
    return ROOT / "data" / "models" / f"{kind}-risk.json"


def describe(kind):
    path = model_path(kind)
    if not path.is_file():
        return {
            "kind": kind,
            "status": "not_trained",
            "features": FEATURES[kind],
            "message": "Нужны размеченные полевые данные. Инструкция: docs/model-training.md",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "kind": kind,
        "status": "research",
        "features": data["features"],
        "report": data["report"],
        "message": "Исследовательская модель. Вероятность класса риска, не концентрация и не диагноз.",
    }


def predict(kind, features):
    path = model_path(kind)
    if not path.is_file():
        raise ValueError("Модель ещё не обучена; сначала выполните инструкцию обучения")
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(features) != set(data["features"]):
        raise ValueError("Нужно передать все признаки модели с указанными единицами")
    values = [float(features[name]) for name in data["features"]]
    if not all(math.isfinite(x) for x in values):
        raise ValueError("Признаки должны быть конечными числами")
    outside = [
        name
        for name, value, interval in zip(data["features"], values, data["ranges"], strict=True)
        if value < interval[0] or value > interval[1]
    ]
    if outside:
        raise ValueError("Признаки вне диапазона обучения: " + ", ".join(outside))
    probabilities = []
    for tree in data["trees"]:
        node = 0
        while tree["left"][node] != -1:
            node = (
                tree["left"][node]
                if values[tree["feature"][node]] <= tree["threshold"][node]
                else tree["right"][node]
            )
        probabilities.append(tree["probability"][node])
    return {
        "risk_probability": sum(probabilities) / len(probabilities),
        "kind": kind,
        "model_version": data["report"]["trained_at"],
        "label_definition": data["report"]["label_definition"],
        "note": "Исследовательская оценка риска; не измерение концентрации. Требуется независимая полевая проверка.",
    }
