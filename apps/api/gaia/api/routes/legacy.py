import io
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from ...services import foundation
from ... import foundation_models as f
from ...foundation_schemas import DeviceIn
from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from ... import models as m, schemas as s, domain as d, security as sec
from ...config import utcnow, aware, ROOT
from ...weather import weather
from ..dependencies import DB, owner

router = APIRouter(tags=["Existing MVP"])


@router.get("/api/v1/health", response_model=s.Message)
def health():
    return {"message": "ok"}


@router.post("/api/v1/auth/register", response_model=s.UserOut, status_code=201)
def register(body: s.Register, request: Request, response: Response, db=DB):
    email = str(body.email).lower()
    sec.rate_limit(db, request, email)
    user = m.User(name=body.name.strip(), email=email, password_hash=sec.hasher.hash(body.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Этот email уже зарегистрирован") from exc
    sec.login_session(db, user, response)
    db.commit()
    return user


@router.post("/api/v1/auth/login", response_model=s.UserOut)
def login(body: s.Login, request: Request, response: Response, db=DB):
    email = str(body.email).lower()
    sec.rate_limit(db, request, email)
    user = db.scalar(select(m.User).where(m.User.email == email))
    valid = sec.verify(body.password, user.password_hash if user else sec.DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Неверный email или пароль")
    old = request.cookies.get(sec.COOKIE)
    if old:
        db.execute(delete(m.AuthSession).where(m.AuthSession.token_hash == sec.digest(old)))
    sec.login_session(db, user, response)
    db.commit()
    return user


@router.post("/api/v1/auth/logout", response_model=s.Message)
def logout(request: Request, response: Response, db=DB):
    token = request.cookies.get(sec.COOKIE)
    if token:
        db.execute(delete(m.AuthSession).where(m.AuthSession.token_hash == sec.digest(token)))
        db.commit()
    response.delete_cookie(sec.COOKIE, path="/")
    return {"message": "Вы вышли из аккаунта"}


@router.get("/api/v1/users/me", response_model=s.UserOut)
def me(request: Request, db=DB):
    return sec.current_user(request, db)


@router.get("/api/v1/territories", response_model=list[s.TerritoryOut])
def territories(request: Request, db=DB):
    user = sec.current_user(request, db)
    return list(
        db.scalars(
            select(m.Territory).where(m.Territory.owner_id == user.id).order_by(m.Territory.created_at.desc())
        )
    )


@router.post("/api/v1/territories", response_model=s.TerritoryOut, status_code=201)
def create_territory(body: s.TerritoryIn, request: Request, db=DB):
    user = sec.current_user(request, db)
    territory = m.Territory(owner_id=user.id, **body.model_dump())
    db.add(territory)
    db.flush()
    for model in (
        m.Sensor,
        m.SimulationSession,
        m.IrrigationZone,
        m.IrrigationRule,
        m.SatelliteLayerMetadata,
    ):
        db.add(model(territory_id=territory.id))
    db.flush()
    foundation.ensure_foundation(db, territory.id)
    db.commit()
    return territory


@router.get("/api/v1/territories/{tid}", response_model=s.TerritoryOut)
def territory_get(tid: str, request: Request, db=DB):
    return owner(request, db, tid)


@router.put("/api/v1/territories/{tid}", response_model=s.TerritoryOut)
def territory_update(tid: str, body: s.TerritoryIn, request: Request, db=DB):
    territory = owner(request, db, tid)
    for key, value in body.model_dump().items():
        setattr(territory, key, value)
    db.commit()
    return territory


@router.delete("/api/v1/territories/{tid}", response_model=s.Message)
def territory_delete(tid: str, request: Request, db=DB):
    territory = owner(request, db, tid)
    photos = list(
        db.scalars(
            select(m.Observation.photo_path).where(
                m.Observation.territory_id == tid, m.Observation.photo_path.is_not(None)
            )
        )
    )
    db.delete(territory)
    db.commit()
    for photo in photos:
        (ROOT / "data" / "uploads" / photo).unlink(missing_ok=True)
    return {"message": "Территория удалена"}


@router.get("/api/v1/territories/{tid}/dashboard", response_model=s.Dashboard)
def dashboard(tid: str, request: Request, db=DB):
    territory = owner(request, db, tid)
    d.refresh_alerts(db, tid)
    db.commit()
    alerts = list(db.scalars(select(m.Alert).where(m.Alert.territory_id == tid, m.Alert.status == "active")))
    return {
        "territory": territory,
        "simulation": d.one(db, m.SimulationSession, tid),
        "zone": d.one(db, m.IrrigationZone, tid),
        "rule": d.one(db, m.IrrigationRule, tid),
        "reading": d.latest(db, tid),
        "alerts": alerts,
        "status": "critical"
        if any(a.severity == "critical" for a in alerts)
        else "warning"
        if alerts
        else "normal",
        "reasons": [a.explanation for a in alerts],
    }


@router.get("/api/v1/territories/{tid}/sensors/readings", response_model=list[s.ReadingOut])
def readings(
    tid: str,
    request: Request,
    start: datetime | None = None,
    end: datetime | None = None,
    source: Literal["simulated", "device"] = "simulated",
    sensor_id: str | None = None,
    db=DB,
):
    owner(request, db, tid)
    query = select(m.SensorReading).where(
        m.SensorReading.territory_id == tid, m.SensorReading.source == source
    )
    if sensor_id:
        sensor = db.get(m.Sensor, sensor_id)
        if not sensor or sensor.territory_id != tid:
            raise HTTPException(404, "Датчик не найден")
        query = query.where(m.SensorReading.sensor_id == sensor_id)
    if any(value and (value.tzinfo is None or value.utcoffset() is None) for value in (start, end)):
        raise HTTPException(422, "Время должно содержать часовой пояс")
    if start and end and start > end:
        raise HTTPException(422, "Начало периода позже окончания")
    if start:
        query = query.where(m.SensorReading.timestamp >= start)
    if end:
        query = query.where(m.SensorReading.timestamp <= end)
    return list(reversed(list(db.scalars(query.order_by(m.SensorReading.timestamp.desc()).limit(10000)))))


@router.get("/api/v1/territories/{tid}/simulations", response_model=s.SimulationOut)
def simulation_get(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return d.one(db, m.SimulationSession, tid)


@router.post("/api/v1/territories/{tid}/simulations", response_model=s.SimulationOut)
def simulation_action(tid: str, body: s.SimulationAction, request: Request, db=DB):
    owner(request, db, tid)
    sim = d.one(db, m.SimulationSession, tid)
    if body.action == "reset":
        d.stop_pump(db, tid, "Сброс симуляции пользователем", "user")
        sim.status, sim.tick_index, sim.soil, sim.reservoir_l = "stopped", 0, 34, 100
        sim.clock = max(utcnow(), aware(sim.clock) + timedelta(seconds=1))
        # Keep accounting, cooldown, emergency latch and history; reset cannot bypass safety limits.
    for key in ("scenario", "speed", "seed"):
        if getattr(body, key) is not None:
            setattr(sim, key, getattr(body, key))
    if body.action in ("start", "resume"):
        sim.status = "running"
    elif body.action in ("pause", "stop"):
        d.stop_pump(
            db, tid, "Симуляция приостановлена" if body.action == "pause" else "Симуляция остановлена", "user"
        )
        sim.status = "paused" if body.action == "pause" else "stopped"
    elif body.action == "tick":
        was_running = sim.status == "running"
        sim.status = "running"
        d.tick(db, tid, 60)
        if not was_running:
            d.stop_pump(db, tid, "Пошаговая симуляция завершена", "user")
            sim.status = "paused"
    db.commit()
    return sim


@router.get("/api/v1/territories/{tid}/irrigation/zones", response_model=s.ZoneOut)
def zone_get(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return d.one(db, m.IrrigationZone, tid)


@router.get("/api/v1/territories/{tid}/irrigation/rules", response_model=s.RuleOut)
def rule_get(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return d.one(db, m.IrrigationRule, tid)


@router.put("/api/v1/territories/{tid}/irrigation/rules", response_model=s.RuleOut)
def rule_update(tid: str, body: s.RuleIn, request: Request, db=DB):
    owner(request, db, tid)
    rule = d.one(db, m.IrrigationRule, tid)
    d.stop_pump(db, tid, "Настройки полива изменены", "user")
    for key, value in body.model_dump().items():
        setattr(rule, key, value)
    d.record_event(db, tid, "configure", "Правила полива сохранены пользователем", "user")
    db.commit()
    return rule


@router.post("/api/v1/territories/{tid}/irrigation/actions", response_model=s.Message)
def pump_action(tid: str, body: s.PumpAction, request: Request, db=DB):
    owner(request, db, tid)
    zone = d.one(db, m.IrrigationZone, tid)
    reason = None
    if body.action == "emergency":
        zone.emergency = True
        d.stop_pump(db, tid, "Аварийная остановка пользователем", "user")
        d.record_event(db, tid, "emergency", "Аварийная блокировка включена", "user")
    elif body.action == "clear_emergency":
        zone.emergency = False
        d.record_event(db, tid, "clear_emergency", "Аварийная блокировка снята", "user")
    elif body.action == "stop":
        d.stop_pump(db, tid, "Насос остановлен пользователем", "user")
        d.one(db, m.IrrigationRule, tid).mode = "off"
    else:
        reason = d.evaluate(db, tid, manual=True, duration_s=body.duration_s)
    db.commit()
    return {"message": reason or "Команда выполнена для виртуального насоса"}


@router.get("/api/v1/territories/{tid}/irrigation/events", response_model=list[s.EventOut])
def events(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return list(
        db.scalars(
            select(m.IrrigationEvent)
            .where(m.IrrigationEvent.territory_id == tid)
            .order_by(m.IrrigationEvent.timestamp.desc())
            .limit(500)
        )
    )


@router.get("/api/v1/territories/{tid}/alerts", response_model=list[s.AlertOut])
def alerts(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return list(
        db.scalars(
            select(m.Alert).where(m.Alert.territory_id == tid).order_by(m.Alert.created_at.desc()).limit(500)
        )
    )


@router.post("/api/v1/territories/{tid}/observations", response_model=s.ObservationOut, status_code=201)
def observation_create(tid: str, body: s.ObservationIn, request: Request, db=DB):
    territory = owner(request, db, tid)
    if abs(body.latitude - territory.latitude) > 0.05 or abs(body.longitude - territory.longitude) > 0.05:
        raise HTTPException(422, "Наблюдение должно находиться рядом с территорией (до 0,05°)")
    observation = m.Observation(territory_id=tid, **body.model_dump())
    db.add(observation)
    db.commit()
    return observation


@router.get("/api/v1/territories/{tid}/observations", response_model=list[s.ObservationOut])
def observations(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return list(
        db.scalars(
            select(m.Observation)
            .where(m.Observation.territory_id == tid)
            .order_by(m.Observation.timestamp.desc())
            .limit(500)
        )
    )


def owned_observation(db, tid, oid):
    observation = db.get(m.Observation, oid)
    if not observation or observation.territory_id != tid:
        raise HTTPException(404, "Наблюдение не найдено")
    return observation


@router.post("/api/v1/territories/{tid}/observations/{oid}/photo", response_model=s.ObservationOut)
def upload_photo(tid: str, oid: str, request: Request, file: UploadFile = File(...), db=DB):
    owner(request, db, tid)
    observation = owned_observation(db, tid, oid)
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(422, "Разрешены JPEG, PNG и WebP")
    raw = file.file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "Максимальный размер фотографии — 5 МБ")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError("Too many pixels")
            image.load()
            image = image.convert("RGB")
            image.thumbnail((1920, 1920))
            upload_dir = ROOT / "data" / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            name = secrets.token_hex(24) + ".jpg"
            image.save(upload_dir / name, "JPEG", quality=85)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Некорректное изображение") from exc
    old = observation.photo_path
    observation.photo_path = name
    db.commit()
    if old:
        (upload_dir / old).unlink(missing_ok=True)
    return observation


@router.get("/api/v1/territories/{tid}/observations/{oid}/photo")
def photo(tid: str, oid: str, request: Request, db=DB):
    owner(request, db, tid)
    observation = owned_observation(db, tid, oid)
    if not observation.photo_path:
        raise HTTPException(404, "Фото отсутствует")
    return FileResponse(ROOT / "data" / "uploads" / observation.photo_path, media_type="image/jpeg")


@router.get("/api/v1/territories/{tid}/weather", response_model=s.WeatherOut)
def weather_get(tid: str, request: Request, db=DB):
    return weather(db, owner(request, db, tid))


@router.get("/api/v1/territories/{tid}/satellite", response_model=s.SatelliteOut)
def satellite(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    date = (utcnow() - timedelta(days=2)).date().isoformat()
    return {
        "date": date,
        "url": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/"
        + date
        + "/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
        "explanation": "Обзорный слой NASA MODIS, 250 м/пиксель; не подходит для оценки отдельных растений. Возможны облака и пропуски. NDVI не рассчитывается.",
    }


@router.post("/api/v1/territories/{tid}/reports", response_model=s.ReportOut, status_code=201)
def report_create(tid: str, request: Request, day: str | None = None, db=DB):
    territory = owner(request, db, tid)
    sim = d.one(db, m.SimulationSession, tid)
    tz = ZoneInfo(territory.timezone)
    try:
        date = datetime.strptime(day, "%Y-%m-%d").date() if day else aware(sim.clock).astimezone(tz).date()
    except ValueError as exc:
        raise HTTPException(422, "Ожидается дата YYYY-MM-DD") from exc
    start = datetime.combine(date, datetime.min.time(), tz).astimezone(timezone.utc)
    end = (datetime.combine(date, datetime.min.time(), tz) + timedelta(days=1)).astimezone(timezone.utc)
    rows = list(
        db.scalars(
            select(m.SensorReading).where(
                m.SensorReading.territory_id == tid,
                m.SensorReading.timestamp >= start,
                m.SensorReading.timestamp < end,
                m.SensorReading.quality == "valid",
                m.SensorReading.source == "simulated",
            )
        )
    )
    stats = {}
    for field in ("soil_moisture_pct", "air_temperature_c", "air_humidity_pct", "light_lux"):
        values = [getattr(r, field) for r in rows if getattr(r, field) is not None]
        stats[field] = (
            {"min": min(values), "max": max(values), "mean": sum(values) / len(values)} if values else None
        )
    ev = list(
        db.scalars(
            select(m.IrrigationEvent).where(
                m.IrrigationEvent.territory_id == tid,
                m.IrrigationEvent.timestamp >= start,
                m.IrrigationEvent.timestamp < end,
            )
        )
    )
    observations = list(
        db.scalars(
            select(m.Observation).where(
                m.Observation.territory_id == tid,
                m.Observation.timestamp >= start,
                m.Observation.timestamp < end,
            )
        )
    )
    alert_rows = list(
        db.scalars(
            select(m.Alert).where(
                m.Alert.territory_id == tid, m.Alert.created_at >= start, m.Alert.created_at < end
            )
        )
    )
    weather_row = db.scalar(
        select(m.WeatherSnapshot)
        .where(
            m.WeatherSnapshot.territory_id == tid,
            m.WeatherSnapshot.fetched_at >= start,
            m.WeatherSnapshot.fetched_at < end,
        )
        .order_by(m.WeatherSnapshot.fetched_at.desc())
    )
    data = {
        "date": str(date),
        "timezone": territory.timezone,
        "reading_count": len(rows),
        "sources": sorted({r.source for r in rows}),
        "stats": stats,
        "alert_count": len(alert_rows),
        "irrigation_count": sum(e.action == "start" for e in ev),
        "duration_s": sum(e.duration_s for e in ev if e.action == "stop"),
        "water_l": sum(e.estimated_water_l for e in ev if e.action == "stop"),
        "water_accounting": "Расход завершённых в этот день поливов; текущий полив появится после остановки.",
        "observations": [o.text for o in observations],
        "weather": weather_row.data.get("current") if weather_row else None,
        "summary": f"Получено {len(rows)} валидных показаний. Предупреждений: {len(alert_rows)}.",
        "recommendations": sorted({a.recommendation for a in alert_rows})
        or ["Продолжайте наблюдение за участком."],
    }
    report = m.DailyReport(territory_id=tid, period_start=start, period_end=end, data=data)
    db.add(report)
    db.commit()
    return report


@router.get("/api/v1/territories/{tid}/reports", response_model=list[s.ReportOut])
def reports(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return list(
        db.scalars(
            select(m.DailyReport)
            .where(m.DailyReport.territory_id == tid)
            .order_by(m.DailyReport.created_at.desc())
            .limit(100)
        )
    )


@router.post("/api/v1/territories/{tid}/sensors/device-credential", response_model=s.CredentialOut)
def device_credential(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    zone = foundation.ensure_foundation(db, tid)
    devices = list(
        db.scalars(
            select(f.Device).where(
                f.Device.territory_id == tid, f.Device.source == "REAL", f.Device.device_type == "SENSOR"
            )
        )
    )
    if len(devices) > 1:
        raise HTTPException(409, "Выберите конкретное устройство на вкладке «Устройства» для выдачи ключа")
    device = (
        devices[0]
        if devices
        else foundation.create_device(db, tid, DeviceIn(name="Raspberry Pi", zone_id=zone.id))
    )
    result = foundation.credential(db, device)
    db.commit()
    return {key: result[key] for key in ("sensor_id", "api_key", "explanation")}


@router.post("/api/v1/devices/telemetry", response_model=s.ReadingOut, status_code=201)
def device_ingest(body: s.Telemetry, request: Request, db=DB):
    auth = request.headers.get("authorization", "")
    sensor = db.get(m.Sensor, body.sensor_id)
    device = db.scalar(select(f.Device).where(f.Device.legacy_sensor_id == body.sensor_id))
    if (
        not auth.startswith("Bearer ")
        or not sensor
        or not sensor.credential_hash
        or not device
        or not device.active
        or device.source != "REAL"
        or not secrets.compare_digest(sec.digest(auth[7:]), sensor.credential_hash)
    ):
        raise HTTPException(401, "Некорректный ключ устройства")
    if body.source != "device" or abs((utcnow() - body.timestamp).total_seconds()) > 300:
        raise HTTPException(422, "Требуются source=device и время в пределах 5 минут UTC")
    previous = db.scalar(
        select(m.SensorReading)
        .where(m.SensorReading.sensor_id == sensor.id)
        .order_by(m.SensorReading.timestamp.desc())
    )
    if previous and aware(previous.timestamp) >= body.timestamp:
        raise HTTPException(409, "Повторная или более старая телеметрия")
    reading = d.ingest(db, sensor.territory_id, body)
    db.commit()
    return reading
