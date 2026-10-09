import math
import random
from datetime import timedelta
from threading import Lock
from zoneinfo import ZoneInfo
from sqlalchemy import select
from . import models as m
from .config import aware, utcnow
from .schemas import Telemetry

# FastAPI may enter and exit sync dependencies on different worker threads.
# All acquisitions are at request/background boundaries; there is no nested acquisition.
LOCK = Lock()
FLOW_L_S = 0.8 / 60


def one(db, model, territory_id):
    return db.scalar(select(model).where(model.territory_id == territory_id))


def latest(db, territory_id):
    return db.scalar(
        select(m.SensorReading)
        .where(m.SensorReading.territory_id == territory_id, m.SensorReading.source == "simulated")
        .order_by(m.SensorReading.timestamp.desc(), m.SensorReading.received_at.desc())
    )


def record_event(db, territory_id, action, reason, actor="system", reading=None):
    sim, zone, rule = (
        one(db, model, territory_id) for model in (m.SimulationSession, m.IrrigationZone, m.IrrigationRule)
    )
    if action == "denied" and actor == "system":
        previous = db.scalar(
            select(m.IrrigationEvent)
            .where(m.IrrigationEvent.territory_id == territory_id)
            .order_by(m.IrrigationEvent.timestamp.desc())
        )
        if (
            previous
            and previous.action == action
            and previous.reason == reason
            and (aware(sim.clock) - aware(previous.timestamp)).total_seconds() < 300
        ):
            return previous
    duration = max(0, (aware(sim.clock) - aware(zone.started_at)).total_seconds()) if zone.started_at else 0
    event = m.IrrigationEvent(
        territory_id=territory_id,
        timestamp=sim.clock,
        mode=rule.mode,
        action=action,
        reason=reason,
        actor=actor,
        trigger_value=reading.soil_moisture_pct if reading else None,
        target_value=rule.target_pct,
        duration_s=duration if action == "stop" else 0,
        estimated_water_l=zone.run_water_l if action == "stop" else 0,
    )
    db.add(event)
    return event


def stop_pump(db, territory_id, reason, actor="system"):
    zone = one(db, m.IrrigationZone, territory_id)
    if zone.pump_on:
        record_event(db, territory_id, "stop", reason, actor, latest(db, territory_id))
        zone.pump_on = False
        zone.stopped_at = one(db, m.SimulationSession, territory_id).clock
        zone.deadline = None


def reset_day(sim, zone, territory):
    day = aware(sim.clock).astimezone(ZoneInfo(territory.timezone)).date().isoformat()
    if zone.water_day != day:
        zone.water_day, zone.daily_water_l = day, 0


def block_reason(db, territory_id, reading, starting=True):
    sim, zone, rule = (
        one(db, model, territory_id) for model in (m.SimulationSession, m.IrrigationZone, m.IrrigationRule)
    )
    if zone.emergency:
        return "Аварийная остановка активна"
    if reading and reading.source != "simulated":
        return "Виртуальный насос принимает только данные симулятора"
    if sim.status != "running":
        return "Симуляция не запущена"
    if not reading or reading.quality != "valid" or reading.soil_moisture_pct is None:
        return "Данные датчика отсутствуют или невалидны"
    if (aware(sim.clock) - aware(reading.timestamp)).total_seconds() > 300 or (
        utcnow() - aware(reading.received_at)
    ).total_seconds() > 120:
        return "Данные датчика устарели"
    if sim.reservoir_l <= rule.min_reservoir_l + 1e-8:
        return "Недостаточно воды в резервуаре"
    if zone.daily_water_l >= rule.daily_limit_l - 1e-8:
        return "Достигнут дневной лимит воды"
    if (
        starting
        and zone.stopped_at
        and (aware(sim.clock) - aware(zone.stopped_at)).total_seconds() < rule.cooldown_s
    ):
        return "Ожидание между поливами (cooldown) ещё не завершено"
    if rule.block_rain:
        weather = db.scalar(
            select(m.WeatherSnapshot)
            .where(m.WeatherSnapshot.territory_id == territory_id)
            .order_by(m.WeatherSnapshot.fetched_at.desc())
        )
        if not weather or (utcnow() - aware(weather.fetched_at)).total_seconds() > 1800:
            return "Нет свежего прогноза: запрет полива при неизвестной погоде"
        if weather.data.get("next_6h_probability", 100) >= rule.rain_threshold_pct:
            return "Ожидается дождь в ближайшие 6 часов"
    return None


