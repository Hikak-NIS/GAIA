from datetime import timedelta
from sqlalchemy import select
from conftest import register, territory
from gaia import models as m, foundation_models as f, domain
from gaia.config import SessionLocal, utcnow


def inventory(client):
    register(client)
    yard = territory(client)
    tid = yard["id"]
    zone = client.get(f"/api/v1/territories/{tid}/zones").json()[0]
    return tid, zone["id"]


def station(client, tid, zid, name="Станция"):
    response = client.post(f"/api/v1/territories/{tid}/devices", json={"name": name, "zone_id": zid})
    assert response.status_code == 201, response.text
    return response.json()


def profile(client):
    response = client.post(
        "/api/v1/plant-profiles",
        json={
            "common_name": "Тестовая культура",
            "soil_moisture_min": 20,
            "soil_moisture_max": 50,
            "stage_requirements": {"flowering": {"soil_moisture_min": 30, "soil_moisture_max": 60}},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def plant(client, tid, zid, pid, channels=None, camera=None):
    response = client.post(
        f"/api/v1/territories/{tid}/plants",
        json={
            "name": "Растение 1",
            "zone_id": zid,
            "profile_id": pid,
            "growth_stage": "flowering",
            "sensor_channel_ids": channels or [],
            "camera_device_id": camera,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def key_for(client, device):
    response = client.post(f"/api/v1/devices/{device['id']}/credential")
    assert response.status_code == 200, response.text
    assert "credential_hash" not in response.text
    return response.json()["api_key"]


def send(client, device, key, **fields):
    return client.post(
        "/api/v1/devices/telemetry",
        headers={"Authorization": "Bearer " + key},
        json={
            "sensor_id": device["sensor_id"],
            "source": "device",
            "timestamp": utcnow().isoformat(),
            "soil_moisture_pct": 12,
            "air_temperature_c": 25,
            **fields,
        },
    )


def test_foundation_defaults_and_multiple_stations(client):
    tid, zid = inventory(client)
    devices = client.get(f"/api/v1/territories/{tid}/devices").json()
    assert len(devices) == 2
    assert {d["device_type"] for d in devices} == {"SENSOR", "ACTUATOR"}
    assert all(d["source"] == "SIMULATED" and d["status"] == "SIMULATED" for d in devices)
    assert len(next(d for d in devices if d["device_type"] == "SENSOR")["channels"]) == 6
    a, b = station(client, tid, zid), station(client, tid, zid, "Вторая")
    assert a["sensor_id"] != b["sensor_id"]
    assert a["status"] == "OFFLINE"
    assert client.post(f"/api/v1/territories/{tid}/sensors/device-credential").status_code == 409
    assert (
        client.post(
            f"/api/v1/territories/{tid}/devices",
            json={"name": "Другой симулятор", "zone_id": zid, "source": "SIMULATED"},
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/zones/{zid}").status_code == 409


def test_profile_ranges_and_stage_validation(client):
    inventory(client)
    for extra in (
        {"soil_moisture_min": 50, "soil_moisture_max": 10},
        {"ph_min": 4},
        {"stage_requirements": {"unknown": {}}},
        {"stage_requirements": {"flowering": {"ph_min": 9, "ph_max": 2}}},
        {"common_diseases": ["x" * 201]},
        {"owner_id": "spoof"},
    ):
        assert (
            client.post("/api/v1/plant-profiles", json={"common_name": "Культура", **extra}).status_code
            == 422
        )
    assert client.post("/api/v1/plant-profiles", json={"common_name": "   "}).status_code == 422


def test_real_telemetry_never_changes_virtual_control_and_reports(client):
    tid, zid = inventory(client)
    with SessionLocal() as db:
        sim = domain.one(db, m.SimulationSession, tid)
        sim.clock = utcnow() + timedelta(days=1)
        sim.status = "running"
        domain.tick(db, tid)
        db.commit()
    before = client.get(f"/api/v1/territories/{tid}/dashboard").json()
    a, b = station(client, tid, zid), station(client, tid, zid, "Вторая")
    ka, kb = key_for(client, a), key_for(client, b)
    assert send(client, a, ka).status_code == 201
    assert send(client, b, kb, quality="invalid", soil_moisture_pct=None).status_code == 201
    after = client.get(f"/api/v1/territories/{tid}/dashboard").json()
    for field in ("simulation", "zone", "reading", "alerts", "rule"):
        assert before[field] == after[field]
    default_rows = client.get(f"/api/v1/territories/{tid}/sensors/readings").json()
    assert len(default_rows) == 1 and default_rows[0]["source"] == "simulated"
    real_rows = client.get(
        f"/api/v1/territories/{tid}/sensors/readings?source=device&sensor_id={a['sensor_id']}"
    ).json()
    assert len(real_rows) == 1 and real_rows[0]["sensor_id"] == a["sensor_id"]
    assert client.get(f"/api/v1/territories/{tid}/sensors/readings?source=unknown").status_code == 422
    report = client.post(f"/api/v1/territories/{tid}/reports").json()
    assert report["data"]["sources"] == ["simulated"]
    assert client.get(f"/api/v1/devices/{a['id']}").json()["status"] == "ONLINE"
    assert client.get(f"/api/v1/devices/{b['id']}").json()["status"] == "ERROR"


def test_device_auth_rotation_replay_and_revocation(client):
    tid, zid = inventory(client)
    a, b = station(client, tid, zid), station(client, tid, zid)
    ka, kb = key_for(client, a), key_for(client, b)
    assert send(client, b, ka).status_code == 401
    assert send(client, a, ka, source="simulated").status_code == 422
    assert send(client, a, ka, timestamp=(utcnow() - timedelta(hours=1)).isoformat()).status_code == 422
    timestamp = utcnow().isoformat()
    assert send(client, a, ka, timestamp=timestamp).status_code == 201
    assert send(client, a, ka, timestamp=timestamp).status_code == 409
    knew = key_for(client, a)
    assert send(client, a, ka).status_code == 401
    assert send(client, a, knew).status_code == 201
    assert send(client, b, kb).status_code == 201
    body = {"name": a["name"], "zone_id": zid, "active": False}
    assert client.put(f"/api/v1/devices/{a['id']}", json=body).status_code == 200
    assert send(client, a, knew).status_code == 401
    assert client.get(f"/api/v1/devices/{a['id']}/readings").json()
    assert client.put(f"/api/v1/devices/{b['id']}", json={**body, "source": "SIMULATED"}).status_code == 422
    assert "credential_hash" not in client.get(f"/api/v1/devices/{a['id']}").text


def test_plant_reads_only_linked_channels_and_marks_stale(client):
    tid, zid = inventory(client)
    a, b = station(client, tid, zid), station(client, tid, zid)
    soil = next(c for c in a["channels"] if c["sensor_type"] == "soil_moisture_pct")
    p = profile(client)
    planted = plant(client, tid, zid, p["id"], [soil["id"]])
    empty = plant(client, tid, zid, p["id"])
    assert send(client, a, key_for(client, a), soil_moisture_pct=11).status_code == 201
    assert send(client, b, key_for(client, b), soil_moisture_pct=88).status_code == 201
    result = client.get(f"/api/v1/plants/{planted['id']}/readings").json()
    assert result["health_status"] == "UNKNOWN"
    assert result["effective_requirements"]["soil_moisture_min"] == 30
    assert len(result["channels"]) == len(result["history"]) == 1
    assert result["channels"][0]["current_value"] == 11
    assert result["channels"][0]["availability"] == "CURRENT"
    assert result["history"][0]["availability"] == "HISTORICAL"
    assert not client.get(f"/api/v1/plants/{empty['id']}/readings").json()["history"]
    assert not client.get(f"/api/v1/plants/{planted['id']}/readings?source=SIMULATED").json()["history"]
    with SessionLocal() as db:
        row = db.scalar(select(m.SensorReading).where(m.SensorReading.sensor_id == a["sensor_id"]))
        row.received_at = utcnow() - timedelta(minutes=10)
        db.commit()
    assert (
        client.get(f"/api/v1/plants/{planted['id']}/readings").json()["channels"][0]["availability"]
        == "STALE"
    )
    client.put(f"/api/v1/devices/{a['id']}", json={"name": a["name"], "zone_id": zid, "active": False})
    result = client.get(f"/api/v1/plants/{planted['id']}/readings").json()
    assert result["channels"][0]["availability"] == "DISABLED"
    assert result["history"][0]["quality"] == "valid"


def test_ownership_links_transfers_and_cascade(client):
    tid, zid = inventory(client)
    second_tid = territory(client, name="Вторая территория")["id"]
    second_zone = client.get(f"/api/v1/territories/{second_tid}/zones").json()[0]["id"]
    a = station(client, tid, zid)
    p = profile(client)
    base = {"name": "Растение", "profile_id": p["id"], "zone_id": zid}
    assert (
        client.post(f"/api/v1/territories/{tid}/plants", json={**base, "zone_id": second_zone}).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/territories/{second_tid}/plants",
            json={**base, "zone_id": second_zone, "sensor_channel_ids": [a["channels"][0]["id"]]},
        ).status_code
        == 422
    )
    camera = client.post(
        f"/api/v1/territories/{tid}/devices", json={"name": "Камера", "zone_id": zid, "device_type": "CAMERA"}
    ).json()
    planted = plant(client, tid, zid, p["id"], [a["channels"][0]["id"]], camera["id"])
    extra_zone = client.post(f"/api/v1/territories/{tid}/zones", json={"name": "Грядка"}).json()
    assert (
        client.put(
            f"/api/v1/devices/{a['id']}", json={"name": "Перенос", "zone_id": extra_zone["id"]}
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/plant-profiles/{p['id']}").status_code == 409
    client.post("/api/v1/auth/logout")
    register(client, email="other@example.com")
    for path in (
        f"zones/{zid}",
        f"devices/{a['id']}",
        f"plants/{planted['id']}",
        f"plants/{planted['id']}/readings",
        f"plant-profiles/{p['id']}",
    ):
        assert client.get("/api/v1/" + path).status_code == 404
    client.post("/api/v1/auth/logout")
    assert (
        client.put(f"/api/v1/sensor-channels/{a['channels'][0]['id']}/calibration", json={}).status_code
        == 401
    )
    assert client.put("/api/v1/sensor-channels/nonexistent/calibration", json={}).status_code == 401
    from conftest import login
    login(client, "anna@example.com")
    response = client.delete(f"/api/v1/territories/{tid}")
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        assert db.get(f.PlantInstance, planted["id"]) is None
        assert db.get(f.Device, a["id"]) is None
        assert db.get(f.Zone, zid) is None
