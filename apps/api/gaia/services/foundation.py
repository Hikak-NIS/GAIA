"""Inventory, ownership-safe associations and source-aware telemetry views."""

import secrets
from fastapi import HTTPException
from sqlalchemy import select, delete
from .. import models as m, foundation_models as f, security
from ..config import utcnow, aware
from ..foundation_schemas import Requirements

CHANNELS = {
    "air_temperature_c": "°C",
    "air_humidity_pct": "%",
    "soil_moisture_pct": "%",
    "light_lux": "lx",
    "pressure_hpa": "hPa",
    "battery_pct": "%",
}


def latest_for_device(db, device):
    if not device.legacy_sensor_id:
        return None
    return db.scalar(
        select(m.SensorReading)
        .where(m.SensorReading.sensor_id == device.legacy_sensor_id)
        .order_by(m.SensorReading.timestamp.desc())
    )


def add_channels(db, device):
    for name, unit in CHANNELS.items():
        db.add(f.SensorChannel(device_id=device.id, sensor_type=name, unit=unit, calibration={}))


def ensure_foundation(db, tid):
    """Idempotent initialization; migration performs the equivalent backfill."""
    zone = db.scalar(select(f.Zone).where(f.Zone.territory_id == tid, f.Zone.is_default.is_(True)))
    if not zone:
        zone = f.Zone(territory_id=tid, name="Основная зона", is_default=True)
        db.add(zone)
        db.flush()
    for sensor in db.scalars(select(m.Sensor).where(m.Sensor.territory_id == tid)):
        if db.scalar(select(f.Device.id).where(f.Device.legacy_sensor_id == sensor.id)):
            continue
        device = f.Device(
            territory_id=tid,
            zone_id=zone.id,
            name=sensor.name,
            device_type="SENSOR",
            source="SIMULATED" if sensor.source == "simulated" else "REAL",
            legacy_sensor_id=sensor.id,
        )
        db.add(device)
        db.flush()
        last = latest_for_device(db, device)
        device.last_seen = last.received_at if last else None
        add_channels(db, device)
    pump = db.scalar(select(m.IrrigationZone).where(m.IrrigationZone.territory_id == tid))
    if pump and not db.scalar(select(f.Device.id).where(f.Device.legacy_irrigation_id == pump.id)):
        db.add(
            f.Device(
                territory_id=tid,
                zone_id=zone.id,
                name="Виртуальный насос",
                device_type="ACTUATOR",
                source="SIMULATED",
                legacy_irrigation_id=pump.id,
                actuator_type="PUMP",
            )
        )
    db.flush()
    return zone


def zone_for(db, tid, zid):
    zone = db.get(f.Zone, zid)
    if not zone or zone.territory_id != tid:
        raise HTTPException(404, "Зона не найдена в этой территории")
    return zone


def profile_for(db, uid, pid):
    profile = db.get(f.PlantProfile, pid)
    if not profile or profile.owner_id != uid:
        raise HTTPException(404, "Профиль растения не найден")
    return profile


def create_device(db, tid, body):
    zone_for(db, tid, body.zone_id)
    if body.source != "REAL":
        raise HTTPException(409, "Виртуальные устройства создаёт существующий симулятор в основной зоне")
    device = f.Device(territory_id=tid, **body.model_dump())
    if body.device_type == "SENSOR":
        station = m.Sensor(territory_id=tid, name=body.name, source="device")
        db.add(station)
        db.flush()
        device.legacy_sensor_id = station.id
    db.add(device)
    db.flush()
    if device.legacy_sensor_id:
        add_channels(db, device)
    db.flush()
    return device


def credential(db, device):
    if device.source != "REAL" or not device.active or not device.legacy_sensor_id:
        raise HTTPException(409, "Ключ телеметрии доступен только активному REAL-устройству типа SENSOR")
    key = secrets.token_urlsafe(48)
    db.get(m.Sensor, device.legacy_sensor_id).credential_hash = security.digest(key)
    return {
        "device_id": device.id,
        "sensor_id": device.legacy_sensor_id,
        "api_key": key,
        "explanation": "Ключ показывается один раз. Предыдущий ключ отозван. Это доступ к телеметрии; GPIO не подключён.",
    }


