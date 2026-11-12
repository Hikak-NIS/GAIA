from datetime import timedelta
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from sqlalchemy import select, func, delete
from ... import security, models as m, global_models as g, earth_schemas as s, domain
from ...config import SessionLocal, settings, utcnow
from ...services import (
    earth_sources,
    environment,
    earth_analysis,
    planet,
    copernicus_live,
    gee_live,
    assistant,
)
from ...services.organizations import ORGANIZATIONS
from ...services.remote import cached, fetch
from ...services import eco_model
from ...global_schemas import Input
from pydantic import Field
from typing import Literal

router = APIRouter(prefix="/api/v1", tags=["Earth observations"])


def read_db():
    with SessionLocal() as db:
        yield db


DB = Depends(read_db)


def quota(user, kind, limit=20):
    # Durable per-account limit shared by aliases. No external I/O while holding the write lock.
    with domain.LOCK, SessionLocal() as db:
        key = security.digest(f"usage:{kind}:{user.id}")
        cutoff = utcnow() - timedelta(hours=1)
        db.execute(delete(m.LoginAttempt).where(m.LoginAttempt.key == key, m.LoginAttempt.timestamp < cutoff))
        count = db.scalar(select(func.count()).select_from(m.LoginAttempt).where(m.LoginAttempt.key == key))
        if count >= limit:
            raise HTTPException(429, "Часовой лимит запросов исчерпан. Повторите позже.")
        db.add(m.LoginAttempt(key=key))
        db.commit()


@router.get("/earth/layers")
def layers(request: Request, db=DB):
    security.current_user(request, db)
    try:
        return earth_sources.layers()
    except Exception as exc:
        raise HTTPException(502, "Каталог спутниковых слоёв NASA временно недоступен") from exc


@router.get("/earth/planet")
def earth_overview(request: Request, db=DB):
    security.admin_user(request, db)
    return planet.overview()


@router.get("/earth/ocean-overview")
def ocean_overview(request: Request, db=DB):
    security.admin_user(request, db)
    from ...services.remote import gather

    points = [
        ("north-atlantic", "Северная Атлантика", 40, -40),
        ("pacific", "Тихий океан", 0, -140),
        ("indian", "Индийский океан", -20, 80),
    ]
    return {
        "points": [
            {"id": key, "name": name, "latitude": lat, "longitude": lon} for key, name, lat, lon in points
        ],
        "sources": gather(
            {
                key: lambda lat=lat, lon=lon: environment.environment(lat, lon, "marine")
                for key, _, lat, lon in points
            }
        ),
        "note": "Три опорные точки морской модели, не среднее состояние мирового океана.",
    }


@router.get("/earth/models")
def models(request: Request, db=DB):
    security.admin_user(request, db)
    return {"items": [eco_model.describe(kind) for kind in eco_model.FEATURES]}


class PredictionIn(Input):
    kind: Literal["land", "microplastics"]
    features: dict[str, float] = Field(max_length=10)


@router.post("/earth/models/predict")
def prediction(body: PredictionIn, request: Request, db=DB):
    security.admin_user(request, db)
    try:
        return eco_model.predict(body.kind, body.features)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/earth/events")
def events(request: Request, db=DB):
    security.admin_user(request, db)
    try:
        return earth_sources.events()
    except Exception as exc:
        raise HTTPException(502, "NASA EONET временно недоступен") from exc


@router.get("/earth/organizations")
def organizations(request: Request, db=DB):
    security.admin_user(request, db)
    return {
        "items": ORGANIZATIONS,
        "note": "Открытый справочник организаций. Партнёрство с GAIA не заявляется. Точки обозначают города размещения, не точный вход в здание.",
    }


