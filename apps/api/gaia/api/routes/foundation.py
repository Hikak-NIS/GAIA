from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select
from ... import models as m, foundation_models as f, foundation_schemas as s, security
from ...schemas import Message, ReadingOut
from ...services import foundation as service
from ..dependencies import DB, owner
from ...config import settings

router = APIRouter(prefix="/api/v1", tags=["Foundation"])


def owned(db, request, model, ident):
    # Authenticate even for an unknown ID, and never disclose another owner's inventory.
    security.current_user(request, db)
    obj = db.get(model, ident)
    if not obj:
        raise HTTPException(404, "Объект не найден")
    owner(request, db, obj.territory_id)
    return obj


@router.get("/territories/{tid}/zones", response_model=list[s.ZoneOut])
def zones(tid: str, request: Request, db=DB):
    owner(request, db, tid)
    return list(db.scalars(select(f.Zone).where(f.Zone.territory_id == tid).order_by(f.Zone.created_at)))


@router.post("/territories/{tid}/zones", response_model=s.ZoneOut, status_code=201)
def zone_create(tid: str, body: s.ZoneIn, request: Request, db=DB):
    owner(request, db, tid)
    zone = f.Zone(territory_id=tid, **body.model_dump())
    db.add(zone)
    db.commit()
    return zone


@router.get("/zones/{zid}", response_model=s.ZoneOut)
def zone_get(zid: str, request: Request, db=DB):
    return owned(db, request, f.Zone, zid)


@router.put("/zones/{zid}", response_model=s.ZoneOut)
def zone_update(zid: str, body: s.ZoneIn, request: Request, db=DB):
    zone = owned(db, request, f.Zone, zid)
    for key, value in body.model_dump().items():
        setattr(zone, key, value)
    db.commit()
    return zone


@router.delete("/zones/{zid}", response_model=Message)
def zone_delete(zid: str, request: Request, db=DB):
    zone = owned(db, request, f.Zone, zid)
    if zone.is_default or any(
        db.scalar(select(model.id).where(model.zone_id == zid).limit(1))
        for model in (f.Device, f.PlantInstance)
    ):
        raise HTTPException(409, "Основную или используемую зону удалить нельзя")
    db.delete(zone)
    db.commit()
    return {"message": "Зона удалена"}


@router.get("/plant-profiles", response_model=list[s.ProfileOut])
def profiles(request: Request, db=DB):
    user = security.current_user(request, db)
    return list(
        db.scalars(
            select(f.PlantProfile)
            .where(f.PlantProfile.owner_id == user.id)
            .order_by(f.PlantProfile.common_name)
        )
    )


@router.post("/plant-profiles", response_model=s.ProfileOut, status_code=201)
def profile_create(body: s.ProfileIn, request: Request, db=DB):
    user = security.current_user(request, db)
    profile = f.PlantProfile(owner_id=user.id, **body.model_dump())
    db.add(profile)
    db.commit()
    return profile


@router.get("/plant-profiles/{pid}", response_model=s.ProfileOut)
def profile_get(pid: str, request: Request, db=DB):
    return service.profile_for(db, security.current_user(request, db).id, pid)


@router.put("/plant-profiles/{pid}", response_model=s.ProfileOut)
def profile_update(pid: str, body: s.ProfileIn, request: Request, db=DB):
    profile = profile_get(pid, request, db)
    for key, value in body.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    return profile


@router.delete("/plant-profiles/{pid}", response_model=Message)
def profile_delete(pid: str, request: Request, db=DB):
    profile = profile_get(pid, request, db)
    if db.scalar(select(f.PlantInstance.id).where(f.PlantInstance.profile_id == pid).limit(1)):
        raise HTTPException(409, "Профиль используется растениями")
    db.delete(profile)
    db.commit()
    return {"message": "Профиль удалён"}


@router.get("/territories/{tid}/devices", response_model=list[s.DeviceOut])
def devices(tid: str, request: Request, source: s.Source | None = None, db=DB):
    owner(request, db, tid)
    if not settings.legacy_simulation_enabled:
        source = "REAL"
    query = select(f.Device).where(f.Device.territory_id == tid)
    if source:
        query = query.where(f.Device.source == source)
    return [service.device_view(db, row) for row in db.scalars(query.order_by(f.Device.created_at))]


@router.post("/territories/{tid}/devices", response_model=s.DeviceOut, status_code=201)
def device_create(tid: str, body: s.DeviceIn, request: Request, db=DB):
    owner(request, db, tid)
    device = service.create_device(db, tid, body)
    db.commit()
    return service.device_view(db, device)


@router.get("/devices/{did}", response_model=s.DeviceOut)
def device_get(did: str, request: Request, db=DB):
    return service.device_view(db, owned(db, request, f.Device, did))


