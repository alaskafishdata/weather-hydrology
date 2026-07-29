#!/usr/bin/env python3
"""
fetch-weather.py
Fetches weather observations for key Alaska fishing communities
from the NOAA National Weather Service API (api.weather.gov)
No API key required — free public JSON API.
"""
import json
import requests
from datetime import datetime, timezone

# NWS observation station IDs for key Alaska fishing locations
# Full list at: https://api.weather.gov/stations?state=AK
STATIONS = {
    "Kenai": {"station": "PAEN", "description": "Kenai Municipal Airport"},
    "Kodiak": {"station": "PADQ", "description": "Kodiak Airport"},
    "Bethel": {"station": "PABE", "description": "Bethel Airport (Kuskokwim/YK)"},
    "Cordova": {"station": "PACV", "description": "Merle K Smith Airport (Copper River)"},
    "Juneau": {"station": "PAJN", "description": "Juneau International Airport"},
    "Sitka": {"station": "PASI", "description": "Sitka Rocky Gutierrez Airport"},
    "Naknek": {"station": "PANC", "description": "Naknek / Bristol Bay area (via ANC proxy)"},
    "Dutch_Harbor": {"station": "PADU", "description": "Unalaska/Dutch Harbor Airport"},
    "Nome": {"station": "PAOM", "description": "Nome Airport (Norton Sound)"},
    "Dillingham": {"station": "PADL", "description": "Dillingham Airport (Bristol Bay)"},
}

NWS_BASE = "https://api.weather.gov"

def fetch_station_obs(station_id: str) -> dict | None:
    """Fetch latest observation from NWS station."""
    url = f"{NWS_BASE}/stations/{station_id}/observations/latest"
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "AlaskaFishData/1.0 (+https://alaskafishdata.com)",
            "Accept": "application/geo+json",
        })
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  ⚠ {station_id}: HTTP {resp.status_code}")
            return None
    except Exception as e:
        print(f"  ✗ {station_id}: {e}")
        return None


def kelvin_to_f(k: float | None) -> float | None:
    if k is None:
        return None
    return round((k - 273.15) * 9/5 + 32, 1)


def mps_to_mph(mps: float | None) -> float | None:
    if mps is None:
        return None
    return round(mps * 2.237, 1)


def main():
    now = datetime.now(timezone.utc).isoformat()
    observations = {}

    for location, info in STATIONS.items():
        print(f"  Fetching {location} ({info['station']})...")
        raw = fetch_station_obs(info["station"])

        if not raw:
            observations[location] = {
                "station": info["station"],
                "description": info["description"],
                "error": "fetch_failed",
                "fetched_at": now,
            }
            continue

        props = raw.get("properties", {})

        # Parse key fields
        temp_c = props.get("temperature", {}).get("value")
        wind_speed_mps = props.get("windSpeed", {}).get("value")
        wind_dir = props.get("windDirection", {}).get("value")
        visibility_m = props.get("visibility", {}).get("value")
        barometric_pa = props.get("barometricPressure", {}).get("value")
        text_desc = props.get("textDescription", "")
        icon_url = props.get("icon", "")

        observations[location] = {
            "station": info["station"],
            "description": info["description"],
            "observed_at": props.get("timestamp"),
            "fetched_at": now,
            "temp_f": kelvin_to_f(temp_c) if temp_c is not None else None,
            "temp_c": round(temp_c, 1) if temp_c is not None else None,
            "wind_speed_mph": mps_to_mph(wind_speed_mps),
            "wind_direction_deg": round(wind_dir, 0) if wind_dir is not None else None,
            "visibility_miles": round(visibility_m / 1609.34, 1) if visibility_m is not None else None,
            "barometric_pressure_mb": round(barometric_pa / 100, 1) if barometric_pa is not None else None,
            "conditions": text_desc,
            "icon": icon_url,
            "fishing_outlook": _fishing_outlook(temp_c, wind_speed_mps, text_desc),
        }
        print(f"    ✓ {location}: {kelvin_to_f(temp_c)}°F, {text_desc[:40]}")

    weather_output = {
        "_meta": {
            "source": "NOAA National Weather Service API",
            "source_url": "https://api.weather.gov/",
            "fetched_at": now,
            "update_frequency": "Hourly via GitHub Actions",
            "stations": len(observations),
        },
        "observations": observations,
    }

    with open("data/weather.json", "w") as f:
        json.dump(weather_output, f, indent=2)

    print(f"\n✓ data/weather.json: {len(observations)} stations")


def _fishing_outlook(temp_c: float | None, wind_mps: float | None, conditions: str) -> str:
    """Simple fishing outlook based on weather conditions."""
    if wind_mps is not None and wind_mps > 11:  # > 25 mph
        return "rough"
    if wind_mps is not None and wind_mps > 6.7:  # > 15 mph
        return "marginal"
    conditions_lower = conditions.lower()
    if any(w in conditions_lower for w in ["fog", "snow", "blizzard", "storm"]):
        return "marginal"
    if "clear" in conditions_lower or "fair" in conditions_lower:
        return "excellent"
    return "good"


if __name__ == "__main__":
    main()
