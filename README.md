# TraffiSense.ai

**Predictive, simulation-driven traffic command for large city events.**
Built on the real **ASTraM Bengaluru Traffic Police** incident dataset, with
**MapMyIndia / Mappls** mapping infrastructure.

TraffiSense turns traffic management from reactive to proactive: forecast an
event's congestion impact *before* it happens, simulate intervention
strategies, and get explainable recommendations for officers, barricades,
diversions and emergency corridors.

---

## Demo walkthrough (live screenshots)

**1. Command dashboard** — historical incident heatmap from 8,057 real ASTraM
records, with the event builder on the left and live data badges up top.

![Command dashboard](docs/screenshots/demo-01-dashboard.png)

**2. AI traffic-impact forecast** — one click drops the event, predicts
corridor congestion (rings), scatters optimized resource markers, and explains
every corridor card (vehicles, delay, ML closure risk).

![Forecast](docs/screenshots/demo-02-forecast.png)

**3. Resource deployment optimization** — officers, barricades, marshals and
tow trucks allocated by marginal need, each with a plain-English rationale and
expected queue relief.

![Resource optimization](docs/screenshots/demo-03-resources.png)

**4. Scenario comparison** — five strategies (no intervention, diversions,
adaptive signals, full optimization, emergency mode) ranked on travel time,
queue, emergency response and CO2.

![Scenario comparison](docs/screenshots/demo-04-scenarios.png)

**5. AI command assistant** — ask natural-language what-ifs; every answer is
computed live from the simulation (no external LLM).

![AI assistant](docs/screenshots/demo-05-assistant.png)

**6. Insights + honest ML model card** — incidents-by-hour, top causes, and the
RandomForest closure-risk model's real holdout metrics.

![Insights](docs/screenshots/demo-06-insights.png)

---

## What it does (the 5 deep features)

1. **Event Intelligence** — pick a real Bengaluru venue (Chinnaswamy Stadium,
   Palace Grounds, BIEC...) and define attendance, time, day and weather.
2. **AI Traffic Impact Prediction** — a gravity demand model spreads attendee
   vehicles across surrounding corridors, fused with real historical incident
   density and an ML closure-risk model. Every number is explained.
3. **Live Command Map** — historical incident heatmap, predicted congestion
   rings, junction hotspots, resource markers, diversion lines and the reserved
   emergency corridor, all on a MapMyIndia base (OSM fallback).
4. **Resource Deployment Optimization** — marginal-need allocation of officers,
   barricades, marshals and tow trucks, each with a plain-English rationale.
5. **Scenario Comparison + AI Command Assistant** — compare 5 strategies side
   by side (travel time, queue, throughput, fuel, emissions, emergency
   response), and ask natural-language "what-if" questions.

Plus: digital-twin simulation, diversion planning, emergency corridors and a
post-hoc insights tab with an honest ML model card.

---

## The data + the model (no hand-waving)

- **8,057** cleaned incidents (Nov 2023 - Apr 2024), 21 corridors, 223 chronic
  junction hotspots, timestamps normalised to IST.
- **ML model:** RandomForest predicting **road-closure requirement** — a real,
  imbalanced operational target (7.4% base rate). Honest holdout
  **AUC 0.798**, average precision **0.32** (4x better than the base rate).
  We deliberately avoided the trap target `priority` (it's a deterministic
  corridor label, so it leaks).

---

## Run it

```bash
./run.sh            # creates venv, installs deps, serves, opens browser
# or manually:
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --port 8077
```

Open http://127.0.0.1:8077

### Enable MapMyIndia / Mappls tiles

```bash
cp .env.example .env
# paste your keys:
#   MAPPLS_MAP_SDK_KEY=...   (browser map tiles)
#   MAPPLS_REST_KEY=...      (server-side REST, optional)
```

Without a key the map falls back to OpenStreetMap so the demo always works.

---

## Architecture

```
app/
  config.py      tunables + Mappls keys (env)
  data.py        ASTraM loader + corridor/junction/temporal intelligence
  ml.py          RandomForest closure-risk model (trained + cached)
  predictor.py   gravity demand x history x ML -> congestion forecast
  simulator.py   digital-twin lite + scenario comparison
  optimizer.py   resource deployment (marginal need + rationale)
  routing.py     diversion plans + emergency corridor
  assistant.py   self-contained NL command brain
  main.py        FastAPI transport layer
web/             command-center dashboard (Leaflet + Mappls, Chart.js, Tailwind)
```

Every engine is a small, single-responsibility module — DRY, testable, and all
under the 600-line budget.

---

## Tech

FastAPI · scikit-learn · pandas · Leaflet + MapMyIndia (Mappls) raster tiles ·
Chart.js · Tailwind. No external LLM required — the assistant computes every
answer from live engine output, so it is always accurate and demo-safe.
