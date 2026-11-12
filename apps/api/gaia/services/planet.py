"""Global observed climate series; each has its own publication cadence and baseline."""

import csv
import io
from ..config import utcnow
from .remote import cached, fetch, gather
from .earth_sources import events


def temperature():
    raw = fetch("https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv", as_text=True)
    rows = csv.DictReader(io.StringIO(raw[raw.index("Year,") :]))
    history = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for row in rows:
        for month, name in enumerate(months, 1):
            try:
                value = float(row[name])
            except (ValueError, TypeError):
                continue
            history.append({"date": f"{row['Year']}-{month:02d}-01", "value": value})
    return {
        "id": "global_temperature_anomaly",
        "label": "Глобальная температурная аномалия",
        "unit": "°C",
        "source": "NASA GISTEMP v4",
        "source_url": "https://data.giss.nasa.gov/gistemp/",
        "kind": "observation",
        "description": "Месячная аномалия температуры суши и океана относительно 1951–1980. Не отклонение от доиндустриального уровня.",
        "value": history[-1]["value"],
        "observed_at": history[-1]["date"],
        "history": history[-600:],
    }


def carbon():
    raw = fetch("https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_gl.csv", as_text=True)
    rows = csv.DictReader(
        io.StringIO("\n".join(line for line in raw.splitlines() if not line.startswith("#")))
    )
    history = []
    for row in rows:
        try:
            value = float(row["average"])
            if value > 0:
                history.append({"date": f"{int(row['year'])}-{int(row['month']):02d}-01", "value": value})
        except (ValueError, KeyError):
            continue
    return {
        "id": "global_co2",
        "label": "Глобальная концентрация CO₂",
        "unit": "ppm",
        "source": "NOAA GML",
        "source_url": "https://gml.noaa.gov/ccgg/trends/gl_data.html",
        "kind": "observation",
        "description": "Глобальное среднемесячное содержание CO₂. Последние значения могут уточняться NOAA.",
        "value": history[-1]["value"],
        "observed_at": history[-1]["date"],
        "history": history[-600:],
    }


def overview():
    return cached(
        "planet-overview",
        lambda: {
            "fetched_at": utcnow().isoformat(),
            "sources": gather(
                {
                    "temperature": temperature,
                    "co2": carbon,
                    "events": events,
                    "arctic_ice": lambda: sea_ice("north"),
                    "antarctic_ice": lambda: sea_ice("south"),
                }
            ),
            "note": "Обзор планеты объединяет продукты с разными датами и разрешением. Единого подтверждённого балла здоровья Земли нет.",
        },
        3600,
    )


def sea_ice(hemisphere):
    if hemisphere not in ("north", "south"):
        raise ValueError("Unknown hemisphere")
    prefix = hemisphere[0].upper()
    raw = fetch(
        f"https://noaadata.apps.nsidc.org/NOAA/G02135/{hemisphere}/daily/data/{prefix}_seaice_extent_daily_v4.0.csv",
        as_text=True,
    )
    rows = csv.DictReader(io.StringIO(raw), skipinitialspace=True)
    history = []
    for row in rows:
        try:
            value = float(row["Extent"])
            if value >= 0 and float(row["Missing"]) == 0:
                history.append(
                    {
                        "date": f"{int(row['Year'])}-{int(row['Month']):02d}-{int(row['Day']):02d}",
                        "value": value,
                    }
                )
        except (ValueError, KeyError, TypeError):
            continue
    return {
        "id": f"sea_ice_{hemisphere}",
        "label": "Протяжённость морского льда · " + ("Арктика" if hemisphere == "north" else "Антарктика"),
        "unit": "млн км²",
        "kind": "satellite",
        "source": "NSIDC Sea Ice Index v4",
        "source_url": "https://nsidc.org/data/g02135/versions/4",
        "value": history[-1]["value"],
        "observed_at": history[-1]["date"],
        "history": history[-3660:],
        "description": "Extent: площадь ячеек с концентрацией льда ≥15%. Не масса ледника и не сумма только ледяной поверхности. Суточные значения подвержены погодной изменчивости; тренд оценивают по сопоставимым сезонам.",
    }
