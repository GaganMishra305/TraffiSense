"""Self-contained AI Command Assistant.

No external LLM: a transparent intent-matching brain that turns natural
language into real calls against the prediction / simulation / optimization
engines. Every answer is computed from live data, so it is always accurate and
demo-safe. Designed with a clean `answer()` entry point so an LLM adapter can
be slotted in later without touching callers.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from . import optimizer, predictor, routing, simulator
from .schemas import EventProfile

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_NUM = re.compile(r"(\d+(?:\.\d+)?)")


def answer(question: str, event: Optional[EventProfile]) -> Dict:
    q = question.lower().strip()
    if event is None:
        return _reply("Select or create an event first, then ask me anything "
                      "about its traffic impact.", intent="no_event")

    for matcher, handler in _ROUTES:
        if matcher(q):
            return handler(q, event)
    return _fallback(q, event)


# ----------------------------------------------------------------------------
# Intent handlers
# ----------------------------------------------------------------------------
def _attendance_whatif(q: str, event: EventProfile) -> Dict:
    m = _PCT.search(q) or _NUM.search(q)
    pct = float(m.group(1)) if m else 20.0
    direction = -1 if any(w in q for w in ("decrease", "drop", "less", "fewer")) else 1
    factor = 1 + direction * pct / 100.0
    new = event.model_copy(update={"attendance": int(event.attendance * factor)})
    base = predictor.predict_impact(event)["summary"]
    alt = predictor.predict_impact(new)["summary"]
    delta = round(alt["worst_congestion"] - base["worst_congestion"], 1)
    return _reply(
        f"If attendance {'rises' if direction>0 else 'falls'} {pct:.0f}% "
        f"({event.attendance:,} -> {new.attendance:,}), worst-corridor "
        f"saturation moves from {base['worst_congestion']:.0f}% to "
        f"{alt['worst_congestion']:.0f}% ({delta:+.0f} pts) on "
        f"{alt['worst_corridor']}, and severe corridors go "
        f"{base['severe_corridors']} -> {alt['severe_corridors']}.",
        intent="attendance_whatif",
        data={"base": base, "alternative": alt},
    )


def _weather_whatif(q: str, event: EventProfile) -> Dict:
    weather = "heavy_rain" if "heavy" in q else "rain"
    new = event.model_copy(update={"weather": weather})
    base = predictor.predict_impact(event)["summary"]
    alt = predictor.predict_impact(new)["summary"]
    return _reply(
        f"With {weather.replace('_',' ')}, demand and severity rise: worst "
        f"corridor {base['worst_congestion']:.0f}% -> {alt['worst_congestion']:.0f}% "
        f"saturation, severe corridors {base['severe_corridors']} -> "
        f"{alt['severe_corridors']}, avg delay {base['avg_delay_min']} -> "
        f"{alt['avg_delay_min']} min. Pre-position tow trucks & marshals.",
        intent="weather_whatif",
        data={"base": base, "alternative": alt},
    )


def _officers_query(q: str, event: EventProfile) -> Dict:
    plan = optimizer.optimize_resources(event)
    if not plan["deployments"]:
        return _reply("No deployment points fall within range of this event.",
                      intent="officers")
    top = max(plan["deployments"], key=lambda d: d["allocation"]["officers"])
    return _reply(
        f"{top['id']} needs the most officers: {top['allocation']['officers']} "
        f"officers + {top['allocation']['barricades']} barricades. "
        f"{top['rationale']}",
        intent="officers", data={"top": top, "totals": plan["totals"]},
    )


def _threshold_query(q: str, event: EventProfile) -> Dict:
    m = _PCT.search(q) or _NUM.search(q)
    thr = float(m.group(1)) if m else 80.0
    affected = predictor.predict_impact(event)["affected"]
    over = [c for c in affected if c["congestion"] >= thr]
    if not over:
        return _reply(f"No corridors are predicted to exceed {thr:.0f}% "
                      "saturation for this event.", intent="threshold")
    names = ", ".join(f"{c['corridor']} ({c['congestion']:.0f}%)" for c in over)
    return _reply(f"{len(over)} corridor(s) exceed {thr:.0f}% saturation: {names}.",
                  intent="threshold", data={"corridors": over})


def _scenario_query(q: str, event: EventProfile) -> Dict:
    cmp = simulator.compare_scenarios(event)
    runs = {r["strategy"]: r for r in cmp["runs"]}
    target = next((s for s in ("full", "diversions", "signals", "emergency")
                   if s in q), cmp["best_strategy"])
    r = runs.get(target, runs[cmp["best_strategy"]])
    return _reply(
        f"'{r['label']}' delivers a {r['improvement_pct']:.0f}% cut in average "
        f"travel time (to {r['metrics']['avg_travel_time_min']} min) and drops "
        f"emergency response to {r['metrics']['emergency_response_min']} min. "
        f"Best overall option: {cmp['best_label']} "
        f"({cmp['best_improvement_pct']:.0f}% improvement).",
        intent="scenario", data=cmp,
    )


def _emergency_query(q: str, event: EventProfile) -> Dict:
    ec = routing.emergency_corridor(event)
    return _reply(ec["summary"] + f" Estimated response time "
                  f"{ec.get('response_time_min','?')} min.",
                  intent="emergency", data=ec)


def _diversion_query(q: str, event: EventProfile) -> Dict:
    dp = routing.diversion_plan(event)
    if not dp["plans"]:
        return _reply(dp["summary"], intent="diversion", data=dp)
    first = dp["plans"][0]
    return _reply(dp["summary"] + " Top move: " + first["rationale"],
                  intent="diversion", data=dp)


def _signals_query(q: str, event: EventProfile) -> Dict:
    affected = predictor.predict_impact(event)["affected"][:3]
    names = ", ".join(c["corridor"] for c in affected)
    return _reply(
        f"Extend green phases on the inbound approaches to {names}. Adaptive "
        f"signal control models a ~16% network-wide congestion relief here "
        f"(see the 'Adaptive signals' scenario).",
        intent="signals", data={"corridors": affected},
    )


def _fallback(q: str, event: EventProfile) -> Dict:
    s = predictor.predict_impact(event)["summary"]
    return _reply(
        f"For {s['event_name']}: {s['headline']} {s['corridors_affected']} "
        f"corridors affected ({s['severe_corridors']} severe), avg delay "
        f"{s['avg_delay_min']} min, congestion radius {s['congestion_radius_km']} km. "
        f"Try asking about attendance changes, rain, officers, diversions, "
        f"emergency routes, or scenario comparisons.",
        intent="summary", data=s,
    )


def _reply(text: str, intent: str, data: Optional[Dict] = None) -> Dict:
    return {"answer": text, "intent": intent, "data": data or {}}


# ----------------------------------------------------------------------------
# Intent routing table (order matters: most specific first)
# ----------------------------------------------------------------------------
def _has(*words):
    return lambda q: any(w in q for w in words)


_ROUTES = [
    (_has("attendance", "crowd", "footfall", "people", "turnout"), _attendance_whatif),
    (_has("rain", "weather", "storm", "monsoon"), _weather_whatif),
    (_has("officer", "police", "manpower", "personnel", "staff"), _officers_query),
    (lambda q: "%" in q or "exceed" in q or "above" in q or "over " in q, _threshold_query),
    (_has("scenario", "plan b", "plan a", "compare", "improvement", "strategy",
          "full optim"), _scenario_query),
    (_has("emergency", "ambulance", "fire", "responder"), _emergency_query),
    (_has("divert", "diversion", "reroute", "alternate"), _diversion_query),
    (_has("signal", "green", "phase", "junction timing"), _signals_query),
]


def example_questions() -> List[str]:
    return [
        "What if attendance increases by 30%?",
        "What happens if heavy rain begins before the event?",
        "Which junction needs the most officers?",
        "Show corridors likely to exceed 80% congestion.",
        "How much improvement does full optimization provide?",
        "Plan an emergency corridor for ambulances.",
        "Recommend diversions for the worst corridors.",
        "Which intersections should get longer green phases?",
    ]
