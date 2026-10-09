from datetime import datetime, timezone

from conftest import register, territory


def test_registration_session_login_logout(client):
    user = register(client)
    assert user["email"] == "anna@example.com"
    assert client.cookies.get("gaia_session")
    assert client.get("/api/v1/users/me").json()["id"] == user["id"]

    session_cookie = client.cookies.get("gaia_session")
    client.cookies.clear()
    client.cookies.set("gaia_session", session_cookie)
    assert client.get("/api/v1/users/me").status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/users/me").status_code == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "anna@example.com", "password": "garden-pass-123"},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/users/me").status_code == 200


def test_duplicate_email_and_password_validation(client):
    register(client)
    client.post("/api/v1/auth/logout")
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"name": "Другая", "email": "ANNA@example.com", "password": "garden-pass-456"},
    )
    assert duplicate.status_code == 409
    weak = client.post(
        "/api/v1/auth/register",
        json={"name": "Другая", "email": "other@example.com", "password": "short"},
    )
    assert weak.status_code == 422


def test_territory_crud_and_ownership(client):
    register(client)
    yard = territory(client)
    assert client.get("/api/v1/territories").json()[0]["name"] == "Мой двор"
    updated = client.put(
        f"/api/v1/territories/{yard['id']}",
        json={
            "name": "Тихий сад",
            "description": "Обновлено",
            "latitude": 43.24,
            "longitude": 76.9,
            "area": 150,
            "timezone": "Asia/Almaty",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Тихий сад"

    client.post("/api/v1/auth/logout")
    register(client, name="Борис", email="boris@example.com")
    assert client.get(f"/api/v1/territories/{yard['id']}").status_code == 404
    assert client.get(f"/api/v1/territories/{yard['id']}/dashboard").status_code == 404
    assert client.get(f"/api/v1/territories/{yard['id']}/alerts").status_code == 404
    assert client.delete(f"/api/v1/territories/{yard['id']}").status_code == 404


def test_observation_and_saved_report(client):
    register(client)
    yard = territory(client)
    observation = client.post(
        f"/api/v1/territories/{yard['id']}/observations",
        json={
            "category": "vegetation",
            "severity": "warning",
            "text": "Листья начали скручиваться",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": yard["latitude"],
            "longitude": yard["longitude"],
        },
    )
    assert observation.status_code == 201, observation.text
    assert observation.json()["source"] == "manual"
    assert len(client.get(f"/api/v1/territories/{yard['id']}/observations").json()) == 1

    report = client.post(f"/api/v1/territories/{yard['id']}/reports")
    assert report.status_code == 201, report.text
    assert report.json()["data"]["observations"] == ["Листья начали скручиваться"]
    assert len(client.get(f"/api/v1/territories/{yard['id']}/reports").json()) == 1


def test_simulation_api_round_trip_has_utc_timestamps(client):
    register(client)
    yard = territory(client)
    response = client.post(
        f"/api/v1/territories/{yard['id']}/simulations",
        json={"action": "tick", "scenario": "drought", "speed": 60, "seed": 42},
    )
    assert response.status_code == 200, response.text
    dashboard = client.get(f"/api/v1/territories/{yard['id']}/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["reading"]["timestamp"].endswith("Z")
    readings = client.get(f"/api/v1/territories/{yard['id']}/sensors/readings")
    assert readings.status_code == 200
    assert len(readings.json()) == 1


def test_device_contract_requires_owner_issued_key(client):
    register(client)
    yard = territory(client)
    issued = client.post(f"/api/v1/territories/{yard['id']}/sensors/device-credential")
    assert issued.status_code == 200
    payload = {
        "sensor_id": issued.json()["sensor_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "device",
        "air_temperature_c": 25,
        "air_humidity_pct": 50,
        "soil_moisture_pct": 31,
        "light_lux": 1000,
        "quality": "valid",
        "raw_metadata": {"firmware": "0.1.0"},
    }
    denied = client.post("/api/v1/devices/telemetry", json=payload)
    assert denied.status_code == 401
    accepted = client.post(
        "/api/v1/devices/telemetry",
        json=payload,
        headers={"Authorization": f"Bearer {issued.json()['api_key']}"},
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["source"] == "device"
