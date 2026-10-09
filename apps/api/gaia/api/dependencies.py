from fastapi import Depends, HTTPException
from .. import domain, models, security
from ..config import SessionLocal


def db_session():
    with domain.LOCK, SessionLocal() as db:
        yield db


DB = Depends(db_session)


def owner(request, db, territory_id):
    user = security.current_user(request, db)
    territory = db.get(models.Territory, territory_id)
    if not territory or territory.owner_id != user.id:
        raise HTTPException(404, "Территория не найдена")
    return territory
