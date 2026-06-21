"""TraffiSense.ai FastAPI application.

Thin transport layer: every route delegates to a focused engine module so the
business logic stays testable and the file stays small.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import (assistant, config, data, ml, optimizer, predictor, routing,
               simulator, venues)
from .schemas import AssistantQuery, EventProfile, ScenarioRequest

app = FastAPI(title="TraffiSense.ai", version="1.0.0")


@app.on_event("startup")
def _warm_caches() -> None:
    """Pre-build the heavy caches so the first request is instant on stage."""
    data.corridor_profiles()
    data.junction_profiles()
    ml.get_model()


@app.get("/api/config")
def get_config() -> dict:
    return {
        "mappls_map_key": config.MAPPLS_MAP_SDK_KEY,
        "city_center": config.CITY_CENTER,
        "default_zoom": config.DEFAULT_ZOOM,
        "weather_options": list(config.WEATHER_MULTIPLIERS.keys()),
    }


@app.get("/api/venues")
def get_venues() -> dict:
    return {"venues": venues.VENUES}


@app.get("/api/overview")
def get_overview() -> dict:
    corridors = data.corridor_profiles()
    return {
        "totals": {
            "incidents": len(data.load_incidents()),
            "corridors": len([c for c in corridors if c["corridor"] != "Non-corridor"]),
            "junction_hotspots": len(data.junction_profiles()),
        },
        "corridors": corridors,
        "junctions": data.junction_profiles()[:40],
        "temporal": data.temporal_pattern(),
        "causes": data.cause_breakdown(),
        "model_card": ml.model_card(),
    }


@app.get("/api/heatmap")
def get_heatmap() -> dict:
    return {"points": data.heatmap_points()}


@app.post("/api/predict")
def post_predict(event: EventProfile) -> dict:
    return predictor.predict_impact(event)


@app.post("/api/optimize")
def post_optimize(event: EventProfile) -> dict:
    return optimizer.optimize_resources(event)


@app.post("/api/scenarios")
def post_scenarios(event: EventProfile) -> dict:
    return simulator.compare_scenarios(event)


@app.post("/api/simulate")
def post_simulate(req: ScenarioRequest) -> dict:
    ev = req.event.model_copy(
        update={"attendance": int(req.event.attendance * req.attendance_multiplier)}
    )
    return simulator.simulate(ev, req.strategy)


@app.post("/api/diversions")
def post_diversions(event: EventProfile) -> dict:
    return routing.diversion_plan(event)


@app.post("/api/emergency")
def post_emergency(event: EventProfile) -> dict:
    return routing.emergency_corridor(event)


@app.post("/api/assistant")
def post_assistant(q: AssistantQuery) -> dict:
    return assistant.answer(q.question, q.event)


@app.get("/api/assistant/examples")
def get_examples() -> dict:
    return {"examples": assistant.example_questions()}


# --- static frontend (mounted last so /api/* wins) ---
@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=config.WEB_DIR), name="static")
