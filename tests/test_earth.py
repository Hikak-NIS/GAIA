"""Observation-mode contracts, email security, data provenance, AI boundaries and training."""

import csv
import importlib.util
import json
from datetime import timedelta
from pathlib import Path
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from conftest import register, territory, verify_challenge, MAILBOX
from gaia import models as m, global_models as g, security
from gaia.config import settings, SessionLocal, utcnow
from gaia.services import (
    mail,
    earth_analysis,
    earth_sources,
    environment,
    remote,
    planet,
    assistant,
    copernicus_live,
)
from gaia.earth_schemas import EarthAnalysisIn
from gaia.global_schemas import Area

FIXTURE = json.loads((Path(__file__).parent / "fixtures/earth-live.json").read_text(encoding="utf-8"))[
    "results"
]


@pytest.fixture(autouse=True)
def real_mode(monkeypatch):
    monkeypatch.setattr(settings, "legacy_simulation_enabled", False)
    remote._cache.clear()


def admin(client):
    user = register(client)
    with SessionLocal() as db:
        db.get(m.User, user["id"]).role = "admin"
        db.commit()
    return user


def body():
    return {
        "area": {"name": "Проверка", "latitude": 45.2, "longitude": 60.3, "radius_km": 20},
        "satellite": False,
    }


def test_signup_requires_email_proof_and_single_use_code(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "A",
            "nickname": "ConfirmMe",
            "email": "verify@example.com",
            "password": "garden-pass-123",
        },
    )
    assert response.status_code == 201
    challenge = response.json()["challenge_id"]
    assert "code" not in response.json()
    assert not client.cookies.get(security.COOKIE)
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.post("/api/v1/auth/resend-email", json={"challenge_id": challenge}).status_code == 429
    code = MAILBOX["verify@example.com"]
    assert (
        client.post(
            "/api/v1/auth/verify-email",
            json={"challenge_id": challenge, "code": "000000" if code != "000000" else "111111"},
        ).status_code
        == 400
    )
    user = verify_challenge(client, response).json()
    assert user["email_verified_at"]
    assert (
        client.post("/api/v1/auth/verify-email", json={"challenge_id": challenge, "code": code}).status_code
        == 400
    )
    client.post("/api/v1/auth/logout")
    login = client.post("/api/v1/auth/login", json={"identifier": "ConfirmMe", "password": "garden-pass-123"})
    assert client.get("/api/v1/users/me").status_code == 401
    verify_challenge(client, login)
    assert client.get("/api/v1/users/me").status_code == 200


def test_codes_expire_lock_out_and_resend_invalidates_old(client):
    register(client)

    def challenge():
        return client.post(
            "/api/v1/auth/login", json={"identifier": "anna@example.com", "password": "garden-pass-123"}
        )

    response = challenge()
    cid = response.json()["challenge_id"]
    with SessionLocal() as db:
        row = db.get(m.EmailChallenge, cid)
        row.created_at = utcnow() - timedelta(minutes=2)
        db.commit()
    resent = client.post("/api/v1/auth/resend-email", json={"challenge_id": cid})
    assert resent.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/verify-email", json={"challenge_id": cid, "code": MAILBOX["anna@example.com"]}
        ).status_code
        == 400
    )
    new_id = resent.json()["challenge_id"]
    wrong = "123456" if MAILBOX["anna@example.com"] != "123456" else "234567"
    for _ in range(5):
        assert (
            client.post("/api/v1/auth/verify-email", json={"challenge_id": new_id, "code": wrong}).status_code
            == 400
        )
    assert (
        client.post(
            "/api/v1/auth/verify-email", json={"challenge_id": new_id, "code": MAILBOX["anna@example.com"]}
        ).status_code
        == 400
    )
    expired = challenge()
    with SessionLocal() as db:
        db.get(m.EmailChallenge, expired.json()["challenge_id"]).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert (
        client.post(
            "/api/v1/auth/verify-email",
            json={"challenge_id": expired.json()["challenge_id"], "code": MAILBOX["anna@example.com"]},
        ).status_code
        == 400
    )


