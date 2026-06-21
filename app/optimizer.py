"""Resource deployment optimizer.

Given an event forecast, decides where to put limited resources (officers,
barricades, marshals, tow trucks) to buy the most congestion relief per unit.
Uses a transparent marginal-need allocation: each candidate deployment point
gets a need score, resources flow to the highest need first, and every
allocation ships with a plain-English rationale.
"""
from __future__ import annotations

import math
from typing import Dict, List

from . import config, data, predictor
from .geo import haversine_km
from .schemas import EventProfile


def _deployment_points(event: EventProfile) -> List[Dict]:
    """Candidate spots = impacted corridors + chronic junctions nearby."""
    forecast = predictor.predict_impact(event)
    points: List[Dict] = []
    max_inc = max((c["historical_incidents"] for c in forecast["affected"]),
                  default=1)

    for c in forecast["affected"]:
        need = (0.5 * c["congestion"] / 100.0
                + 0.3 * c["closure_risk"]
                + 0.2 * c["historical_incidents"] / max_inc)
        points.append({
            "id": c["corridor"], "kind": "corridor",
            "lat": c["lat"], "lon": c["lon"],
            "congestion": c["congestion"], "closure_risk": c["closure_risk"],
            "incidents": c["historical_incidents"], "need": round(need, 4),
        })

    venue = (event.lat, event.lon)
    for j in data.junction_profiles():
        d = haversine_km(venue, (j["lat"], j["lon"]))
        if d > config.MAX_IMPACT_RADIUS_KM:
            continue
        need = 0.4 * j["high_priority_rate"] + 0.6 * min(j["incidents"] / 50.0, 1.0)
        points.append({
            "id": j["junction"], "kind": "junction",
            "lat": j["lat"], "lon": j["lon"],
            "congestion": None, "closure_risk": None,
            "incidents": j["incidents"], "need": round(need, 4),
        })

    points.sort(key=lambda p: p["need"], reverse=True)
    return points[:12]  # keep the command picture readable


def _totals(event: EventProfile) -> Dict[str, int]:
    """Resource budget scaled to event size + weather."""
    weather = config.WEATHER_MULTIPLIERS.get(event.weather, 1.0)
    a = event.attendance * weather
    return {
        "officers": max(8, math.ceil(a / 1800)),
        "barricades": max(6, math.ceil(a / 2500)),
        "marshals": max(4, math.ceil(a / 4000)),
        "tow_trucks": max(2, math.ceil(a / 12000)),
    }


def optimize_resources(event: EventProfile) -> Dict:
    """Allocate each resource type across deployment points by need."""
    points = _deployment_points(event)
    totals = _totals(event)
    if not points:
        return {"totals": totals, "deployments": [], "summary":
                "No deployment points within range."}

    need_sum = sum(p["need"] for p in points) or 1.0
    deployments: List[Dict] = []
    for p in points:
        share = p["need"] / need_sum
        alloc = {r: int(round(totals[r] * share)) for r in config.RESOURCE_TYPES}
        # Guarantee the highest-need spots get a minimum presence.
        if p["need"] >= 0.5:
            alloc["officers"] = max(alloc["officers"], 2)
        if not any(alloc.values()):
            continue
        deployments.append({
            **{k: p[k] for k in ("id", "kind", "lat", "lon", "congestion",
                                 "incidents", "need")},
            "allocation": alloc,
        })

    # Reconcile rounding so totals match the stated budget, then attach the
    # explainable rationale + relief estimate AFTER allocations are final.
    _reconcile(deployments, totals)
    for d in deployments:
        share = d["need"] / need_sum
        d["expected_relief_pct"] = round(min(35.0, 8 + 90 * share), 1)
        d["rationale"] = _rationale(d, d["allocation"], d["expected_relief_pct"])

    return {
        "totals": totals,
        "deployments": deployments,
        "summary": (
            f"Deploying {totals['officers']} officers, {totals['barricades']} "
            f"barricades, {totals['marshals']} marshals and {totals['tow_trucks']} "
            f"tow trucks across {len(deployments)} priority points."
        ),
    }


def _rationale(p: Dict, alloc: Dict, relief: float) -> str:
    where = f"{p['id']} ({p['kind']})"
    if p["kind"] == "corridor" and p["congestion"] is not None:
        why = (f"predicted {p['congestion']:.0f}% saturation, "
               f"{p['incidents']} historical incidents")
    else:
        why = f"chronic hotspot with {p['incidents']} historical incidents"
    return (
        f"Deploy {alloc['officers']} officers + {alloc['barricades']} barricades "
        f"at {where} because {why}; projected {relief:.0f}% queue reduction."
    )


def _reconcile(deployments: List[Dict], totals: Dict[str, int]) -> None:
    """Absorb rounding remainder on the LOWEST-priority deployment so the
    highest-need points are never starved of resources."""
    if not deployments:
        return
    sink = deployments[-1]
    for r in config.RESOURCE_TYPES:
        used = sum(d["allocation"][r] for d in deployments)
        diff = totals[r] - used
        if diff != 0:
            sink["allocation"][r] = max(0, sink["allocation"][r] + diff)
