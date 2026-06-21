"""Diversion planning + emergency corridor generation.

Without a full routing graph we work at the corridor level: severe corridors
are paired with the nearest lighter corridor that can absorb spillover, and an
emergency corridor reserves the least-congested exit path from the venue. Both
return map-ready geometry (line segments) plus rationale.
"""
from __future__ import annotations

from typing import Dict, List

from . import predictor
from .geo import haversine_km
from .schemas import EventProfile

SEVERE_THRESHOLD = 70.0
RELIEF_TARGET = 60.0  # only divert onto corridors below this saturation


def diversion_plan(event: EventProfile) -> Dict:
    """Pair each severe corridor with the best nearby relief corridor."""
    forecast = predictor.predict_impact(event)
    affected = forecast["affected"]
    severe = [c for c in affected if c["congestion"] >= SEVERE_THRESHOLD]
    relief_pool = [c for c in affected if c["congestion"] < RELIEF_TARGET]

    plans: List[Dict] = []
    for s in severe:
        candidates = [
            (haversine_km((s["lat"], s["lon"]), (r["lat"], r["lon"])), r)
            for r in relief_pool
        ]
        candidates.sort(key=lambda t: t[0])
        if not candidates:
            continue
        dist, target = candidates[0]
        diverted = int(s["demand_vehicles"] * 0.30)
        plans.append({
            "from": s["corridor"],
            "to": target["corridor"],
            "from_lat": s["lat"], "from_lon": s["lon"],
            "to_lat": target["lat"], "to_lon": target["lon"],
            "distance_km": round(dist, 2),
            "diverted_vehicles": diverted,
            "from_congestion": s["congestion"],
            "to_congestion": target["congestion"],
            "rationale": (
                f"Divert ~{diverted:,} vehicles from {s['corridor']} "
                f"({s['congestion']:.0f}% saturated) onto {target['corridor']} "
                f"({target['congestion']:.0f}%), {round(dist,1)} km away."
            ),
        })
    return {
        "plans": plans,
        "summary": (f"{len(plans)} diversion(s) recommended to relieve "
                    f"{len(severe)} severe corridor(s).") if plans else
                   "No severe corridors require diversion.",
    }


def emergency_corridor(event: EventProfile) -> Dict:
    """Reserve the least-congested exit path from the venue for responders."""
    forecast = predictor.predict_impact(event)
    affected = sorted(forecast["affected"], key=lambda c: c["congestion"])
    if not affected:
        return {"corridor": None, "path": [], "summary": "No corridors in range."}

    chosen = affected[0]  # least congested = cleanest exit
    path = [
        [event.lat, event.lon],
        [chosen["lat"], chosen["lon"]],
    ]
    return {
        "corridor": chosen["corridor"],
        "congestion": chosen["congestion"],
        "path": path,
        "response_time_min": round(8 * (1 + chosen["congestion"] / 100.0), 1),
        "summary": (
            f"Reserved emergency corridor via {chosen['corridor']} "
            f"({chosen['congestion']:.0f}% saturation) -- the cleanest exit "
            f"for ambulances & fire services."
        ),
    }
