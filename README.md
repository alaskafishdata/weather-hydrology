# weather-hydrology

> **Public data repo** — USGS NWIS streamflow gauges + NOAA NWS weather observations for Alaska fishing regions
> Part of the [alaskafishdata](https://github.com/alaskafishdata) public data network.

## Data Files

| File | Description | Updated |
|------|-------------|---------|
| `data/hydrology.json` | USGS NWIS streamflow gauge readings (discharge, height, temperature) | Every hour |
| `data/weather.json` | NOAA NWS weather observations at major Alaska hubs | Every hour |

## Station Coverage

**Hydrology:** Kenai River at Soldotna, Deshka River, Little Susitna River, Copper River, Kasilof River, Russian River, Chena River, Susitna River near Talkeetna.

**Weather:** Anchorage (PANC), Juneau (PAJN), King Salmon (PAKN), Kodiak (PADK), Cold Bay (PACD), Nome (PFNO).

## Sources

- **USGS NWIS Instantaneous Values** — https://waterservices.usgs.gov/nwis/iv/
- **NOAA NWS API** — https://api.weather.gov/

## Raw API Usage

```
https://raw.githubusercontent.com/alaskafishdata/weather-hydrology/main/data/hydrology.json
https://raw.githubusercontent.com/alaskafishdata/weather-hydrology/main/data/weather.json
```

## License

Data sourced from USGS and NOAA (public domain). Code: MIT License.
