# TraffiSense.ai - Demo Video Script (~3 minutes)

> Tip: run `./run.sh`, maximise the browser, and (optionally) paste a Mappls
> key into `.env` first so the base map shows MapMyIndia tiles.

## 0:00 - The hook (15s)
"Cities host huge events every week - cricket, concerts, rallies. Today,
traffic control is reactive: they watch CCTV and respond *after* the jam forms.
TraffiSense flips that - it predicts and plans *before* the event, on real
Bengaluru traffic-police data."

Show the landing dashboard: point at the badges - **8,057 real incidents,
21 corridors, 223 hotspots, ML model AUC 0.798** - and the historical incident
heatmap glowing over the city.

## 0:15 - Build an event (25s)
On the left panel:
- Pick **M. Chinnaswamy Stadium**.
- Event: "RCB vs CSK - IPL", attendance **40,000**, **19:00**, **Saturday**,
  weather **clear**.
- Click **Run Forecast & Plan**.

"In one click we forecast impact, simulate strategies, optimize resources and
plan emergency routes."

## 0:40 - The forecast (30s)
- Map: event marker drops, congestion rings appear around CBD corridors, green
  officer-deployment markers scatter across priority junctions.
- KPI strip: **16,800 vehicles, 7 corridors, worst 61%**.
- Forecast tab: read the headline and one corridor card -
  *"1,359 event vehicles routed onto CBD 2 -> 61% saturation, ~19 min delay,
  closure probability 40% (ML)."* Everything is explained.

## 1:10 - What-if with the Assistant (35s)
Open the **Assistant** tab. Click the chips:
- "What happens if heavy rain begins before the event?"
  -> *worst corridor 61% -> 100%, severe corridors 0 -> 7, avg delay
  15 -> 59 min. Pre-position tow trucks & marshals.*
- "Which junction needs the most officers?" -> names the top junction + count.
- "Show corridors likely to exceed 80% congestion."

"No external LLM - every answer is computed live from the simulation, so it's
always accurate."

## 1:45 - Resources + Scenarios (40s)
- **Resources** tab: the optimized deployment plan - officers, barricades,
  marshals, tow trucks - each with a rationale and expected relief %.
- **Scenarios** tab: the bar chart + table comparing No intervention vs
  Diversions vs Adaptive signals vs **Full optimization** (-30% travel time)
  vs Emergency mode. Metrics: travel time, queue, emergency response, CO2.

## 2:25 - Insights + close (25s)
- **Insights** tab: the honest **ML model card** (RandomForest, closure-risk,
  AUC 0.798), incidents-by-hour curve, and top causes.
- Re-run with attendance bumped to 60,000 or weather = heavy_rain to show it
  react live.

"TraffiSense.ai - anticipate congestion, test every plan, and deploy with
confidence. Built on real ASTraM data and MapMyIndia. Reactive becomes
proactive."
