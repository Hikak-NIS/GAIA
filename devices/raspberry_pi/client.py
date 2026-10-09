"""Minimal Raspberry Pi telemetry sender; GPIO control is intentionally absent."""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone


def send_reading(reading: dict) -> None:
    base_url = os.environ.get("GAIA_API_BASE", "http://127.0.0.1:8000")
    api_key = os.environ["GAIA_DEVICE_API_KEY"]
    request = urllib.request.Request(
        f"{base_url}/api/v1/devices/telemetry",
        data=json.dumps(reading).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(response.read().decode())
    except urllib.error.HTTPError as error:
        raise SystemExit(f"GAIA rejected telemetry: {error.code} {error.read().decode()}") from error


if __name__ == "__main__":
    send_reading(
        {
            "sensor_id": os.environ["GAIA_SENSOR_ID"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "device",
            "air_temperature_c": float(os.environ.get("GAIA_SAMPLE_TEMPERATURE", "24.5")),
            "air_humidity_pct": float(os.environ.get("GAIA_SAMPLE_HUMIDITY", "52")),
            "soil_moisture_pct": float(os.environ.get("GAIA_SAMPLE_SOIL", "36")),
            "light_lux": float(os.environ.get("GAIA_SAMPLE_LIGHT", "12000")),
            "quality": "valid",
            "raw_metadata": {"firmware": "example-0.1.0", "model": "raspberry-pi"},
        }
    )