def evaluate(db, territory_id, manual=False, duration_s=300):
    sim, zone, rule = (
        one(db, model, territory_id) for model in (m.SimulationSession, m.IrrigationZone, m.IrrigationRule)
    )
    reset_day(sim, zone, db.get(m.Territory, territory_id))
    reading = latest(db, territory_id)
    if zone.pump_on:
        reason = block_reason(db, territory_id, reading, starting=False)
        if rule.mode == "off":
            reason = "Режим полива выключен"
        elif (
            reading and reading.soil_moisture_pct is not None and reading.soil_moisture_pct >= rule.target_pct
        ):
            reason = f"Достигнута целевая влажность {rule.target_pct:g}%"
        elif zone.deadline and aware(sim.clock) >= aware(zone.deadline):
            reason = "Достигнута заданная или максимальная длительность полива"
        if reason:
            stop_pump(db, territory_id, reason)
        return
    should_start = manual or (
        rule.mode == "automatic"
        and (not reading or reading.soil_moisture_pct is None or reading.soil_moisture_pct < rule.trigger_pct)
    )
    if not should_start:
        return
    reason = block_reason(db, territory_id, reading)
    if manual and rule.mode != "manual":
        reason = "Для ручного запуска выберите ручной режим"
    if reason:
        record_event(db, territory_id, "denied", reason, "user" if manual else "system", reading)
        return reason
    zone.pump_on = True
    zone.started_at = sim.clock
    zone.run_water_l = 0
    zone.deadline = aware(sim.clock) + timedelta(
        seconds=min(duration_s, rule.max_duration_s) if manual else rule.max_duration_s
    )
    rain = (
        "; прогноз проверен, дождь ниже порога"
        if rule.block_rain
        else "; проверка прогноза отключена пользователем"
    )
    record_event(
        db,
        territory_id,
        "start",
        (
            f"Ручной полив на {min(duration_s, rule.max_duration_s)} с"
            if manual
            else f"Автополив включён: влажность почвы {reading.soil_moisture_pct:.1f}%, порог {rule.trigger_pct:g}%, цель {rule.target_pct:g}%"
        )
        + rain,
        "user" if manual else "system",
        reading,
    )
    return None


def refresh_alerts(db, territory_id):
    sim, zone, rule = (
        one(db, model, territory_id) for model in (m.SimulationSession, m.IrrigationZone, m.IrrigationRule)
    )
    r = latest(db, territory_id)
    soil = r.soil_moisture_pct if r and r.soil_moisture_pct is not None else 100
    temp = r.air_temperature_c if r and r.air_temperature_c is not None else 20
    stale = (
        not r
        or r.quality != "valid"
        or (utcnow() - aware(r.received_at)).total_seconds() > 120
        or (aware(sim.clock) - aware(r.timestamp)).total_seconds() > 300
    )
    weather = db.scalar(
        select(m.WeatherSnapshot)
        .where(m.WeatherSnapshot.territory_id == territory_id)
        .order_by(m.WeatherSnapshot.fetched_at.desc())
    )
    heavy_rain = bool(
        weather
        and (utcnow() - aware(weather.fetched_at)).total_seconds() < 1800
        and weather.data.get("next_6h_precipitation_mm", 0) >= 10
    )
    checks = [
        (
            "dry_soil",
            soil < rule.trigger_pct,
            "warning",
            "Почва пересыхает",
            f"Влажность {soil:.1f}% ниже порога {rule.trigger_pct:g}%.",
            "Проверьте автополив и запас воды.",
        ),
        (
            "heat_drought",
            temp >= 35 and soil < 30,
            "critical",
            "Жара и сухая почва",
            f"Температура {temp:.1f} °C, влажность {soil:.1f}%.",
            "Обеспечьте полив и затенение.",
        ),
        (
            "frost",
            temp < 2,
            "warning",
            "Риск заморозка",
            f"Температура {temp:.1f} °C.",
            "Укройте чувствительные растения.",
        ),
        (
            "heavy_rain",
            heavy_rain,
            "warning",
            "Ожидается сильный дождь",
            "Прогноз осадков за 6 часов не менее 10 мм.",
            "Отключите лишний полив и проверьте дренаж.",
        ),
        (
            "low_reservoir",
            sim.reservoir_l <= rule.min_reservoir_l,
            "critical",
            "Резервуар почти пуст",
            f"Осталось {sim.reservoir_l:.2f} л.",
            "Сброс симуляции восстановит демонстрационный резервуар.",
        ),
        (
            "sensor_failure",
            stale,
            "critical",
            "Нет надёжных данных датчика",
            "Показания отсутствуют, устарели или невалидны.",
            "Возобновите симуляцию или проверьте станцию.",
        ),
        (
            "pump_timeout",
            bool(
                zone.started_at
                and (aware(sim.clock) - aware(zone.started_at)).total_seconds() >= rule.max_duration_s
                and zone.pump_on
            ),
            "critical",
            "Превышена длительность полива",
            "Насос достиг ограничения длительности.",
            "Проверьте настройки и историю остановки.",
        ),
        (
            "daily_limit",
            zone.daily_water_l >= rule.daily_limit_l - 1e-8,
            "warning",
            "Достигнут дневной лимит воды",
            f"Использовано {zone.daily_water_l:.2f} л.",
            "Проверьте расход и дождитесь следующего дня.",
        ),
    ]
    active = {
        a.code: a
        for a in db.scalars(
            select(m.Alert).where(m.Alert.territory_id == territory_id, m.Alert.status == "active")
        )
    }
    for code, condition, severity, title, explanation, recommendation in checks:
        if condition and code not in active:
            db.add(
                m.Alert(
                    territory_id=territory_id,
                    code=code,
                    severity=severity,
                    title=title,
                    explanation=explanation,
                    recommendation=recommendation,
                    created_at=sim.clock,
                )
            )
        elif condition:
            active[code].explanation = explanation
        elif code in active:
            active[code].status, active[code].resolved_at = "resolved", sim.clock