@router.post("/earth/analyses", status_code=201)
def analyze(body: s.EarthAnalysisIn, request: Request, db=DB):
    user = security.admin_user(request, db)
    quota(user, "earth", 30)
    result = earth_analysis.analyze(body)
    # Recheck the role after potentially slow remote I/O.
    db.expire_all()
    security.admin_user(request, db)
    row = g.GlobalAnalysis(
        creator_id=user.id,
        name=body.area.name,
        latitude=body.area.latitude,
        longitude=body.area.longitude,
        source="observations",
        result=result,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "created_at": row.created_at, **result}


@router.post("/earth/satellite-image")
def satellite_image(body: s.EarthAnalysisIn, request: Request, db=DB):
    user = security.admin_user(request, db)
    quota(user, "image", 30)
    try:
        return Response(copernicus_live.image(body.area, body.start, body.end), media_type="image/png")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Sentinel Hub не вернул снимок. Проверьте доступ, период и квоту.") from exc


@router.get("/earth/forest-map")
def forest_map(request: Request, db=DB):
    user = security.admin_user(request, db)
    quota(user, "forest-map", 30)
    try:
        return cached("forest-map", gee_live.forest_map, 1800)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            502, "Не удалось получить карту Earth Engine. Проверьте подключение проекта."
        ) from exc


@router.get("/earth/fires")
def fires(request: Request, db=DB):
    security.admin_user(request, db)
    if not settings.firms_map_key:
        raise HTTPException(
            503,
            "Для точек FIRMS добавьте FIRMS_MAP_KEY в .env. События EONET и спутниковые слои доступны отдельно.",
        )

    def load():
        text = fetch(
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{settings.firms_map_key}/VIIRS_SNPP_NRT/world/1",
            as_text=True,
        )
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "latitude" not in reader.fieldnames:
            raise ValueError("Invalid FIRMS response")
        rows = list(reader)
        return {
            "items": [
                {
                    "latitude": float(r["latitude"]),
                    "longitude": float(r["longitude"]),
                    "date": r["acq_date"],
                    "confidence": r.get("confidence"),
                    "frp": r.get("frp"),
                }
                for r in rows[:3000]
            ],
            "total": len(rows),
            "source": "NASA FIRMS VIIRS SNPP NRT",
            "fetched_at": utcnow().isoformat(),
            "note": "Тепловые аномалии за сутки; не каждая точка является лесным пожаром. На карте до 3000 точек.",
        }

    try:
        return cached("firms", load, 900)
    except Exception as exc:
        raise HTTPException(502, "FIRMS недоступен. Проверьте ключ и квоту.") from exc


@router.get("/grow/territories/{tid}/environment")
def grow_environment(tid: str, request: Request, db=DB):
    user = security.current_user(request, db)
    territory = db.get(m.Territory, tid)
    if not territory or territory.owner_id != user.id:
        raise HTTPException(404, "Территория не найдена")
    return environment.local_environment(territory.latitude, territory.longitude)