@router.put("/devices/{did}", response_model=s.DeviceOut)
def device_update(did: str, body: s.DeviceUpdate, request: Request, db=DB):
    device = owned(db, request, f.Device, did)
    service.zone_for(db, device.territory_id, body.zone_id)
    if device.source == "SIMULATED" and (body.zone_id != device.zone_id or not body.active):
        raise HTTPException(409, "Основные виртуальные устройства управляются через вкладку «Симуляция»")
    if body.zone_id != device.zone_id:
        links = db.scalar(
            select(f.PlantSensorLink.plant_id)
            .join(f.SensorChannel)
            .where(f.SensorChannel.device_id == did)
            .limit(1)
        )
        camera = db.scalar(select(f.PlantInstance.id).where(f.PlantInstance.camera_device_id == did).limit(1))
        if links or camera or service.latest_for_device(db, device):
            raise HTTPException(409, "Устройство с привязками или историей нельзя переносить в другую зону")
    for key, value in body.model_dump().items():
        setattr(device, key, value)
    if not device.active and device.legacy_sensor_id:
        db.get(m.Sensor, device.legacy_sensor_id).credential_hash = None
    db.commit()
    return service.device_view(db, device)


@router.post("/devices/{did}/credential", response_model=s.CredentialOut)
def device_credential(did: str, request: Request, db=DB):
    result = service.credential(db, owned(db, request, f.Device, did))
    db.commit()
    return result


@router.put("/sensor-channels/{cid}/calibration", response_model=s.ChannelOut)
def calibration(cid: str, body: s.Calibration, request: Request, db=DB):
    security.current_user(request, db)
    channel = db.get(f.SensorChannel, cid)
    if not channel:
        raise HTTPException(404, "Канал не найден")
    device = owned(db, request, f.Device, channel.device_id)
    if device.source != "REAL":
        raise HTTPException(409, "Калибровка виртуального сенсора фиксирована моделью симуляции")
    channel.calibration = body.model_dump()
    db.commit()
    return service.channel_view(channel, device, service.latest_for_device(db, device))


@router.get("/devices/{did}/readings", response_model=list[ReadingOut])
def device_readings(did: str, request: Request, limit: int = Query(100, ge=1, le=1000), db=DB):
    device = owned(db, request, f.Device, did)
    if not device.legacy_sensor_id:
        return []
    return list(
        reversed(
            list(
                db.scalars(
                    select(m.SensorReading)
                    .where(m.SensorReading.sensor_id == device.legacy_sensor_id)
                    .order_by(m.SensorReading.timestamp.desc())
                    .limit(limit)
                )
            )
        )
    )


@router.get("/territories/{tid}/plants", response_model=list[s.PlantOut])
def plants(tid: str, request: Request, zone_id: str | None = None, db=DB):
    owner(request, db, tid)
    query = select(f.PlantInstance).where(f.PlantInstance.territory_id == tid)
    if zone_id:
        service.zone_for(db, tid, zone_id)
        query = query.where(f.PlantInstance.zone_id == zone_id)
    return [service.plant_view(db, plant) for plant in db.scalars(query.order_by(f.PlantInstance.created_at))]


@router.post("/territories/{tid}/plants", response_model=s.PlantOut, status_code=201)
def plant_create(tid: str, body: s.PlantIn, request: Request, db=DB):
    territory = owner(request, db, tid)
    plant = service.save_plant(db, f.PlantInstance(territory_id=tid), body, territory.owner_id)
    db.commit()
    return service.plant_view(db, plant)


@router.get("/plants/{pid}", response_model=s.PlantOut)
def plant_get(pid: str, request: Request, db=DB):
    return service.plant_view(db, owned(db, request, f.PlantInstance, pid))


@router.put("/plants/{pid}", response_model=s.PlantOut)
def plant_update(pid: str, body: s.PlantIn, request: Request, db=DB):
    plant = owned(db, request, f.PlantInstance, pid)
    service.save_plant(db, plant, body, security.current_user(request, db).id)
    db.commit()
    return service.plant_view(db, plant)


@router.delete("/plants/{pid}", response_model=Message)
def plant_delete(pid: str, request: Request, db=DB):
    db.delete(owned(db, request, f.PlantInstance, pid))
    db.commit()
    return {"message": "Растение удалено; история устройств сохранена"}


@router.get("/plants/{pid}/readings")
def plant_readings(
    pid: str, request: Request, source: s.Source | None = None, limit: int = Query(100, ge=1, le=1000), db=DB
):
    if not settings.legacy_simulation_enabled:
        source = "REAL"
    plant = owned(db, request, f.PlantInstance, pid)
    channels = list(
        db.scalars(select(f.SensorChannel).join(f.PlantSensorLink).where(f.PlantSensorLink.plant_id == pid))
    )
    devices_by_id = {c.device_id: db.get(f.Device, c.device_id) for c in channels}
    if source:
        channels = [c for c in channels if devices_by_id[c.device_id].source == source]
    # Return only explicitly linked scalar channels, never adjacent values from the same station.
    rows = []
    for channel in channels:
        device = devices_by_id[channel.device_id]
        history = db.scalars(
            select(m.SensorReading)
            .where(m.SensorReading.sensor_id == device.legacy_sensor_id)
            .order_by(m.SensorReading.timestamp.desc())
            .limit(limit)
        )
        rows.extend(service.channel_view(channel, device, reading, current=False) for reading in history)
    profile = db.get(f.PlantProfile, plant.profile_id)
    return {
        "health_status": "UNKNOWN",
        "health_explanation": "Оценка состояния ещё не рассчитана",
        "effective_requirements": service.effective_requirements(profile, plant.growth_stage),
        "channels": [
            service.channel_view(
                c, devices_by_id[c.device_id], service.latest_for_device(db, devices_by_id[c.device_id])
            )
            for c in channels
        ],
        "history": sorted(rows, key=lambda r: r["timestamp"], reverse=True),
    }
