"""Isolated browser-test app: captures verification mail and replays recorded public data.

There is no email bypass or fixture mode in the production application.
"""

import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
from gaia.config import engine, settings, SessionLocal  # noqa: E402
from gaia import models as m  # noqa: E402
from gaia.services import mail, earth_sources, environment, earth_analysis, planet  # noqa: E402
from gaia.main import app  # noqa: E402
import uvicorn  # noqa: E402

if (
    engine.dialect.name != "sqlite"
    or Path(engine.url.database).resolve() != ROOT / "data/gaia_e2e.db"
    or settings.web_origin != "http://localhost:5174"
):
    raise SystemExit("Refusing test server outside isolated E2E database and origin")

mailbox = ROOT / "data/e2e-mailbox.json"
mailbox.write_text("{}", encoding="utf-8")


def capture(address, code):
    values = json.loads(mailbox.read_text(encoding="utf-8"))
    values[address] = code
    temporary = mailbox.with_suffix(".tmp")
    temporary.write_text(json.dumps(values), encoding="utf-8")
    temporary.replace(mailbox)


mail.send_code = capture
recorded = json.loads((ROOT / "tests/fixtures/earth-live.json").read_text(encoding="utf-8"))["results"]
earth_sources.layers = lambda: copy.deepcopy(recorded["layers"]["data"])
planet.overview = lambda: copy.deepcopy(recorded["planet"]["data"])
earth_sources.events = lambda: copy.deepcopy(recorded["planet"]["data"]["sources"]["events"]["data"])


def env(latitude, longitude, service="weather"):
    if service == "marine":
        key = {(0, -140): "ocean_pacific", (-20, 80): "ocean_indian"}.get((latitude, longitude), "ocean")
        return copy.deepcopy(recorded[key]["data"])
    return copy.deepcopy(recorded["analysis"]["data"]["sources"][service]["data"])


def analyze(body):
    value = copy.deepcopy(recorded["analysis"]["data"])
    value.update(
        area=body.area.model_dump(), ocean=body.ocean, period={"start": str(body.start), "end": str(body.end)}
    )
    return value


environment.environment = env
earth_analysis.analyze = analyze
with SessionLocal() as db:
    db.query(m.LoginAttempt).delete()
    db.commit()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, workers=1)
