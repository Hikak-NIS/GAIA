"""Back up and verify a local GAIA SQLite upgrade. Stop the API first."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from gaia.config import engine  # noqa: E402


def snapshot(path):
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        names = [
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if row[0] != "alembic_version"
        ]
        return {
            name: sorted(db.execute('SELECT * FROM "' + name.replace('"', '""') + '"').fetchall(), key=repr)
            for name in names
        }


def migrate(path):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "apps/api"), "DATABASE_URL": "sqlite:///" + path.as_posix()}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True)
    subprocess.run([sys.executable, "-m", "alembic", "check"], cwd=ROOT, env=env, check=True)
    with sqlite3.connect(path) as db:
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Foreign key check failed")


def main():
    if engine.dialect.name != "sqlite":
        raise SystemExit("This helper is only for a local SQLite database")
    path = Path(engine.url.database).resolve()
    if not path.is_relative_to(ROOT / "data") or not path.is_file():
        raise SystemExit("Expected an existing SQLite database inside this project's data directory")
    engine.dispose()
    backup_dir = ROOT / "data" / "backups"
    backup_dir.mkdir(exist_ok=True)
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = backup_dir / f"{path.stem}-before-phase1-{suffix}.db"
    trial = backup_dir / f"{path.stem}-upgrade-trial-{suffix}.db"
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as source:
        with sqlite3.connect(backup) as destination:
            source.backup(destination)
        with sqlite3.connect(trial) as destination:
            source.backup(destination)
    original = snapshot(backup)
    if snapshot(path) != original:
        raise RuntimeError("Database changed during backup. Stop the API and retry")
    migrate(trial)
    trial_rows = snapshot(trial)
    if any(trial_rows.get(name) != rows for name, rows in original.items()):
        raise RuntimeError("Trial upgrade changed existing data. Original database was not migrated")
    # The source must remain stopped; refuse to overwrite concurrent changes.
    if snapshot(path) != original:
        raise RuntimeError("Source database changed during trial. Original was not migrated")
    migrate(path)
    actual = snapshot(path)
    if any(actual.get(name) != rows for name, rows in original.items()):
        raise RuntimeError(f"Existing data differs after upgrade. Preserved backup: {backup}")
    print(
        json.dumps(
            {
                "database": str(path),
                "backup": str(backup),
                "verified_trial": str(trial),
                "preserved_tables": len(original),
                "preserved_rows": sum(map(len, original.values())),
                "result": "all existing rows preserved",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
