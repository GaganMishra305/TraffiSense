"""Traffic-impact predictor.

Fuses three signals into a per-corridor congestion forecast for an event:
  1. Event demand  -- a gravity model spreading attendee vehicles across the
     surrounding corridors, decaying with distance.
  2. Historical risk -- real ASTraM incident density near each corridor.
  3. ML closure propensity -- learned probability that disruptions escalate.

Output is fully explainable: every number traces back to a stated driver.
"""
from __future__ import annotations

from typing import Dict, List

from . import config, data, ml
from .geo import Coord, gaussian_decay, haversine_km
from .schemas import EventProfile

# Smooth time-of-day baseline congestion (0-1) for Bengaluru arterials.
_HOURLY_BASE = [
    0.20, 0.15, 0.12, 0.12, 0.15, 0.25, 0.45, 0.70, 0.85, 0.80,
    0.65, 0.60, 0.62, 0.60, 0.58, 0.62, 0.70, 0.85, 0.92, 0.88,
    0.70, 0.55, 0.42, 0.30,
]


def _event_demand_vehicles(event: EventProfile) -> int:
    """Total inbound+outbound vehicle trips the event generates."""
    weather = config.WEATHER_MULTIPLIERS.get(event.weather, 1.0)
    return int(event.attendance * config.VEHICLES_PER_ATTENDEE * weather)


def predict_impact(event: EventProfile) -> Dict:
    """Forecast congestion on corridors within the event's impact radius."""
    venue: Coord = (event.lat, event.lon)
    total_vehicles = _event_demand_vehicles(event)
    vol_lookup = ml.corridor_volume_lookup()
    weather_mult = config.WEATHER_MULTIPLIERS.get(event.weather, 1.0)

    # 1) Gather candidate corridors within range + their gravity weights.
    #    "Non-corridor" is a catch-all bucket, not a routable road -> skip it.
    candidates = []
    for prof in data.corridor_profiles():
        if prof["corridor"] == "Non-corridor":
            continue
        dist = haversine_km(venue, (prof["lat"], prof["lon"]))
        if dist > config.MAX_IMPACT_RADIUS_KM:
            continue
        weight = gaussian_decay(dist, config.IMPACT_DECAY_KM)
        candidates.append((prof, dist, weight))

    if not candidates:
        return {"affected": [], "summary": _empty_summary(event, total_vehicles)}

    weight_sum = sum(w for _, _, w in candidates) or 1.0
    # ~40% of all event trips concentrate in the single peak arrival hour.
    peak_hour_vehicles = total_vehicles * 0.40

    # 2) Distribute demand + build the per-corridor forecast.
    affected: List[Dict] = []
    for prof, dist, weight in candidates:
        share = weight / weight_sum
        corridor_vehicles = int(peak_hour_vehicles * share)
        corridor_vol = vol_lookup.get(prof["corridor"], 0.15)

        base = _HOURLY_BASE[event.start_hour]
        # Event load vs a ~3000 veh/hr multi-lane arterial reference.
        event_load = min(corridor_vehicles / 3000.0, 1.5)
        history = prof["risk_score"] / 100.0
        raw = (0.42 * base + 0.43 * event_load + 0.15 * history) * weather_mult
        congestion = min(100.0, 100.0 * raw)

        closure_prob = ml.closure_propensity(
            event.start_hour, event.weekday, corridor_vol,
            high_priority=prof["high_priority_rate"] > 0.5,
            cause="accident", heavy=True,
        )
        delay = round(_delay_minutes(congestion), 1)
        peak_hour = max(event.start_hour, prof["peak_hour"])

        affected.append({
            "corridor": prof["corridor"],
            "lat": prof["lat"],
            "lon": prof["lon"],
            "distance_km": round(dist, 2),
            "demand_vehicles": corridor_vehicles,
            "congestion": round(congestion, 1),
            "severity": _severity_label(congestion),
            "delay_min": delay,
            "closure_risk": round(closure_prob, 3),
            "peak_window": f"{peak_hour:02d}:00-{(peak_hour + 1) % 24:02d}:00",
            "historical_incidents": prof["incidents"],
            "rationale": _corridor_rationale(
                prof, corridor_vehicles, congestion, delay, closure_prob
            ),
        })

    affected.sort(key=lambda a: a["congestion"], reverse=True)
    return {
        "affected": affected,
        "summary": _build_summary(event, total_vehicles, affected),
    }


def _delay_minutes(congestion: float) -> float:
    """Convex delay curve -- pain rises sharply past ~70% saturation."""
    x = congestion / 100.0
    return 60.0 * (x ** 2.4)


def _severity_label(c: float) -> str:
    if c >= 85:
        return "gridlock"
    if c >= 70:
        return "severe"
    if c >= 50:
        return "heavy"
    if c >= 30:
        return "moderate"
    return "light"


def _corridor_rationale(prof, vehicles, congestion, delay, closure) -> str:
    return (
        f"{vehicles:,} event vehicles routed onto {prof['corridor']} "
        f"(historically {prof['incidents']} incidents, peak {prof['peak_hour']:02d}:00) "
        f"-> {congestion:.0f}% saturation, ~{delay:.0f} min added delay. "
        f"Closure probability {closure*100:.0f}% (ML)."
    )


def _build_summary(event, total_vehicles, affected) -> Dict:
    worst = affected[0]
    severe = [a for a in affected if a["congestion"] >= 70]
    radius = max((a["distance_km"] for a in severe), default=0.0)
    return {
        "event_name": event.name,
        "total_vehicles": total_vehicles,
        "corridors_affected": len(affected),
        "severe_corridors": len(severe),
        "worst_corridor": worst["corridor"],
        "worst_congestion": worst["congestion"],
        "peak_period": worst["peak_window"],
        "congestion_radius_km": round(radius, 2),
        "avg_delay_min": round(
            sum(a["delay_min"] for a in affected) / len(affected), 1
        ),
        "headline": (
            f"{worst['corridor']} expected to hit {worst['congestion']:.0f}% "
            f"saturation ({worst['severity']}) around {worst['peak_window']}."
        ),
    }


def _empty_summary(event, total_vehicles) -> Dict:
    return {
        "event_name": event.name,
        "total_vehicles": total_vehicles,
        "corridors_affected": 0,
        "severe_corridors": 0,
        "worst_corridor": None,
        "worst_congestion": 0,
        "peak_period": None,
        "congestion_radius_km": 0,
        "avg_delay_min": 0,
        "headline": "No mapped corridors fall within this event's impact radius.",
    }
