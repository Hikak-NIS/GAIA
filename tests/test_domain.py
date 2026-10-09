from datetime import timedelta

import pytest
from sqlalchemy import select

from gaia import domain as d
from gaia import models as m
from gaia.config import SessionLocal, utcnow
from gaia.schemas import Telemetry


def make_territory(db, name="Участок"):
    user = m.User(name="Тест", email=f"{name}@example.com", password_hash="unused")
    db.add(user)
    db.flush()
    territory = m.Territory(
        owner_id=user.id,
        name=name,
        latitude=43.2,
        longitude=76.9,
        area=100,
        timezone="Asia/Almaty",
    )
    db.add(territory)
    db.flush()
    sensor = m.Sensor(territory_id=territory.id)
    sim = m.SimulationSession(territory_id=territory.id, status="running", clock=utcnow())
    zone = m.IrrigationZone(territory_id=territory.id)
    rule = m.IrrigationRule(territory_id=territory.id)
    db.add_all([sensor, sim, zone, rule])
    db.flush()
    return territory, sensor, sim, zone, rule


def reading(db, territory, sensor, sim, soil=25, quality="valid"):
    return d.ingest(
        db,
        territory.id,
        Telemetry(
            sensor_id=sensor.id,
            timestamp=sim.clock,
            source="simulated",
            air_temperature_c=30,
            air_humidity_pct=30,
            soil_moisture_pct=soil if quality == "valid" else None,
            light_lux=50_000,
            quality=quality,
        ),
    )


def test_same_seed_is_deterministic_and_weather_changes_soil():
    with SessionLocal() as db:
        a = make_territory(db, "a")
        b = make_territory(db, "b")
        for territory, _sensor, sim, _zone, _rule in (a, b):
            sim.seed = 77
            sim.scenario = "drought"
            d.tick(db, territory.id, 60)
        assert a[2].soil == pytest.approx(b[2].soil)
        ar = d.latest(db, a[0].id)
        br = d.latest(db, b[0].id)
        assert ar.air_temperature_c == br.air_temperature_c
        assert ar.air_humidity_pct == br.air_humidity_pct

        before = a[2].soil
        a[2].scenario = "drought"
        d.tick(db, a[0].id, 60)
        assert a[2].soil < before
        before = a[2].soil
        a[2].scenario = "rain"
        d.tick(db, a[0].id, 60)
        assert a[2].soil > before


def test_automatic_irrigation_starts_grows_soil_and_stops_at_target():
    with SessionLocal() as db:
        territory, sensor, sim, zone, rule = make_territory(db)
        rule.mode, rule.trigger_pct, rule.target_pct = "automatic", 30, 45
        sim.scenario, sim.soil = "drought", 29
        d.tick(db, territory.id, 60)
        assert zone.pump_on
        assert db.scalar(select(m.IrrigationEvent).where(m.IrrigationEvent.action == "start"))
        low = sim.soil
        for _ in range(20):
            d.tick(db, territory.id, 60)
            if not zone.pump_on:
                break
        assert sim.soil > low
        assert not zone.pump_on
        stopped = db.scalar(
            select(m.IrrigationEvent)
            .where(m.IrrigationEvent.action == "stop")
            .order_by(m.IrrigationEvent.timestamp.desc())
        )
        assert stopped and ("целев" in stopped.reason or "длительност" in stopped.reason)
        assert stopped.estimated_water_l > 0
        assert sim.reservoir_l < 100


@pytest.mark.parametrize(
    ("guard", "reason"),
    [
        ("stale", "устарели"),
        ("empty", "Недостаточно воды"),
        ("cooldown", "cooldown"),
        ("limit", "дневной лимит"),
        ("emergency", "Аварийная"),
    ],
)
def test_manual_irrigation_safety_guards(guard, reason):
    with SessionLocal() as db:
        territory, sensor, sim, zone, rule = make_territory(db, guard)
        rule.mode = "manual"
        reading(db, territory, sensor, sim, soil=20)
        zone.pump_on = False
        if guard == "stale":
            current = d.latest(db, territory.id)
            current.timestamp = sim.clock - timedelta(minutes=10)
            current.received_at = utcnow() - timedelta(minutes=10)
        elif guard == "empty":
            sim.reservoir_l = rule.min_reservoir_l
        elif guard == "cooldown":
            zone.stopped_at = sim.clock
        elif guard == "limit":
            zone.daily_water_l = rule.daily_limit_l
            zone.water_day = sim.clock.astimezone().date().isoformat()
        elif guard == "emergency":
            zone.emergency = True
        result = d.evaluate(db, territory.id, manual=True)
        assert reason.lower() in result.lower()
        assert not zone.pump_on
        denied = db.scalar(select(m.IrrigationEvent).where(m.IrrigationEvent.action == "denied"))
        assert denied and reason.lower() in denied.reason.lower()


def test_sensor_failure_stops_running_pump_and_max_duration_stops():
    with SessionLocal() as db:
        territory, sensor, sim, zone, rule = make_territory(db)
        rule.mode = "manual"
        reading(db, territory, sensor, sim, soil=20)
        zone.pump_on = False
        assert d.evaluate(db, territory.id, manual=True, duration_s=60) is None
        assert zone.pump_on
        d.tick(db, territory.id, 60)
        assert not zone.pump_on

        zone.stopped_at = None
        sim.clock += timedelta(seconds=1)
        reading(db, territory, sensor, sim, soil=20)
        zone.pump_on = False
        assert d.evaluate(db, territory.id, manual=True) is None
        sim.scenario = "sensor_failure"
        d.tick(db, territory.id, 60)
        assert not zone.pump_on
        assert d.latest(db, territory.id).quality == "invalid"