def test_mail_failure_does_not_create_account_or_session(client, monkeypatch):
    def fail(*args):
        raise HTTPException(503, "SMTP unavailable")

    monkeypatch.setattr(mail, "send_code", fail)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "A",
            "nickname": "MailFailure",
            "email": "failed@example.com",
            "password": "garden-pass-123",
        },
    )
    assert response.status_code == 503
    assert not client.cookies.get(security.COOKIE)
    with SessionLocal() as db:
        assert db.scalar(select(m.User).where(m.User.email == "failed@example.com")) is None


def test_first_email_confirmation_revokes_all_pre_upgrade_sessions(client):
    user = register(client)
    with SessionLocal() as db:
        db.get(m.User, user["id"]).email_verified_at = None
        db.add(
            m.AuthSession(
                user_id=user["id"],
                token_hash=security.digest("old-browser-token"),
                expires_at=utcnow() + timedelta(days=1),
            )
        )
        db.commit()
    assert client.get("/api/v1/users/me").status_code == 401
    login = client.post(
        "/api/v1/auth/login", json={"identifier": user["email"], "password": "garden-pass-123"}
    )
    verify_challenge(client, login)
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(m.AuthSession).where(m.AuthSession.token_hash == security.digest("old-browser-token"))
            )
            is None
        )
        assert len(db.scalars(select(m.AuthSession)).all()) == 1


def test_observation_mode_hides_generated_history_and_devices(client):
    user = admin(client)
    yard = territory(client)
    assert client.get(f"/api/v1/territories/{yard['id']}/devices").json() == []
    assert client.post(f"/api/v1/territories/{yard['id']}/simulation/start").status_code == 410
    with SessionLocal() as db:
        row = g.GlobalAnalysis(
            creator_id=user["id"], name="old", latitude=0, longitude=0, source="demo", result={}
        )
        db.add(row)
        db.commit()
        old_id = row.id
    assert client.get("/api/v1/global/analyses").json() == []
    assert client.get(f"/api/v1/global/analyses/{old_id}").status_code == 410


def test_analysis_role_provenance_persistence_and_partial_failure(client, monkeypatch):
    register(client)
    assert client.post("/api/v1/earth/analyses", json=body()).status_code == 403
    with SessionLocal() as db:
        db.scalar(select(m.User)).role = "admin"
        db.commit()
    recorded = FIXTURE["analysis"]["data"]
    monkeypatch.setattr(earth_analysis, "analyze", lambda request: recorded)
    result = client.post("/api/v1/earth/analyses", json=body())
    assert result.status_code == 201, result.text
    saved = result.json()
    assert saved["data_kind"] == "observations" and saved["assessment"]["score"] is None
    assert all(m["source"] and m["observed_at"] for m in saved["metrics"] if m["value"] is not None)
    assert client.get(f"/api/v1/global/analyses/{saved['id']}").json()["metrics"] == saved["metrics"]
    with SessionLocal() as db:
        db.scalar(select(m.User)).role = "user"
        db.commit()
    assert client.get(f"/api/v1/global/analyses/{saved['id']}").status_code == 403


