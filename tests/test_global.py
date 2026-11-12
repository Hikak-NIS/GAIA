from datetime import date
import sqlite3
import pytest
from sqlalchemy import select
from conftest import register, verify_challenge
from gaia import models as m, global_models as g, security
from gaia.config import SessionLocal, utcnow
from gaia.global_schemas import Area, Weights
from gaia.global_data.demo import DemoProvider
from gaia.services.global_analysis import evaluate, health_level
from test_migrations import run_migration, legacy_database, snapshot


def login(client, identifier, password="garden-pass-123"):
    response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200, response.text
    return verify_challenge(client, response).json()


def chief(client):
    with SessionLocal() as db:
        user = m.User(
            name="Главный",
            nickname="SENQwir",
            nickname_key="senqwir",
            email="gulnarapulatova9@gmail.com",
            role="superadmin",
            password_hash=security.hasher.hash("garden-pass-123"),
        )
        db.add(user)
        db.commit()
    return login(client, "SENQwir")


def analysis_body(scenario="degraded"):
    return {
        "area": {"name": "Тестовая область", "latitude": 45.1, "longitude": 60.2, "radius_km": 50},
        "source": "demo",
        "scenario": scenario,
    }


def test_registration_requires_nickname_and_cannot_self_promote(client):
    body = {"name": "Обычный", "email": "ordinary@example.com", "password": "garden-pass-123"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 422
    assert (
        client.post(
            "/api/v1/auth/register", json={**body, "nickname": "Ordinary", "role": "superadmin"}
        ).status_code
        == 422
    )
    for nickname in ("x", "contains space", "bad@email", "a" * 33):
        assert client.post("/api/v1/auth/register", json={**body, "nickname": nickname}).status_code == 422
    for update in ({"nickname": "SeNqWiR"}, {"nickname": "Ordinary", "email": "gulnarapulatova9@gmail.com"}):
        assert client.post("/api/v1/auth/register", json={**body, **update}).status_code == 409
    user = register(client, nickname="GardenUser")
    assert user["role"] == "user"
    assert "password" not in str(user)
    client.post("/api/v1/auth/logout")
    assert client.post("/api/v1/auth/register", json={**body, "nickname": "gardenuser"}).status_code == 409
    assert login(client, "GARDENUSER")["id"] == user["id"]
    assert login(client, "ANNA@EXAMPLE.COM")["id"] == user["id"]
    changed = client.put("/api/v1/users/me/nickname", json={"nickname": "RenamedUser"})
    assert changed.status_code == 200
    assert login(client, "renameduser")["id"] == user["id"]
    assert client.put("/api/v1/users/me/nickname", json={"nickname": "SENQwir"}).status_code == 409


def test_global_and_directory_require_server_side_roles(client):
    paths = [
        "/global/providers",
        "/global/settings",
        "/global/analyses",
        "/global/analyses/missing",
        "/global/markers",
        "/admin/users",
        "/admin/audit",
    ]
    for path in paths:
        assert client.get("/api/v1" + path).status_code == 401
    register(client)
    for path in paths:
        assert client.get("/api/v1" + path).status_code == 403
    assert client.post("/api/v1/global/analyses", json=analysis_body()).status_code == 403
    assert client.put("/api/v1/admin/users/fake/role", json={"role": "admin"}).status_code == 403
    assert (
        client.post("/api/v1/global/markers", json={"title": "X", "latitude": 0, "longitude": 0}).status_code
        == 403
    )


def test_chief_can_assign_revoke_and_cannot_be_removed(client):
    ordinary = register(client, nickname="SelectedAdmin")
    ordinary_cookie = client.cookies.get(security.COOKIE)
    client.cookies.clear()  # Separate browser session; login otherwise correctly revokes the prior cookie.
    superuser = chief(client)
    assert client.get("/api/v1/admin/users?q=selectedADMIN").json()["total"] == 1
    assert client.get("/api/v1/admin/users?q=%").json()["total"] == 0
    promote = client.put(f"/api/v1/admin/users/{ordinary['id']}/role", json={"role": "admin"})
    assert promote.status_code == 200 and promote.json()["role"] == "admin"
    chief_cookie = client.cookies.get(security.COOKIE)
    client.cookies.clear()
    client.cookies.set(security.COOKIE, ordinary_cookie)
    assert client.get("/api/v1/global/providers").status_code == 200
    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.put(f"/api/v1/admin/users/{ordinary['id']}/role", json={"role": "admin"}).status_code == 403
    client.cookies.clear()
    client.cookies.set(security.COOKIE, chief_cookie)
    assert client.put(f"/api/v1/admin/users/{superuser['id']}/role", json={"role": "user"}).status_code == 409
    assert (
        client.put(f"/api/v1/admin/users/{ordinary['id']}/role", json={"role": "superadmin"}).status_code
        == 422
    )
    assert client.put("/api/v1/users/me/nickname", json={"nickname": "OtherChief"}).status_code == 409
    client.put(f"/api/v1/admin/users/{ordinary['id']}/role", json={"role": "user"})
    audit = client.get("/api/v1/admin/audit").json()
    assert len(audit) == 2
    client.cookies.clear()
    client.cookies.set(security.COOKIE, ordinary_cookie)
    assert client.get("/api/v1/global/providers").status_code == 403
    assert client.get("/api/v1/users/me").status_code == 200


def test_global_analysis_snapshot_and_weight_revision(client):
    chief(client)
    response = client.post("/api/v1/global/analyses", json=analysis_body())
    assert response.status_code == 201, response.text
    data = response.json()
    assert len(data["metrics"]) == 7 and len(data["history"]) == 12
    assert all(m["source"] == "DEMO" and m["updated_at"] for m in data["metrics"])
    assert all(h["source"] == "DEMO" for h in data["history"])
    assert data["recommendations"] and all(
        r["problem"] and r["action"] and r["expected_effect"] for r in data["recommendations"]
    )
    assert data["area"] == analysis_body()["area"]
    assert client.get(f"/api/v1/global/analyses/{data['id']}").json() == data
    assert client.get("/api/v1/global/analyses").json()[0]["id"] == data["id"]
    old = client.get("/api/v1/global/settings").json()
    new = {
        "weights": {"vegetation": 100, "moisture": 0, "temperature": 0, "change": 0, "precipitation": 0},
        "expected_revision": old["revision"],
    }
    assert client.put("/api/v1/global/settings", json=new).status_code == 200
    assert client.put("/api/v1/global/settings", json=new).status_code == 409
    assert client.get(f"/api/v1/global/analyses/{data['id']}").json() == data
    next_result = client.post("/api/v1/global/analyses", json=analysis_body()).json()
    assert next_result["gehi"]["weights_revision"] == 2
    assert next_result["gehi"]["weights"]["vegetation"] == 100
    assert next_result["gehi"]["score"] != data["gehi"]["score"]


def test_real_provider_never_falls_back_to_demo(client):
    chief(client)
    providers = client.get("/api/v1/global/providers").json()
    assert sum(p["available"] for p in providers) == 1
    for source in ("copernicus", "nasa", "earth_engine"):
        response = client.post("/api/v1/global/analyses", json={**analysis_body(), "source": source})
        assert response.status_code == 503
    assert client.get("/api/v1/global/analyses").json() == []


def test_global_validation_and_csrf(client):
    chief(client)
    for field, value in (("latitude", 86), ("longitude", -181), ("radius_km", 0), ("name", "   ")):
        body = analysis_body()
        body["area"][field] = value
        assert client.post("/api/v1/global/analyses", json=body).status_code == 422
    assert (
        client.post("/api/v1/global/analyses", json={**analysis_body(), "scenario": "invented"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/global/analyses", headers={"Origin": "https://evil.example"}, json=analysis_body()
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/v1/global/settings", json={"weights": {"vegetation": 101}, "expected_revision": 1}
        ).status_code
        == 422
    )


def test_shared_markers_only_creator_or_chief_deletes(client):
    ordinary = register(client, nickname="AdminTwo")
    with SessionLocal() as db:
        db.get(m.User, ordinary["id"]).role = "admin"
        db.commit()
    chief(client)
    created = client.post(
        "/api/v1/global/markers",
        json={"title": "Полевой осмотр", "category": "erosion", "latitude": 45, "longitude": 60},
    ).json()
    login(client, "AdminTwo")
    assert client.get("/api/v1/global/markers").json()[0]["id"] == created["id"]
    assert client.delete(f"/api/v1/global/markers/{created['id']}").status_code == 403
    mine = client.post(
        "/api/v1/global/markers", json={"title": "Моя заметка", "latitude": 0, "longitude": 0}
    ).json()
    assert client.delete(f"/api/v1/global/markers/{mine['id']}").status_code == 200
    assert (
        client.put("/api/v1/global/settings", json={"weights": {}, "expected_revision": 1}).status_code == 403
    )


def test_gehi_reproducibility_and_scenario_sensitivity():
    provider = DemoProvider()
    area = Area(latitude=45.1, longitude=60.2, radius_km=50)
    scores = {}
    for scenario in ("degraded", "recovering", "balanced"):
        observation = provider.fetch(area, scenario, date(2026, 11, 8))
        assert provider.fetch(area, scenario, date(2026, 11, 8)) == observation
        result = evaluate(observation, Weights(), 1)
        scores[scenario] = result["gehi"]["score"]
        assert 0 <= scores[scenario] <= 100
        assert abs(sum(f["contribution"] for f in result["gehi"]["factors"]) - scores[scenario]) < 0.55
        history = result["history"]
        assert history[0]["date"] == "2025-12-01" and history[-1]["date"] == "2026-11-01"
        assert history[-1]["vegetation_cover"] - history[0]["vegetation_cover"] == pytest.approx(
            observation["values"]["vegetation_change"]
        )
    assert scores["degraded"] < scores["recovering"] < scores["balanced"]
    with pytest.raises(ValueError):
        Weights(vegetation=0)


@pytest.mark.parametrize(
    "score,level",
    [
        (0, "critical"),
        (20, "critical"),
        (21, "severe"),
        (40, "severe"),
        (41, "moderate"),
        (60, "moderate"),
        (61, "satisfactory"),
        (80, "satisfactory"),
        (81, "good"),
        (100, "good"),
    ],
)
def test_gehi_boundaries(score, level):
    assert health_level(score)[0] == level


def test_global_migration_preserves_password_sessions_and_user_history(tmp_path):
    path = tmp_path / "global-upgrade.db"
    legacy_database(path)
    run_migration(path, "upgrade", "7b94d6120344")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE users SET email='gulnarapulatova9@gmail.com'")
        uid = db.execute("SELECT id FROM users").fetchone()[0]
        db.execute(
            "INSERT INTO auth_sessions (id,user_id,token_hash,expires_at) VALUES (?,?,?,?)",
            (m.uid(), uid, "preserved-session", utcnow().isoformat()),
        )
    before = snapshot(path)
    run_migration(path, "upgrade", "head")
    after = snapshot(path)
    assert all(after[name] == rows for name, rows in before.items())
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT nickname,nickname_key,role,password_hash FROM users").fetchone() == (
            "SENQwir",
            "senqwir",
            "superadmin",
            "test-only-hash",
        )
        assert db.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0] == 1
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
    run_migration(path, "check")


