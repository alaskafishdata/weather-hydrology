#!/usr/bin/env python3
"""
fetch-hydrology.py
Fetches real-time USGS streamflow data for major Alaska salmon rivers.
Uses the USGS Water Services REST API — no auth required.
Docs: https://waterservices.usgs.gov/rest/IV-Service.html
"""
import json
import requests
from datetime import datetime, timezone

# USGS NWIS site numbers for major Alaska salmon rivers
# Parameter code 00060 = discharge in cubic feet per second (cfs)
GAUGES = {
    "kenai_at_soldotna": {
        "site_no": "15266300",
        "description": "Kenai River at Soldotna, AK",
        "river": "Kenai River",
        "region": "Upper Cook Inlet",
        "salmon_relevance": "Primary flow gauge for Kenai sonar adjustment factors",
        "typical_june_cfs": 12400,
        "typical_july_cfs": 18600,
        "typical_aug_cfs": 14200,
    },
    "copper_near_chitina": {
        "site_no": "15214000",
        "description": "Copper River near Chitina, AK",
        "river": "Copper River",
        "region": "Prince William Sound",
        "salmon_relevance": "Copper River commercial salmon fishery management",
        "typical_june_cfs": 124000,
        "typical_july_cfs": 168000,
        "typical_aug_cfs": 142000,
    },
    "susitna_near_talkeetna": {
        "site_no": "15292000",
        "description": "Susitna River near Talkeetna, AK",
        "river": "Susitna River",
        "region": "Upper Cook Inlet",
        "salmon_relevance": "UCI Chinook and sockeye migration flows",
        "typical_june_cfs": 42000,
        "typical_july_cfs": 68000,
        "typical_aug_cfs": 56000,
    },
    "yukon_at_ruby": {
        "site_no": "15565447",
        "description": "Yukon River at Ruby, AK",
        "river": "Yukon River",
        "region": "Interior",
        "salmon_relevance": "Yukon Chinook salmon management flows",
        "typical_june_cfs": 248000,
        "typical_july_cfs": 284000,
        "typical_aug_cfs": 212000,
    },
    "kuskokwim_at_bethel": {
        "site_no": "15304000",
        "description": "Kuskokwim River at Bethel, AK",
        "river": "Kuskokwim River",
        "region": "Western Alaska",
        "salmon_relevance": "Kuskokwim subsistence fisheries management",
        "typical_june_cfs": 88000,
        "typical_july_cfs": 112000,
        "typical_aug_cfs": 86000,
    },
}

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"


def fetch_gauge(site_no: str) -> dict | None:
    """Fetch latest instantaneous value from USGS NWIS."""
    params = {
        "sites": site_no,
        "parameterCd": "00060",  # Discharge, cfs
        "siteStatus": "active",
        "format": "json",
        "period": "PT1H",  # Last 1 hour
    }
    try:
        resp = requests.get(USGS_IV_URL, params=params, timeout=15, headers={
            "User-Agent": "AlaskaFishData/1.0 (+https://alaskafishdata.com)"
        })
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ✗ Site {site_no}: {e}")
        return None


def flow_status(current_cfs: float, typical_cfs: float) -> str:
    """Classify flow relative to typical seasonal levels."""
    if typical_cfs <= 0:
        return "unknown"
    ratio = current_cfs / typical_cfs
    if ratio > 1.5:
        return "high"
    elif ratio > 1.2:
        return "above_normal"
    elif ratio > 0.8:
        return "normal"
    elif ratio > 0.5:
        return "below_normal"
    else:
        return "low"


def main():
    now = datetime.now(timezone.utc)
    month = now.month
    readings = {}

    for gauge_key, gauge_info in GAUGES.items():
        print(f"  Fetching {gauge_info['description']}...")
        raw = fetch_gauge(gauge_info["site_no"])

        if not raw:
            readings[gauge_key] = {
                **gauge_info,
                "current_cfs": None,
                "fetched_at": now.isoformat(),
                "error": "fetch_failed",
            }
            continue

        # Parse USGS JSON format
        try:
            ts_series = raw["value"]["timeSeries"]
            if not ts_series:
                raise ValueError("No time series data")

            values = ts_series[0]["values"][0]["value"]
            if not values:
                raise ValueError("No values")

            latest = values[-1]
            current_cfs = float(latest["value"])
            observed_at = latest["dateTime"]

            # Typical seasonal flow based on month
            if month in [6]:
                typical = gauge_info["typical_june_cfs"]
            elif month in [7]:
                typical = gauge_info["typical_july_cfs"]
            elif month in [8, 9]:
                typical = gauge_info["typical_aug_cfs"]
            else:
                typical = (gauge_info["typical_june_cfs"] + gauge_info["typical_july_cfs"]) / 2

            readings[gauge_key] = {
                **gauge_info,
                "current_cfs": current_cfs,
                "observed_at": observed_at,
                "fetched_at": now.isoformat(),
                "flow_status": flow_status(current_cfs, typical),
                "pct_of_seasonal_typical": round(current_cfs / typical * 100, 1),
                "usgs_url": f"https://waterdata.usgs.gov/nwis/uv?site_no={gauge_info['site_no']}",
            }
            print(f"    ✓ {current_cfs:,.0f} cfs ({readings[gauge_key]['flow_status']})")

        except (KeyError, IndexError, ValueError) as e:
            print(f"  ✗ Parse error for {gauge_key}: {e}")
            readings[gauge_key] = {
                **gauge_info,
                "current_cfs": None,
                "fetched_at": now.isoformat(),
                "error": f"parse_error: {e}",
            }

    output = {
        "_meta": {
            "source": "USGS National Water Information System (NWIS) — Instantaneous Values",
            "source_url": "https://waterservices.usgs.gov/",
            "fetched_at": now.isoformat(),
            "update_frequency": "Hourly via GitHub Actions",
            "parameter": "Discharge (00060) in cubic feet per second (cfs)",
            "gauge_count": len(readings),
        },
        "gauges": readings,
    }

    with open("data/hydrology.json", "w") as f:
        json.dump(output, f, indent=2)

    ok = sum(1 for r in readings.values() if r.get("current_cfs") is not None)
    print(f"\n✓ data/hydrology.json: {ok}/{len(readings)} gauges successfully fetched")


if __name__ == "__main__":
    main()
