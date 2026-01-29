from __future__ import annotations

import requests


def get_hourly_forecast(lat: float, lon: float) -> dict:
    # Open-Meteo: no API key required.
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,precipitation_probability,wind_speed_10m"
        "&forecast_days=3"
        "&timezone=UTC"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()
