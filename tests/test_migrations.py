"""Exercise real Alembic upgrades on isolated populated SQLite databases."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from gaia import models as m
from gaia.config import utcnow

ROOT = Path(__file__).resolve().parents[1]


def run_migration(path, *args, code=None, success=True):
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + path.as_posix(), "PYTHONPATH": str(ROOT / "apps/api")}
    cmd = [sys.executable, "-c", code] if code else [sys.executable, "-m", "alembic", *args]
    result = subprocess.run(cmd, env=env, cwd=ROOT, capture_output=True, text=True)
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
    return result


def snapshot(path):
    with sqlite3.connect(path) as db:
        names = [
            r[0]
            for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if r[0] != "alembic_version"
        ]
        result = {}
        for name in names:
            columns = [
                r[1]
                for r in db.execute(f'PRAGMA table_info("{name}")')
                if name != "users" or r[1] not in ("nickname", "nickname_key", "role", "email_verified_at")
            ]
            projection = ",".join('"' + column + '"' for column in columns)
            result[name] = sorted(db.execute(f'SELECT {projection} FROM "{name}"').fetchall(), key=repr)
        return result


def legacy_database(path):
    run_migration(path, "upgrade", "10f579997c3a")
    engine = create_engine("sqlite:///" + path.as_posix())
    with Session(engine) as db:
        user = m.User(
            id=m.uid(), name="Migration", email="migration@example.com", password_hash="test-only-hash"
        )
        # This fixture is intentionally pre-nickname schema; do not insert using the latest ORM columns.
        db.execute(
            text(
                "INSERT INTO users (id,name,email,password_hash,created_at) VALUES (:id,:name,:email,:password,:created)"
            ),
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "password": user.password_hash,
                "created": utcnow().isoformat(),
            },
        )
        yard = m.Territory(owner_id=user.id, name="Старая территория", latitude=43, longitude=76)
        db.add(yard)
        db.flush()
        sensors = [
            m.Sensor(
                territory_id=yard.id,
                source=source,
                credential_hash="test-hash" if source == "device" else None,
            )
            for source in ("simulated", "device")
        ]
        db.add_all(sensors)
        db.flush()
        for sensor in sensors:
            db.add(
                m.SensorReading(
                    territory_id=yard.id,
                    sensor_id=sensor.id,
                    source=sensor.source,
                    timestamp=utcnow(),
                    soil_moisture_pct=27,
                )
            )
        db.add(m.SimulationSession(territory_id=yard.id, seed=79, tick_index=17, total_water_l=19))
        db.add(m.IrrigationZone(territory_id=yard.id, emergency=True, stopped_at=utcnow(), daily_water_l=7))
        db.add(m.IrrigationRule(territory_id=yard.id, cooldown_s=1111))
        db.add(
            m.IrrigationEvent(
                territory_id=yard.id,
                timestamp=utcnow(),
                mode="manual",
                action="stop",
                reason="История",
                actor="user",
                target_value=45,
            )
        )
        db.add(
            m.Observation(
                territory_id=yard.id,
                category="soil",
                latitude=43,
                longitude=76,
                severity="warning",
                text="История",
                timestamp=utcnow(),
            )
        )
        db.add(
            m.Alert(
                territory_id=yard.id,
                code="old",
                created_at=utcnow(),
                severity="warning",
                title="История",
                explanation="Тест",
                recommendation="Тест",
            )
        )
        db.add(
            m.DailyReport(
                territory_id=yard.id, period_start=utcnow(), period_end=utcnow(), data={"test": True}
            )
        )
        db.commit()
    engine.dispose()


def test_populated_upgrade_preserves_every_legacy_row(tmp_path):
    path = tmp_path / "populated.db"
    legacy_database(path)
    before = snapshot(path)
    run_migration(path, "upgrade", "head")
    after = snapshot(path)
    assert all(after[name] == rows for name, rows in before.items())
    assert len(after["zones"]) == 1
    assert len(after["devices"]) == 3
    assert len(after["sensor_channels"]) == 12
    with sqlite3.connect(path) as db:
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        assert (
            db.execute(
                "SELECT COUNT(*) FROM devices d JOIN sensors s ON s.id=d.legacy_sensor_id WHERE s.territory_id!=d.territory_id"
            ).fetchone()[0]
            == 0
        )
    run_migration(path, "upgrade", "head")
    assert snapshot(path) == after
    run_migration(path, "check")


def test_failed_backfill_rolls_back_schema_and_history(tmp_path):
    path = tmp_path / "rollback.db"
    legacy_database(path)
    before = snapshot(path)
    code = """
from alembic import command
from alembic.config import Config
from alembic.operations import Operations
original = Operations.execute
def fail_after_first_channel(self, sql, *args, **kwargs):
    result = original(self, sql, *args, **kwargs)
    if "INSERT INTO sensor_channels" in str(sql):
        raise RuntimeError("intentional migration failure")
    return result
Operations.execute = fail_after_first_channel
command.upgrade(Config("alembic.ini"), "head")
"""
    result = run_migration(path, code=code, success=False)
    assert "intentional migration failure" in result.stderr
    assert snapshot(path) == before
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "10f579997c3a"
    run_migration(path, "upgrade", "head")


def test_fresh_upgrade_has_no_model_drift(tmp_path):
    path = tmp_path / "fresh.db"
    run_migration(path, "upgrade", "head")
    run_migration(path, "check")