def ingest(db, territory_id, payload: Telemetry):
    sensor = db.get(m.Sensor, payload.sensor_id)
    if not sensor or sensor.territory_id != territory_id or sensor.source != payload.source:
        raise ValueError("Датчик и источник не соответствуют территории")
    r = m.SensorReading(territory_id=territory_id, **payload.model_dump())
    db.add(r)
    db.flush()
    from .foundation_models import Device

    device = db.scalar(select(Device).where(Device.legacy_sensor_id == sensor.id))
    if device:
        device.last_seen = r.received_at
    if payload.source == "simulated":
        refresh_alerts(db, territory_id)
        evaluate(db, territory_id)
    return r


def tick(db, territory_id, seconds=60):
    sim, zone, rule = (
        one(db, model, territory_id) for model in (m.SimulationSession, m.IrrigationZone, m.IrrigationRule)
    )
    reset_day(sim, zone, db.get(m.Territory, territory_id))
    # Stop unsafe runs before integrating water; each integration step is <= 60 seconds.
    evaluate(db, territory_id)
    rng = random.Random(sim.seed + sim.tick_index * 7919)
    hour = (sim.tick_index * seconds / 3600) % 24
    daylight = max(0, math.sin((hour - 6) * math.pi / 12))
    scenario = sim.scenario
    temperature = (
        {"normal": 23, "drought": 30, "heatwave": 39, "rain": 19, "frost": -3, "sensor_failure": 25}[scenario]
        + 3 * daylight
        + rng.uniform(-0.5, 0.5)
    )
    humidity = {"normal": 55, "drought": 25, "heatwave": 18, "rain": 90, "frost": 65, "sensor_failure": 45}[
        scenario
    ] + rng.uniform(-2, 2)
    light = daylight * (15000 if scenario == "rain" else 70000)
    evaporation = (0.035 + max(temperature, 0) * 0.004 + daylight * 0.05 + 0.02) * (
        3.5 if scenario in ("drought", "heatwave") else 1
    )
    rain = 1.6 if scenario == "rain" else 0
    used = 0
    if zone.pump_on and scenario == "sensor_failure":
        stop_pump(db, territory_id, "Отказ датчика: полив остановлен до следующего шага")
    if zone.pump_on:
        remaining = max(0, (aware(zone.deadline) - aware(sim.clock)).total_seconds())
        used = max(
            0,
            min(
                FLOW_L_S * min(seconds, remaining),
                sim.reservoir_l - rule.min_reservoir_l,
                rule.daily_limit_l - zone.daily_water_l,
            ),
        )
        zone.run_water_l += used
        zone.daily_water_l += used
        sim.reservoir_l -= used
        sim.total_water_l += used
    sim.soil = max(0, min(100, sim.soil + (rain - evaporation) * seconds / 60 + used * 4.5))
    sim.clock = aware(sim.clock) + timedelta(seconds=seconds)
    sim.tick_index += 1
    sensor = db.scalar(
        select(m.Sensor).where(m.Sensor.territory_id == territory_id, m.Sensor.source == "simulated")
    )
    ingest(
        db,
        territory_id,
        Telemetry(
            sensor_id=sensor.id,
            timestamp=sim.clock,
            source="simulated",
            air_temperature_c=round(temperature, 2),
            air_humidity_pct=round(humidity, 2),
            soil_moisture_pct=round(sim.soil, 3) if scenario != "sensor_failure" else None,
            light_lux=round(light),
            pressure_hpa=1013,
            battery_pct=100,
            quality="invalid" if scenario == "sensor_failure" else "valid",
            raw_metadata={"scenario": scenario, "tick": sim.tick_index},
        ),
    )
    db.flush()
    refresh_alerts(db, territory_id)