def test_migration_failure_during_users_rebuild_is_atomic(tmp_path):
    path = tmp_path / "global-failed.db"
    legacy_database(path)
    run_migration(path, "upgrade", "7b94d6120344")
    before = snapshot(path)
    code = """
from alembic import command
from alembic.config import Config
from alembic.operations import Operations
original = Operations.create_table
def fail(self, name, *args, **kwargs):
    if name == "global_analyses":
        raise RuntimeError("intentional global failure")
    return original(self, name, *args, **kwargs)
Operations.create_table = fail
command.upgrade(Config("alembic.ini"), "head")
"""
    response = run_migration(path, code=code, success=False)
    assert "intentional global failure" in response.stderr
    assert snapshot(path) == before
    with sqlite3.connect(path) as db:
        assert "nickname" not in {r[1] for r in db.execute("PRAGMA table_info(users)")}
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "7b94d6120344"


def test_saved_analysis_access_is_revoked_even_with_existing_session(client):
    user = register(client)
    with SessionLocal() as db:
        db.get(m.User, user["id"]).role = "admin"
        db.commit()
    created = client.post("/api/v1/global/analyses", json=analysis_body()).json()
    with SessionLocal() as db:
        db.get(m.User, user["id"]).role = "user"
        db.commit()
        assert db.scalar(select(g.GlobalAnalysis).where(g.GlobalAnalysis.id == created["id"])) is not None
    assert client.get(f"/api/v1/global/analyses/{created['id']}").status_code == 403