def test_no_synthetic_fallback_and_no_secrets_on_upstream_errors(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("secret-key-should-not-leak")

    monkeypatch.setattr(earth_analysis, "environment", fail)
    monkeypatch.setattr(earth_sources, "scenes", fail)
    monkeypatch.setattr(earth_sources, "nasa_catalog", fail)
    monkeypatch.setattr(settings, "copernicus_client_id", "")
    result = earth_analysis.analyze(EarthAnalysisIn(area=Area(latitude=0, longitude=0)))
    assert result["metrics"] == []
    assert result["assessment"]["score"] is None
    assert "secret-key" not in json.dumps(result)
    assert result["sources"]["sentinel_statistics"]["status"] == "needs_configuration"


def test_dates_nan_and_limits_are_validated(client):
    admin(client)
    for change in (
        {"start": "1999-01-01"},
        {"end": "2099-01-01"},
        {"start": "2020-01-01", "end": "2022-01-01"},
    ):
        assert client.post("/api/v1/earth/analyses", json={**body(), **change}).status_code == 422
    assert (
        client.post(
            "/api/v1/earth/analyses", json={**body(), "area": {**body()["area"], "latitude": 91}}
        ).status_code
        == 422
    )


def test_model_series_excludes_future_and_preserves_missing(monkeypatch):
    now = utcnow()
    data = {
        "latitude": 0,
        "longitude": 0,
        "hourly": {
            "time": [
                (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
                (now + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            ],
            "temperature_2m": [12, 99],
        },
        "hourly_units": {"temperature_2m": "°C"},
    }
    monkeypatch.setattr(environment, "fetch", lambda *a, **k: data)
    result = environment.environment(0, 0)
    assert result["metrics"][0]["value"] == 12
    assert result["metrics"][1]["value"] is None
    assert result["metrics"][0]["kind"] == "model"


def test_climate_parser_baseline_and_missing(monkeypatch):
    monkeypatch.setattr(
        planet,
        "fetch",
        lambda *a, **k: (
            "Land-Ocean: Global Means\nYear,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec\n2025,1.2,1.1,***,***,***,***,***,***,***,***,***,***\n"
        ),
    )
    result = planet.temperature()
    assert result["observed_at"] == "2025-02-01" and result["value"] == 1.1
    assert "1951–1980" in result["description"]


def test_sea_ice_v4_parser_ignores_units_missing_and_invalid_rows(monkeypatch):
    urls = []

    def fetch(url, **kwargs):
        urls.append(url)
        return "Year, Month, Day, Extent, Missing, Source Data\nyyyy, mm, dd, million sq km, million sq km, source\n2026, 11, 6, 8.400, 0.000, amsr2\n2026, 11, 7, -9999, 0.000, missing\n2026, 11, 8, 8.580, 0.000, amsr2\n2026, 11, 9, 9.000, 0.200, incomplete\n"

    monkeypatch.setattr(planet, "fetch", fetch)
    data = planet.sea_ice("north")
    assert data["value"] == 8.58 and data["observed_at"] == "2026-11-08"
    assert len(data["history"]) == 2 and data["kind"] == "satellite"
    assert urls[0].endswith("/north/daily/data/N_seaice_extent_daily_v4.0.csv")
    with pytest.raises(ValueError):
        planet.sea_ice("invalid")


def test_assistant_no_key_and_cross_user_context(client, monkeypatch):
    user = register(client)
    yard = territory(client)
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert client.post("/api/v1/assistant/chat", json={"question": "Почва?"}).status_code == 503
    client.post("/api/v1/auth/logout")
    register(client, email="second@example.com")
    assert (
        client.post(
            "/api/v1/assistant/chat", json={"question": "Почва?", "territory_id": yard["id"]}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/assistant/chat", json={"question": "Почва?", "analysis_id": user["id"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/assistant/transcribe", files={"file": ("bad.exe", b"MZ", "application/octet-stream")}
        ).status_code
        == 415
    )


def test_assistant_text_voice_contract_and_secret_not_returned(client, monkeypatch):
    register(client)
    calls = []

    class Result:
        content = b"ID3-test-audio"

        def json(self):
            return {
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "Нужны измерения."}]}
                ],
                "text": "Проверь почву",
            }

    def call(path, **kwargs):
        calls.append((path, kwargs))
        return Result()

    monkeypatch.setattr(assistant, "call", call)
    response = client.post("/api/v1/assistant/chat", json={"question": "Что делать?"})
    assert response.json()["text"] == "Нужны измерения."
    assert calls[0][1]["json"]["store"] is False
    assert (
        client.post(
            "/api/v1/assistant/transcribe", files={"file": ("voice.webm", b"audio", "audio/webm")}
        ).json()["text"]
        == "Проверь почву"
    )
    assert (
        client.post("/api/v1/assistant/speech", json={"text": "Ответ"}).headers["content-type"]
        == "audio/mpeg"
    )
    assert [x[0] for x in calls] == ["responses", "audio/transcriptions", "audio/speech"]


