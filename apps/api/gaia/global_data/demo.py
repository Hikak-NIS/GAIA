import hashlib
import math
from datetime import date
from ..global_schemas import Area


class DemoProvider:
    key = "demo"

    def describe(self):
        return {
            "id": self.key,
            "name": "GAIA · DEMO dataset v1",
            "status": "demo",
            "available": True,
            "url": None,
            "requirements": "Синтетические сценарии; не измерения территории и не спутниковый продукт.",
            "products": ["7 экологических индикаторов", "12 месяцев демонстрационной истории"],
        }

    def fetch(self, area: Area, scenario: str, as_of: date):
        # Reproducible variation is only for demonstrating the interface, not geography-derived evidence.
        key = f"{area.latitude:.4f}|{area.longitude:.4f}|{area.radius_km:.1f}|{scenario}"
        variation = (int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF - 0.5) * 0.06
        base = {
            "degraded": (0.23, 12, 8, 14, 24, -15),
            "recovering": (0.48, 27, 3.5, 38, 51, 8),
            "balanced": (0.76, 43, 0.8, 58, 79, 2),
        }[scenario]
        ndvi, soil, anomaly, rain, cover, change = base
        ndvi = round(ndvi + variation, 3)
        soil = round(soil + variation * 20, 1)
        cover = round(cover + variation * 25, 1)
        anomaly = round(anomaly - variation * 5, 1)
        rain = round(rain + variation * 50, 1)
        total_month = as_of.year * 12 + as_of.month - 1
        history = []
        for i in range(12):
            year, month = divmod(total_month - 11 + i, 12)
            fraction = i / 11
            seasonal = math.sin(fraction * 2 * math.pi)  # both endpoints zero; declared change stays exact
            history.append(
                {
                    "date": date(year, month + 1, 1).isoformat(),
                    "source": "DEMO",
                    "ndvi": round(max(-1, min(1, ndvi - change / 100 * (1 - fraction) + 0.03 * seasonal)), 3),
                    "vegetation_cover": round(cover - change * (1 - fraction) + 2 * seasonal, 1),
                    "soil_moisture": round(max(0, soil + 4 * seasonal), 1),
                    "precipitation": round(max(0, rain + 6 * seasonal), 1),
                }
            )
        return {
            "source": "DEMO",
            "provider": "GAIA DEMO v1",
            "as_of": as_of.isoformat(),
            "values": {
                "ndvi": ndvi,
                "soil_moisture": soil,
                "lst": round(24 + anomaly, 1),
                "temperature_anomaly": anomaly,
                "precipitation": rain,
                "vegetation_cover": cover,
                "vegetation_change": change,
            },
            "demo_baselines": {"lst_c": 24, "precipitation_mm_30d": 60},
            "history": history,
        }
