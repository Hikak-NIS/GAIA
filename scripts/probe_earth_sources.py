"""Probe public services; optional recorded fixture for reproducible browser tests."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
from gaia.config import utcnow  # noqa: E402
from gaia.earth_schemas import EarthAnalysisIn  # noqa: E402
from gaia.global_schemas import Area  # noqa: E402
from gaia.services import earth_sources, earth_analysis, environment, planet  # noqa: E402
from gaia.services.remote import gather  # noqa: E402


def probe():
    area = Area(name="Приаралье", latitude=45.2, longitude=60.3, radius_km=20)
    result = gather(
        {
            "layers": earth_sources.layers,
            "planet": planet.overview,
            "analysis": lambda: earth_analysis.analyze(EarthAnalysisIn(area=area, satellite=False)),
            "ocean": lambda: environment.environment(40, -40, "marine"),
            "ocean_pacific": lambda: environment.environment(0, -140, "marine"),
            "ocean_indian": lambda: environment.environment(-20, 80, "marine"),
        }
    )
    return {
        "recorded_at": utcnow().isoformat(),
        "purpose": "Recorded responses from real public providers for tests; not production fallback",
        "results": result,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    result = probe()
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, source in result["results"].items():
        print(name, source["status"])
        if name == "analysis" and source.get("data"):
            for key, item in source["data"]["sources"].items():
                print(" ", key, item["status"])
        if name == "layers" and source.get("data"):
            print(" ", len(source["data"]["items"]), "satellite layers")
        if name == "planet" and source.get("data"):
            for key, item in source["data"]["sources"].items():
                print(" ", key, item["status"], (item.get("data") or {}).get("observed_at", ""))