def test_configuration_never_exposes_credentials(client, monkeypatch):
    user = register(client)
    monkeypatch.setattr(settings, "openai_api_key", "sensitive-value")
    assert "items" not in client.get("/api/v1/integrations/status").json()
    with SessionLocal() as db:
        db.get(m.User, user["id"]).role = "superadmin"
        db.commit()
    response = client.get("/api/v1/integrations/status")
    assert "items" in response.json() and "sensitive-value" not in response.text


def test_satellite_geometry_and_scope():
    area = Area(latitude=45, longitude=60, radius_km=20)
    ring = copernicus_live.geometry(area)["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 65
    with pytest.raises(HTTPException):
        copernicus_live.input_data(Area(latitude=0, longitude=0, radius_km=100), "2026-01-01", "2026-01-31")


@pytest.mark.parametrize("ocean,expected", [(False, "ndvi"), (True, "ndwi")])
def test_satellite_statistics_exclude_masked_intervals_and_preserve_quality(monkeypatch, ocean, expected):
    requests = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": [
                    {
                        "interval": {"from": "2026-01-01T00:00:00Z", "to": "2026-01-11T00:00:00Z"},
                        "outputs": {
                            "indices": {
                                "bands": {
                                    "B0": {"stats": {"mean": 0.4, "sampleCount": 100, "noDataCount": 25}}
                                }
                            }
                        },
                    },
                    {
                        "interval": {"from": "2026-01-11T00:00:00Z", "to": "2026-01-21T00:00:00Z"},
                        "outputs": {
                            "indices": {
                                "bands": {
                                    "B0": {"stats": {"mean": 99, "sampleCount": 100, "noDataCount": 100}}
                                }
                            }
                        },
                    },
                ]
            }

    def post(url, **kwargs):
        requests.append((url, kwargs))
        return Response()

    monkeypatch.setattr(copernicus_live, "token", lambda: "test-token")
    monkeypatch.setattr(copernicus_live.httpx, "post", post)
    result = copernicus_live.stats(
        Area(latitude=45, longitude=60, radius_km=20), "2026-01-01", "2026-01-31", ocean
    )
    metric = result["metrics"][0]
    assert metric["id"] == expected and metric["value"] == 0.4 and metric["quality"] == 0.75
    assert len(metric["history"]) == 1 and result["metrics"][1]["value"] is None
    payload = requests[0][1]["json"]
    assert payload["input"]["bounds"]["geometry"]["type"] == "Polygon"
    assert ("s.SCL===6" if ocean else "s.SCL!==6") in payload["aggregation"]["evalscript"]


def test_training_holdout_portable_inference_and_no_deployed_test_model(tmp_path, monkeypatch):
    from gaia.services import eco_model

    spec = importlib.util.spec_from_file_location(
        "trainer", Path(__file__).parents[1] / "scripts/train_eco_model.py"
    )
    trainer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trainer)
    data = tmp_path / "test-only-fixture.csv"
    fields = eco_model.FEATURES["land"]
    with data.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["site_id", "observed_at", "risk_label", *fields])
        writer.writeheader()
        for day in range(1, 29):
            for site in range(20):
                label = (day + site) % 2
                writer.writerow(
                    {
                        "site_id": f"test-site-{site}",
                        "observed_at": f"2025-01-{day:02d}",
                        "risk_label": label,
                        **{key: label + site / 100 + day / 1000 for key in fields},
                    }
                )
    output = tmp_path / "land-risk.json"
    report = trainer.train(data, "land", "Synthetic test fixture only", output)
    assert report["test_rows"] >= 20 and report["train_rows"] >= 40
    artifact = json.loads(output.read_text(encoding="utf-8"))
    monkeypatch.setattr(eco_model, "model_path", lambda kind: output)
    prediction = eco_model.predict("land", {key: 1.1 for key in fields})
    assert 0 <= prediction["risk_probability"] <= 1
    with pytest.raises(ValueError):
        eco_model.predict("land", {key: 999 for key in fields})
    assert artifact["report"]["status"] == "research_only"
