"""Lightweight digital-twin simulator + scenario comparison.

We don't ship a full SUMO microsimulation (heavy, fragile on a demo stage).
Instead we model the network as the set of impacted corridors and apply a
transparent macroscopic flow model: each management strategy reshapes the
congestion distribution, and we derive operational KPIs (travel time, queue,
throughput, fuel, emissions, emergency response) from that distribution.
"""
from __future__ import annotations

import copy
from typing import Dict, List

from . import predictor
from .schemas import EventProfile

# How each strategy reshapes congestion. (worst_relief, network_relief,
# spillover) -- worst_relief eases the most-loaded corridors, network_relief
# eases everything, spillover is congestion pushed onto lighter corridors.
STRATEGIES: Dict[str, Dict] = {
    "baseline": {"label": "No intervention", "worst": 0.0, "net": 0.0, "spill": 0.0},
    "diversions": {"label": "Diversions only", "worst": 0.28, "net": 0.05, "spill": 0.10},
    "signals": {"label": "Adaptive signals", "worst": 0.12, "net": 0.16, "spill": 0.0},
    "full": {"label": "Full optimization", "worst": 0.34, "net": 0.22, "spill": 0.06},
    "emergency": {"label": "Emergency mode", "worst": 0.30, "net": 0.10, "spill": 0.14},
}


def simulate(event: EventProfile, strategy: str = "baseline") -> Dict:
    """Run the macroscopic model for one strategy and return KPIs."""
    cfg = STRATEGIES.get(strategy, STRATEGIES["baseline"])
    forecast = predictor.predict_impact(event)
    corridors = copy.deepcopy(forecast["affected"])
    if not corridors:
        return {"strategy": strategy, "label": cfg["label"], "metrics": _zero_metrics(),
                "corridors": []}

    congs = [c["congestion"] for c in corridors]
    worst = max(congs)

    for c in corridors:
        relief = cfg["net"] + (cfg["worst"] if c["congestion"] >= 0.85 * worst else 0)
        new_c = c["congestion"] * (1 - relief)
        # Spillover lifts the lighter half of the network slightly.
        if c["congestion"] < 0.6 * worst:
            new_c = min(100.0, new_c * (1 + cfg["spill"]))
        c["congestion"] = round(max(0.0, new_c), 1)
        c["delay_min"] = round(predictor._delay_minutes(c["congestion"]), 1)
        c["severity"] = predictor._severity_label(c["congestion"])

    metrics = _kpis(corridors, event)
    metrics["strategy"] = strategy
    metrics["label"] = cfg["label"]
    return {"strategy": strategy, "label": cfg["label"],
            "metrics": metrics, "corridors": corridors}


def _kpis(corridors: List[Dict], event: EventProfile) -> Dict:
    n = len(corridors)
    congs = [c["congestion"] / 100.0 for c in corridors]
    avg_c = sum(congs) / n
    delays = [c["delay_min"] for c in corridors]

    # Free-flow ~12 min crossing; travel time grows convexly with saturation.
    avg_travel = round(12 * (1 + 2.2 * avg_c ** 2), 1)
    # Queue: empirical metres per corridor at this saturation.
    max_queue = round(max(congs) * 1200, 0)
    # Throughput: capacity actually served (drops past saturation).
    throughput = round(sum(min(c, 0.95) * 3000 for c in congs) * 0.6, 0)
    vehicles = sum(c["demand_vehicles"] for c in corridors)
    # Fuel: idle burn scales with delay; ~0.9 L per extra hour stuck.
    fuel = round(vehicles * (sum(delays) / n / 60.0) * 0.9 / 10, 1)
    emissions = round(fuel * 2.31, 1)  # kg CO2 per litre petrol
    # Emergency response degrades with worst-corridor saturation.
    emergency = round(8 * (1 + 1.8 * max(congs) ** 2), 1)

    return {
        "avg_travel_time_min": avg_travel,
        "max_queue_m": max_queue,
        "throughput_vph": throughput,
        "fuel_litres": fuel,
        "emissions_kg": emissions,
        "emergency_response_min": emergency,
        "avg_congestion_pct": round(avg_c * 100, 1),
    }


def _zero_metrics() -> Dict:
    return {k: 0 for k in [
        "avg_travel_time_min", "max_queue_m", "throughput_vph", "fuel_litres",
        "emissions_kg", "emergency_response_min", "avg_congestion_pct"]}


def compare_scenarios(event: EventProfile,
                      strategies: List[str] | None = None) -> Dict:
    """Run several strategies and rank them against the baseline."""
    strategies = strategies or list(STRATEGIES.keys())
    runs = [simulate(event, s) for s in strategies]
    base = next((r for r in runs if r["strategy"] == "baseline"), runs[0])
    base_m = base["metrics"]

    for r in runs:
        m = r["metrics"]
        bt = base_m["avg_travel_time_min"] or 1
        r["improvement_pct"] = round(
            100 * (bt - m["avg_travel_time_min"]) / bt, 1
        )
    ranked = sorted(runs, key=lambda r: r["metrics"]["avg_travel_time_min"])
    best = next((r for r in ranked if r["strategy"] != "baseline"), ranked[0])
    return {
        "runs": runs,
        "best_strategy": best["strategy"],
        "best_label": best["label"],
        "best_improvement_pct": best["improvement_pct"],
    }