@router.get("/integrations/status")
def integrations(request: Request, db=DB):
    user = security.current_user(request, db)
    basic = {
        "assistant": bool(settings.openai_api_key),
        "email": bool(settings.smtp_host and settings.smtp_from),
    }
    if user.role != "superadmin":
        return basic
    return {
        **basic,
        "config_path": "D:\\GAIA\\.env",
        "items": [
            {
                "name": "OpenAI · текст и голос",
                "configured": bool(settings.openai_api_key),
                "variables": [
                    "OPENAI_API_KEY",
                    "OPENAI_TEXT_MODEL",
                    "OPENAI_TRANSCRIBE_MODEL",
                    "OPENAI_SPEECH_MODEL",
                ],
                "url": "https://platform.openai.com/api-keys",
            },
            {
                "name": "SMTP · подтверждение email",
                "configured": bool(settings.smtp_host and settings.smtp_from),
                "variables": [
                    "SMTP_HOST",
                    "SMTP_PORT",
                    "SMTP_USERNAME",
                    "SMTP_PASSWORD",
                    "SMTP_FROM",
                    "SMTP_SECURITY",
                ],
                "url": "https://support.google.com/accounts/answer/185833",
            },
            {
                "name": "Copernicus · Sentinel Hub",
                "configured": copernicus_live.configured(),
                "variables": ["COPERNICUS_CLIENT_ID", "COPERNICUS_CLIENT_SECRET"],
                "url": "https://shapps.dataspace.copernicus.eu/dashboard/",
            },
            {
                "name": "NASA Earthdata · защищённые данные",
                "configured": bool(settings.earthdata_token),
                "variables": ["EARTHDATA_TOKEN"],
                "url": "https://urs.earthdata.nasa.gov/",
            },
            {
                "name": "NASA FIRMS · очаги пожаров",
                "configured": bool(settings.firms_map_key),
                "variables": ["FIRMS_MAP_KEY"],
                "url": "https://firms.modaps.eosdis.nasa.gov/api/",
            },
            {
                "name": "Google Earth Engine",
                "configured": gee_live.configured(),
                "variables": ["GEE_PROJECT", "GEE_SERVICE_ACCOUNT", "GEE_KEY_FILE"],
                "url": "https://console.cloud.google.com/earth-engine",
            },
            {
                "name": "Open-Meteo · коммерческий доступ",
                "configured": bool(settings.openmeteo_api_key),
                "variables": ["OPENMETEO_API_KEY"],
                "url": "https://open-meteo.com/en/pricing",
            },
        ],
        "note": "Наличие настройки не подтверждает действительность ключа. Ключи не передаются браузеру. GIBS, STAC, CMR, EONET, GISTEMP и NOAA доступны без ключа; Open-Meteo — в пределах условий бесплатного доступа.",
    }


@router.post("/assistant/chat")
def chat(body: s.AssistantIn, request: Request, db=DB):
    user = security.current_user(request, db)
    context = {}
    if body.analysis_id:
        security.admin_user(request, db)
        row = db.get(g.GlobalAnalysis, body.analysis_id)
        if not row or row.source != "observations":
            raise HTTPException(404, "Анализ наблюдений не найден")
        context = {
            key: row.result.get(key) for key in ("area", "period", "metrics", "assessment", "coverage_note")
        }
        context["metrics"] = [
            {k: v for k, v in metric.items() if k != "history"} for metric in context.get("metrics", [])
        ]
    if body.territory_id:
        territory = db.get(m.Territory, body.territory_id)
        if not territory or territory.owner_id != user.id:
            raise HTTPException(404, "Территория не найдена")
        context["territory"] = {
            "name": territory.name,
            "latitude": territory.latitude,
            "longitude": territory.longitude,
        }
    quota(user, "assistant", 30)
    return assistant.answer(body.question, context, [x.model_dump() for x in body.history])


@router.post("/assistant/transcribe")
def transcribe(request: Request, file: UploadFile = File(...), db=DB):
    user = security.current_user(request, db)
    quota(user, "voice", 30)
    allowed = {
        "audio/webm": "webm",
        "video/webm": "webm",
        "audio/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/ogg": "ogg",
    }
    mime = (file.content_type or "").split(";")[0]
    if mime not in allowed:
        raise HTTPException(415, "Поддерживаются webm, mp4, mp3, wav и ogg")
    content = file.file.read(8_000_001)
    if not content or len(content) > 8_000_000:
        raise HTTPException(413, "Аудиозапись должна быть меньше 8 МБ")
    data = assistant.call(
        "audio/transcriptions",
        files={"file": ("recording." + allowed[mime], content, mime)},
        data={"model": settings.openai_transcribe_model},
    ).json()
    return {"text": data.get("text", "")}


@router.post("/assistant/speech")
def speech(body: s.SpeechIn, request: Request, db=DB):
    user = security.current_user(request, db)
    quota(user, "voice", 30)
    response = assistant.call(
        "audio/speech",
        json={
            "model": settings.openai_speech_model,
            "voice": settings.openai_voice,
            "input": body.text,
            "response_format": "mp3",
        },
    )
    return Response(response.content, media_type="audio/mpeg")
