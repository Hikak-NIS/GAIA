from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select, func, or_
from ... import models as m, global_models as g, global_schemas as s, security
from ...schemas import UserOut, Message
from ...config import utcnow, settings
from ...global_data import PROVIDERS
from ...global_data.base import ProviderUnavailable
from ...services.global_analysis import evaluate
from ..dependencies import DB

router = APIRouter(prefix="/api/v1", tags=["GAIA Global"])


def config(db):
    row = db.get(g.GlobalSettings, 1)
    if row is None:
        row = g.GlobalSettings(id=1, weights=s.Weights().model_dump(), revision=1)
        db.add(row)
        db.flush()
    return row


@router.get("/global/providers")
def providers(request: Request, db=DB):
    security.admin_user(request, db)
    return [provider.describe() for provider in PROVIDERS.values()]


@router.get("/global/settings")
def settings_get(request: Request, db=DB):
    security.admin_user(request, db)
    row = config(db)
    db.commit()
    return {"weights": row.weights, "revision": row.revision}


@router.put("/global/settings")
def settings_update(body: s.WeightsUpdate, request: Request, db=DB):
    actor = security.superadmin_user(request, db)
    row = config(db)
    if row.revision != body.expected_revision:
        raise HTTPException(409, "Веса уже изменены. Обновите страницу перед сохранением.")
    previous = row.weights
    row.weights = body.weights.model_dump()
    row.revision += 1
    db.add(
        g.AdminAudit(
            actor_id=actor.id,
            action="weights_changed",
            details={"previous": previous, "weights": row.weights, "revision": row.revision},
        )
    )
    db.commit()
    return {"weights": row.weights, "revision": row.revision}


@router.post("/global/analyses", status_code=201)
def analyze(body: s.AnalysisIn, request: Request, db=DB):
    user = security.admin_user(request, db)
    if not settings.legacy_simulation_enabled:
        raise HTTPException(410, "Используйте /api/v1/earth/analyses для анализа наблюдений")
    provider = PROVIDERS[body.source]
    try:
        observation = provider.fetch(body.area, body.scenario, utcnow().date())
    except ProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    model_settings = config(db)
    result = evaluate(observation, s.Weights.model_validate(model_settings.weights), model_settings.revision)
    result.update(area=body.area.model_dump(), scenario=body.scenario, source=body.source)
    row = g.GlobalAnalysis(
        creator_id=user.id,
        name=body.area.name,
        latitude=body.area.latitude,
        longitude=body.area.longitude,
        source=body.source,
        result=result,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "created_at": row.created_at, **result}


@router.get("/global/analyses", response_model=list[s.AnalysisSummary])
def history(request: Request, limit: int = Query(30, ge=1, le=100), db=DB):
    security.admin_user(request, db)
    query = select(g.GlobalAnalysis)
    if not settings.legacy_simulation_enabled:
        query = query.where(g.GlobalAnalysis.source == "observations")
    return list(
        db.scalars(query.order_by(g.GlobalAnalysis.created_at.desc()).limit(limit))
    )


@router.get("/global/analyses/{aid}")
def analysis_get(aid: str, request: Request, db=DB):
    security.admin_user(request, db)
    row = db.get(g.GlobalAnalysis, aid)
    if row is None:
        raise HTTPException(404, "Анализ не найден")
    if row.source != "observations" and not settings.legacy_simulation_enabled:
        raise HTTPException(410, "Этот результат относится к архивному режиму. Создайте анализ наблюдений.")
    return {"id": row.id, "created_at": row.created_at, **row.result}


@router.get("/global/markers", response_model=list[s.MarkerOut])
def markers(request: Request, db=DB):
    security.admin_user(request, db)
    return list(db.scalars(select(g.GlobalMarker).order_by(g.GlobalMarker.created_at.desc()).limit(200)))


@router.post("/global/markers", response_model=s.MarkerOut, status_code=201)
def marker_add(body: s.MarkerIn, request: Request, db=DB):
    user = security.admin_user(request, db)
    row = g.GlobalMarker(creator_id=user.id, **body.model_dump())
    db.add(row)
    db.commit()
    return row


@router.delete("/global/markers/{mid}", response_model=Message)
def marker_delete(mid: str, request: Request, db=DB):
    user = security.admin_user(request, db)
    row = db.get(g.GlobalMarker, mid)
    if not row:
        raise HTTPException(404, "Маркер не найден")
    if row.creator_id != user.id and user.role != "superadmin":
        raise HTTPException(403, "Удалить маркер может его автор или главный администратор")
    db.delete(row)
    db.commit()
    return {"message": "Маркер удалён"}


@router.get("/admin/users")
def users(
    request: Request,
    q: str = Query("", max_length=254),
    page: int = Query(1, ge=1),
    administrators_only: bool = False,
    db=DB,
):
    security.superadmin_user(request, db)
    query = select(m.User)
    if q.strip():
        term = q.strip().lower()
        query = query.where(
            or_(
                m.User.nickname_key.contains(term, autoescape=True),
                func.lower(m.User.email).contains(term, autoescape=True),
                func.lower(m.User.name).contains(term, autoescape=True),
            )
        )
    if administrators_only:
        query = query.where(m.User.role.in_(["admin", "superadmin"]))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(m.User.nickname_key, m.User.id).offset((page - 1) * 25).limit(25))
    return {
        "items": [UserOut.model_validate(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": 25,
    }


@router.put("/admin/users/{uid}/role", response_model=UserOut)
def role_update(uid: str, body: s.RoleUpdate, request: Request, db=DB):
    actor = security.superadmin_user(request, db)
    user = db.get(m.User, uid)
    if not user:
        raise HTTPException(404, "Аккаунт не найден")
    if user.role == "superadmin":
        raise HTTPException(409, "Роль главного администратора защищена от изменения")
    if user.role != body.role:
        previous = user.role
        user.role = body.role
        db.add(
            g.AdminAudit(
                actor_id=actor.id,
                target_id=user.id,
                action="role_changed",
                details={"previous": previous, "role": body.role},
            )
        )
        # Existing sessions remain usable for the garden; access is checked against DB on every request.
        db.commit()
    return user


@router.get("/admin/audit")
def audit(request: Request, db=DB):
    security.superadmin_user(request, db)
    rows = db.scalars(select(g.AdminAudit).order_by(g.AdminAudit.created_at.desc()).limit(100))
    return [
        {
            "id": row.id,
            "actor": db.get(m.User, row.actor_id).nickname,
            "target": db.get(m.User, row.target_id).nickname if row.target_id else None,
            "action": row.action,
            "details": row.details,
            "created_at": row.created_at,
        }
        for row in rows
    ]
