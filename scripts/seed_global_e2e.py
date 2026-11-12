"""Test-only chief in the explicitly isolated browser-test database."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from gaia.config import SessionLocal, engine, settings  # noqa: E402
from gaia import models as m, security  # noqa: E402
from sqlalchemy import select  # noqa: E402

if (
    engine.dialect.name != "sqlite"
    or Path(engine.url.database).resolve() != ROOT / "data/gaia_e2e.db"
    or settings.web_origin != "http://localhost:5174"
):
    raise SystemExit("Refusing to create test credentials outside the isolated E2E database")

with SessionLocal() as db:
    user = db.scalar(select(m.User).where(m.User.email == "chief-e2e@example.com"))
    other_chief = db.scalar(
        select(m.User).where(m.User.role == "superadmin", m.User.email != "chief-e2e@example.com")
    )
    if other_chief:
        raise SystemExit("Unexpected chief in test database; refusing to modify roles")
    if not user:
        user = m.User(
            name="E2E Chief",
            email="chief-e2e@example.com",
            nickname="E2EChief",
            nickname_key="e2echief",
            role="superadmin",
            password_hash=security.hasher.hash("test-only-global-123"),
        )
        db.add(user)
        db.commit()
print("Isolated Global browser-test account ready")
