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
    user = db.get(m.User, session.user_id)
    if not user or user.email_verified_at is None:
        raise HTTPException(401, "Войдите в аккаунт")
    return user


def email_challenge(db, user):
    from .services.mail import send_code
    challenge_id = m.uid()
    code = f"{secrets.randbelow(1_000_000):06d}"
    send_code(user.email, code)
    # A successfully sent replacement invalidates previous challenges for this account.
    db.query(m.EmailChallenge).filter_by(user_id=user.id, consumed=False).update({"consumed": True})
    db.add(m.EmailChallenge(id=challenge_id, user_id=user.id, code_hash=digest(challenge_id + code),
                          expires_at=utcnow() + timedelta(minutes=10)))
    db.commit()
    local, domain = user.email.split("@", 1)
    return {"challenge_id": challenge_id, "email_hint": local[:2] + "***@" + domain,
            "expires_in": 600, "verification_required": True}


def admin_user(request: Request, db):
    user = current_user(request, db)
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "GAIA Global доступен только администраторам")
    return user


def superadmin_user(request: Request, db):
    user = current_user(request, db)
    if user.role != "superadmin":
        raise HTTPException(403, "Управлять доступом может только главный администратор")
    return user


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
    db.execute(delete(m.LoginAttempt).where(m.LoginAttempt.timestamp < cutoff, m.LoginAttempt.key.in_(keys)))
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
