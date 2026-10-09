import hashlib
import secrets
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request, Response
from sqlalchemy import select, delete, func
from . import models as m
from .config import utcnow, aware, settings

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("not-a-user-password")
COOKIE = "gaia_session"


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request, db):
    token = request.cookies.get(COOKIE)
    session = (
        db.scalar(select(m.AuthSession).where(m.AuthSession.token_hash == digest(token))) if token else None
    )
    if not session or aware(session.expires_at) <= utcnow():
        raise HTTPException(401, "Войдите в аккаунт")
    return db.get(m.User, session.user_id)


def login_session(db, user, response: Response):
    token = secrets.token_urlsafe(48)
    db.add(
        m.AuthSession(
            user_id=user.id,
            token_hash=digest(token),
            expires_at=utcnow() + timedelta(days=settings.session_days),
        )
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.session_days * 86400,
        path="/",
    )


def rate_limit(db, request, email):
    # Both per-IP and per-account buckets are persisted; single-process mutations are serialized.
    keys = [digest("ip:" + (request.client.host if request.client else "unknown")), digest("email:" + email)]
    cutoff = utcnow() - timedelta(minutes=15)
    db.execute(delete(m.LoginAttempt).where(m.LoginAttempt.timestamp < cutoff))
    for key in keys:
        count = db.scalar(select(func.count()).select_from(m.LoginAttempt).where(m.LoginAttempt.key == key))
        if count >= 15:
            db.commit()
            raise HTTPException(429, "Слишком много попыток. Повторите через 15 минут.")
    for key in keys:
        db.add(m.LoginAttempt(key=key))
    db.commit()


def verify(password, stored):
    try:
        return hasher.verify(stored, password)
    except VerificationError:
        return False
