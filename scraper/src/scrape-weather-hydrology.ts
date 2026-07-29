import * as fs from "fs/promises";
import * as path from "path";

const OUTPUT_DIR = path.join(process.cwd(), "data");

// USGS NWIS station IDs for Alaska river gauge monitoring
// Maps to rivers in alaskafishdata.com river directory
const USGS_STATIONS: { id: string; name: string; slug: string; paramCd: string }[] = [
  { id: "15266300", name: "Kenai River at Soldotna",             slug: "kenai-river",               paramCd: "00060,00065,00010" },
  { id: "15292000", name: "Deshka River near Houston",           slug: "deshka-river",              paramCd: "00060,00065" },
  { id: "15294000", name: "Little Susitna River near Palmer",    slug: "little-susitna-river",      paramCd: "00060,00065" },
  { id: "15212100", name: "Copper River at Million Dollar Bridge",slug: "copper-river-miles-lake",   paramCd: "00060,00065" },
  { id: "15290000", name: "Kasilof River near Kasilof",          slug: "kasilof-river-sockeye",     paramCd: "00060,00065" },
  { id: "15258000", name: "Russian River near Cooper Landing",   slug: "russian-river",             paramCd: "00060,00065" },
  { id: "15484000", name: "Chena River at Fairbanks",            slug: "salcha-river",              paramCd: "00060,00065" },
  { id: "15304000", name: "Susitna River near Talkeetna",        slug: "crooked-creek",             paramCd: "00060,00065" },
];

// NOAA NWS weather stations for major Alaska hubs
const NOAA_STATIONS: { id: string; name: string; region: string }[] = [
  { id: "PANC", name: "Anchorage Ted Stevens International",     region: "Southcentral" },
  { id: "PAJN", name: "Juneau International Airport",            region: "Southeast" },
  { id: "PAKN", name: "King Salmon Airport",                     region: "Bristol Bay" },
  { id: "PADK", name: "Kodiak Airport",                          region: "Kodiak" },
  { id: "PACD", name: "Cold Bay Airport",                        region: "Westward" },
  { id: "PFNO", name: "Nome Airport",                            region: "Arctic-Yukon-Kuskokwim" },
];

const USGS_BASE = "https://waterservices.usgs.gov/nwis/iv/";
const NOAA_BASE = "https://api.weather.gov/stations";

async function fetchUSGSGauge(station: typeof USGS_STATIONS[0]) {
  const url = `${USGS_BASE}?format=json&sites=${station.id}&parameterCd=${station.paramCd}&siteStatus=active`;
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "AlaskaFishData-PublicDataBot/1.0 (github.com/alaskafishdata/weather-hydrology)" }
    });
    if (!res.ok) return null;
    const json = await res.json() as any;

    const timeSeries = json?.value?.timeSeries || [];
    const readings: Record<string, any> = {};

    for (const series of timeSeries) {
      const varCode = series.variable?.variableCode?.[0]?.value;
      const latestValue = series.values?.[0]?.value?.[0];
      if (varCode && latestValue) {
        const val = parseFloat(latestValue.value);
        const unitCode = series.variable?.unit?.unitCode;
        if (varCode === "00060") readings.discharge = { value: val, unit: unitCode || "ft3/s", dateTime: latestValue.dateTime };
        if (varCode === "00065") readings.gaugeHeight = { value: val, unit: unitCode || "ft", dateTime: latestValue.dateTime };
        if (varCode === "00010") readings.waterTemp = { value: val, unit: unitCode || "°C", dateTime: latestValue.dateTime };
      }
    }

    return {
      stationId: station.id,
      name: station.name,
      slug: station.slug,
      ...readings,
    };
  } catch (e) {
    console.warn(`  [WARN] USGS ${station.id}: ${e}`);
    return null;
  }
}

async function fetchNOAAWeather(station: typeof NOAA_STATIONS[0]) {
  const url = `${NOAA_BASE}/${station.id}/observations/latest`;
  try {
    const res = await fetch(url, {
      headers: {
        "User-Agent": "AlaskaFishData-PublicDataBot/1.0 (github.com/alaskafishdata/weather-hydrology)",
        "Accept": "application/geo+json"
      }
    });
    if (!res.ok) return null;
    const json = await res.json() as any;
    const props = json?.properties || {};

    return {
      stationId: station.id,
      name: station.name,
      region: station.region,
      timestamp: props.timestamp,
      temperature: props.temperature?.value !== null ? {
        value: props.temperature.value,
        unit: "°C",
      } : null,
      windSpeed: props.windSpeed?.value !== null ? {
        value: props.windSpeed.value,
        unit: "km/h",
      } : null,
      windDirection: props.windDirection?.value ?? null,
      precipitation: props.precipitationLastHour?.value !== null ? {
        value: props.precipitationLastHour?.value,
        unit: "mm",
      } : null,
      textDescription: props.textDescription ?? null,
    };
  } catch (e) {
    console.warn(`  [WARN] NOAA ${station.id}: ${e}`);
    return null;
  }
}

async function main() {
  console.log("AlaskaFishData | Weather & Hydrology Scraper");
  console.log("Sources: USGS NWIS (streamflow) + NOAA NWS (weather observations)");
  console.log(`Run: ${new Date().toISOString()}\n`);

  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  // Fetch USGS streamflow gauges
  console.log(`Fetching ${USGS_STATIONS.length} USGS streamflow stations...`);
  const hydrologyResults = await Promise.all(USGS_STATIONS.map(fetchUSGSGauge));
  const hydrology = hydrologyResults.filter(Boolean);
  console.log(`  → ${hydrology.length} stations returned data`);

  // Fetch NOAA weather observations
  console.log(`\nFetching ${NOAA_STATIONS.length} NOAA weather stations...`);
  const weatherResults = await Promise.all(NOAA_STATIONS.map(fetchNOAAWeather));
  const weather = weatherResults.filter(Boolean);
  console.log(`  → ${weather.length} stations returned data`);

  await fs.writeFile(
    path.join(OUTPUT_DIR, "hydrology.json"),
    JSON.stringify({
      _meta: {
        source: "USGS National Water Information System (NWIS)",
        sourceUrl: "https://waterservices.usgs.gov/nwis/iv/",
        generated: new Date().toISOString(),
        count: hydrology.length,
      },
      stations: hydrology,
    }, null, 2)
  );

  await fs.writeFile(
    path.join(OUTPUT_DIR, "weather.json"),
    JSON.stringify({
      _meta: {
        source: "NOAA National Weather Service API",
        sourceUrl: "https://api.weather.gov/",
        generated: new Date().toISOString(),
        count: weather.length,
      },
      stations: weather,
    }, null, 2)
  );

  console.log(`\n✓ Wrote data/hydrology.json (${hydrology.length} stations)`);
  console.log(`✓ Wrote data/weather.json (${weather.length} stations)`);
}

main().catch(console.error);
