# Контракты GAIA

Версия REST API — `/api/v1`; интерактивная OpenAPI-схема доступна на `/docs`, JSON — на `/openapi.json`.

`telemetry.v1.schema.json` — единая модель показаний симулятора и Raspberry Pi. Источник обязателен. Проценты ограничены диапазоном 0–100, timestamp обязан содержать смещение и сохраняется в UTC. `quality=stale|invalid` запрещает автоматический запуск и останавливает работающий насос.

Устройство получает отдельные `sensor_id` и одноразово показанный ключ во вкладке «Настройки». Оно отправляет `POST /api/v1/devices/telemetry` с `Authorization: Bearer <device-key>`. Ключ не является пользовательской сессией и не даёт читать территорию. Сервер принимает только `source=device`, время в пределах пяти минут и строго более новые показания; ответы: `201`, `401`, `409` или `422`.

Пример:

```json
{
  "sensor_id": "9ed4f4c7-b9d8-4ff5-bcb0-1e8d83a4e70c",
  "timestamp": "2026-09-05T15:00:00Z",
  "source": "device",
  "air_temperature_c": 27.2,
  "air_humidity_pct": 44.1,
  "soil_moisture_pct": 31.8,
  "light_lux": 24000,
  "pressure_hpa": 1012.4,
  "battery_pct": 93,
  "quality": "valid",
  "raw_metadata": {"firmware": "0.1.0", "model": "garden-node"}
}
```
