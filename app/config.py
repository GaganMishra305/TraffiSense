"""Central configuration for TraffiSense.ai.

All tunables live here so the rest of the codebase stays declarative.
Mappls keys are read from the environment (see .env.example) and never
hard-coded -- the frontend gracefully falls back to OpenStreetMap when
no key is present, so the demo always runs.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"

# The single source ASTraM dataset shipped in /data.
DATASET_CSV = next(DATA_DIR.glob("*.csv"))

# Bengaluru sits at UTC+5:30; the raw timestamps are UTC.
IST_OFFSET_HOURS = 5.5

# Mappls / MapMyIndia credentials (paste yours into a .env file).
MAPPLS_REST_KEY = os.getenv("MAPPLS_REST_KEY", "")
MAPPLS_MAP_SDK_KEY = os.getenv("MAPPLS_MAP_SDK_KEY", "")

# Geographic centre of Bengaluru -- the default map view.
CITY_CENTER = (12.9716, 77.5946)
DEFAULT_ZOOM = 11

# Event impact model tunables.
# Vehicles arriving per attendee (cars + cabs + two-wheelers averaged).
VEHICLES_PER_ATTENDEE = 0.42
# How far (km) an event's gravitational pull reaches into the network.
IMPACT_DECAY_KM = 4.5
# Junctions/corridors beyond this radius (km) are considered unaffected.
MAX_IMPACT_RADIUS_KM = 6.0

# Weather multipliers applied to demand & severity.
WEATHER_MULTIPLIERS = {
    "clear": 1.0,
    "cloudy": 1.05,
    "rain": 1.35,
    "heavy_rain": 1.7,
}

# Resource types the optimizer can deploy.
RESOURCE_TYPES = ["officers", "barricades", "marshals", "tow_trucks"]
