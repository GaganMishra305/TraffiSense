"""ASTraM dataset loader + intelligence layer.

Loads the anonymized Bengaluru traffic-police incident export once, cleans
it, and derives the reusable aggregates (corridor risk, junction hotspots,
temporal patterns) that every downstream model leans on. Everything is
cached in-process so the API stays snappy.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

import numpy as np
import pandas as pd

from . import config
from .geo import Coord

# Bengaluru bounding box -- drops the handful of stray/garbage coordinates.
_LAT_RANGE = (12.7, 13.3)
_LON_RANGE = (77.2, 77.85)


@lru_cache(maxsize=1)
def load_incidents() -> pd.DataFrame:
    """Return the cleaned incident DataFrame (cached for the process)."""
    df = pd.read_csv(config.DATASET_CSV, low_memory=False)

    # Numeric coordinates, drop anything outside Bengaluru.
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df[
        df["latitude"].between(*_LAT_RANGE)
        & df["longitude"].between(*_LON_RANGE)
    ].copy()

    # Timestamps -> local Bengaluru time (IST). Drop rows we can't time.
    ts = pd.to_datetime(df["start_datetime"], errors="coerce", utc=True)
    ist = ts + pd.Timedelta(hours=config.IST_OFFSET_HOURS)
    df["ts_ist"] = ist
    df = df[df["ts_ist"].notna()].copy()
    df["hour"] = df["ts_ist"].dt.hour
    df["weekday"] = df["ts_ist"].dt.weekday  # 0 = Monday
    df["is_weekend"] = df["weekday"] >= 5

    # Tidy categoricals.
    df["corridor"] = df["corridor"].fillna("Non-corridor").replace("", "Non-corridor")
    df["priority"] = df["priority"].fillna("Low")
    df["is_high"] = df["priority"].str.lower().eq("high")
    df["closure"] = df["requires_road_closure"].astype(str).str.upper().eq("TRUE")
    df["event_cause"] = df["event_cause"].fillna("others").replace("", "others")
    df["junction"] = df["junction"].where(df["junction"].notna(), None)

    df = df.reset_index(drop=True)
    return df


@lru_cache(maxsize=1)
def corridor_profiles() -> List[Dict]:
    """Per-corridor risk profile, sorted by incident volume."""
    df = load_incidents()
    rows: List[Dict] = []
    for name, g in df.groupby("corridor"):
        rows.append(
            {
                "corridor": name,
                "incidents": int(len(g)),
                "high_priority_rate": round(float(g["is_high"].mean()), 3),
                "closure_rate": round(float(g["closure"].mean()), 3),
                "lat": round(float(g["latitude"].mean()), 6),
                "lon": round(float(g["longitude"].mean()), 6),
                "peak_hour": int(g["hour"].mode().iloc[0]) if len(g) else 0,
                "top_cause": g["event_cause"].mode().iloc[0] if len(g) else "others",
            }
        )
    rows.sort(key=lambda r: r["incidents"], reverse=True)
    # Normalised 0-100 risk score blending volume, severity and closures.
    max_inc = max((r["incidents"] for r in rows), default=1)
    for r in rows:
        vol = r["incidents"] / max_inc
        r["risk_score"] = round(
            100 * (0.55 * vol + 0.3 * r["high_priority_rate"] + 0.15 * r["closure_rate"]),
            1,
        )
    return rows


@lru_cache(maxsize=1)
def junction_profiles() -> List[Dict]:
    """Named junctions with >=3 incidents -- the chronic hotspots."""
    df = load_incidents()
    named = df[df["junction"].notna()]
    rows: List[Dict] = []
    for name, g in named.groupby("junction"):
        if len(g) < 3:
            continue
        rows.append(
            {
                "junction": name,
                "incidents": int(len(g)),
                "high_priority_rate": round(float(g["is_high"].mean()), 3),
                "lat": round(float(g["latitude"].mean()), 6),
                "lon": round(float(g["longitude"].mean()), 6),
                "corridor": g["corridor"].mode().iloc[0],
                "peak_hour": int(g["hour"].mode().iloc[0]),
            }
        )
    rows.sort(key=lambda r: r["incidents"], reverse=True)
    return rows


@lru_cache(maxsize=1)
def temporal_pattern() -> Dict:
    """Incident counts by hour-of-day and weekday for the whole city."""
    df = load_incidents()
    by_hour = df.groupby("hour").size().reindex(range(24), fill_value=0)
    by_weekday = df.groupby("weekday").size().reindex(range(7), fill_value=0)
    return {
        "by_hour": [int(x) for x in by_hour.values],
        "by_weekday": [int(x) for x in by_weekday.values],
    }


@lru_cache(maxsize=1)
def cause_breakdown() -> List[Dict]:
    """Top incident causes city-wide."""
    df = load_incidents()
    vc = df["event_cause"].value_counts().head(10)
    return [{"cause": k, "count": int(v)} for k, v in vc.items()]


def heatmap_points(max_points: int = 2500) -> List[List[float]]:
    """Down-sampled [lat, lon, weight] list for the congestion heatmap."""
    df = load_incidents()
    if len(df) > max_points:
        df = df.sample(max_points, random_state=7)
    weight = np.where(df["is_high"], 1.0, 0.5)
    return [
        [round(float(la), 6), round(float(lo), 6), float(w)]
        for la, lo, w in zip(df["latitude"], df["longitude"], weight)
    ]


def historical_risk_at(point: Coord, radius_km: float) -> float:
    """Local incident density (severity-weighted) near a point, 0-1 scaled.

    Used by the predictor to ground event forecasts in real history.
    """
    from .geo import haversine_km

    df = load_incidents()
    # Coarse bbox prefilter for speed before the exact haversine pass.
    dlat = radius_km / 111.0
    dlon = radius_km / 100.0
    box = df[
        df["latitude"].between(point[0] - dlat, point[0] + dlat)
        & df["longitude"].between(point[1] - dlon, point[1] + dlon)
    ]
    if box.empty:
        return 0.0
    score = 0.0
    for la, lo, hi in zip(box["latitude"], box["longitude"], box["is_high"]):
        d = haversine_km(point, (la, lo))
        if d <= radius_km:
            score += (1.0 if hi else 0.5) * (1 - d / radius_km)
    # Scale against a busy-corridor reference so output lands in ~0-1.
    return round(min(score / 120.0, 1.0), 4)