def channel_view(channel, device, reading, *, current=True):
    availability = "HISTORICAL"
    if current:
        availability = "MISSING" if not reading else "DISABLED" if not device.active else "CURRENT"
        if (
            reading
            and availability == "CURRENT"
            and (
                (utcnow() - aware(reading.received_at)).total_seconds() > 120
                or (
                    device.source == "REAL"
                    and abs((utcnow() - aware(reading.timestamp)).total_seconds()) > 300
                )
            )
        ):
            availability = "STALE"
    return {
        "id": channel.id,
        "device_id": device.id,
        "sensor_type": channel.sensor_type,
        "unit": channel.unit,
        "calibration": channel.calibration,
        "source": device.source,
        "current_value": getattr(reading, channel.sensor_type) if reading else None,
        "timestamp": reading.timestamp if reading else None,
        "received_at": reading.received_at if reading else None,
        "quality": reading.quality if reading else "missing",
        "availability": availability,
    }


def device_view(db, device):
    reading = latest_for_device(db, device)
    if device.source == "SIMULATED":
        status = "SIMULATED"
    elif (
        not device.active
        or not device.last_seen
        or (utcnow() - aware(device.last_seen)).total_seconds() > 120
    ):
        status = "OFFLINE"
    else:
        status = (
            "ERROR"
            if reading and reading.quality == "invalid"
            else ("WARNING" if reading and reading.quality != "valid" else "ONLINE")
        )
    pump = db.get(m.IrrigationZone, device.legacy_irrigation_id) if device.legacy_irrigation_id else None
    state = (
        ("ON" if pump.pump_on else "OFF")
        if pump
        else ("UNKNOWN" if device.device_type == "ACTUATOR" else None)
    )
    return {
        "id": device.id,
        "territory_id": device.territory_id,
        "zone_id": device.zone_id,
        "name": device.name,
        "device_type": device.device_type,
        "source": device.source,
        "active": device.active,
        "status": status,
        "last_seen": device.last_seen,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
        "sensor_id": device.legacy_sensor_id,
        "channels": [
            channel_view(c, device, reading)
            for c in db.scalars(
                select(f.SensorChannel)
                .where(f.SensorChannel.device_id == device.id)
                .order_by(f.SensorChannel.sensor_type)
            )
        ],
        "actuator_type": device.actuator_type,
        "actuator_state": state,
        "safety_status": ("EMERGENCY" if pump.emergency else "VIRTUAL_ONLY")
        if pump
        else ("NOT_CONNECTED" if device.device_type == "ACTUATOR" else None),
        "last_action": max(filter(None, (pump.started_at, pump.stopped_at)), default=None) if pump else None,
    }


def plant_view(db, plant):
    return {
        key: getattr(plant, key)
        for key in (
            "id",
            "territory_id",
            "zone_id",
            "profile_id",
            "name",
            "planted_on",
            "growth_stage",
            "health_status",
            "camera_device_id",
            "created_at",
            "updated_at",
        )
    } | {
        "sensor_channel_ids": list(
            db.scalars(select(f.PlantSensorLink.channel_id).where(f.PlantSensorLink.plant_id == plant.id))
        )
    }


def save_plant(db, plant, body, uid):
    zone_for(db, plant.territory_id, body.zone_id)
    profile_for(db, uid, body.profile_id)
    if body.camera_device_id:
        camera = db.get(f.Device, body.camera_device_id)
        if (
            not camera
            or camera.territory_id != plant.territory_id
            or camera.zone_id != body.zone_id
            or camera.device_type != "CAMERA"
            or not camera.active
        ):
            raise HTTPException(422, "Выберите активную камеру из зоны растения")
    channels = set(body.sensor_channel_ids)
    for channel_id in channels:
        channel = db.get(f.SensorChannel, channel_id)
        device = db.get(f.Device, channel.device_id) if channel else None
        if (
            not device
            or device.territory_id != plant.territory_id
            or device.zone_id != body.zone_id
            or not device.active
        ):
            raise HTTPException(422, "Каждый сенсор должен принадлежать зоне растения и активному устройству")
    for key, value in body.model_dump(exclude={"sensor_channel_ids"}).items():
        setattr(plant, key, value)
    db.add(plant)
    db.flush()
    db.execute(delete(f.PlantSensorLink).where(f.PlantSensorLink.plant_id == plant.id))
    db.add_all([f.PlantSensorLink(plant_id=plant.id, channel_id=cid) for cid in channels])
    db.flush()
    return plant


def effective_requirements(profile, stage):
    values = Requirements.model_validate(profile).model_dump()
    # Null/empty stage values inherit the profile, never manufacture default agronomic thresholds.
    values.update(
        {
            key: value
            for key, value in profile.stage_requirements.get(stage, {}).items()
            if value is not None and value != ""
        }
    )
    return Requirements.model_validate(values).model_dump()
