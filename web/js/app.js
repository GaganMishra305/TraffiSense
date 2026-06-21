/* TraffiSense.ai - front-end orchestrator. */

const App = (() => {
  let venuesById = {}, overview = null, lastEvent = null, lastResults = {};

  const $ = (id) => document.getElementById(id);

  function eventFromForm() {
    const v = venuesById[$('venue').value];
    return {
      name: $('ev-name').value || 'Untitled Event',
      venue_id: $('venue').value,
      event_type: $('ev-type').value,
      lat: v.lat, lon: v.lon,
      attendance: +$('ev-att').value,
      start_hour: +$('ev-hour').value,
      duration_hours: +$('ev-dur').value,
      weekday: +$('ev-day').value,
      weather: $('ev-weather').value,
    };
  }

  function syncSliderLabels() {
    $('att-val').textContent = (+$('ev-att').value).toLocaleString();
    $('hour-val').textContent = $('ev-hour').value + ':00';
    $('dur-val').textContent = $('ev-dur').value;
  }

  async function init() {
    const [cfg, ven, ov, ex] = await Promise.all([
      API.config(), API.venues(), API.overview(), API.examples(),
    ]);
    overview = ov;

    // Weather options.
    $('ev-weather').innerHTML = cfg.weather_options.map(w =>
      `<option value="${w}">${w.replace('_', ' ')}</option>`).join('');

    // Venues.
    ven.venues.forEach(v => { venuesById[v.id] = v; });
    $('venue').innerHTML = ven.venues.map(v =>
      `<option value="${v.id}">${v.name} (${v.capacity.toLocaleString()})</option>`).join('');
    $('venue').addEventListener('change', () => {
      const v = venuesById[$('venue').value];
      $('ev-att').value = Math.min(60000, v.capacity);
      $('ev-type').value = v.type;
      syncSliderLabels();
    });

    // Map.
    TMap.init(cfg.city_center, cfg.default_zoom, cfg.mappls_map_key);
    TMap.drawHeat(await API.heatmap().then(r => r.points));
    TMap.drawJunctions(ov.junctions);
    TMap.toggle('junctions', false);
    UI.legend();

    // UI scaffolding.
    UI.badges(ov);
    UI.layerToggles((layer, on) => TMap.toggle(layer, on));
    setupTabs();

    ['ev-att', 'ev-hour', 'ev-dur'].forEach(id =>
      $(id).addEventListener('input', syncSliderLabels));
    syncSliderLabels();
    $('run-btn').addEventListener('click', run);

    // Default tab content before first run.
    renderTab('forecast');
    window._examples = ex.examples;
  }

  // ---- Tabs -------------------------------------------------------------
  function setupTabs() {
    UI.tabs([
      { id: 'forecast', label: 'Forecast' },
      { id: 'resources', label: 'Resources' },
      { id: 'scenarios', label: 'Scenarios' },
      { id: 'assistant', label: 'Assistant' },
      { id: 'insights', label: 'Insights' },
    ], renderTab);
  }

  function renderTab(id) {
    const body = $('tab-body');
    if (id === 'forecast') {
      body.innerHTML = lastResults.predict
        ? UI.forecast(lastResults.predict)
        : hint('Run a forecast to see predicted corridor congestion.');
    } else if (id === 'resources') {
      body.innerHTML = lastResults.optimize
        ? UI.resources(lastResults.optimize)
        : hint('Run a forecast to generate an optimized deployment plan.');
    } else if (id === 'scenarios') {
      body.innerHTML = lastResults.scenarios
        ? UI.scenarios(lastResults.scenarios)
        : hint('Run a forecast to compare management strategies.');
      if (lastResults.scenarios) Charts.scenarios('chart-scen', lastResults.scenarios.runs);
    } else if (id === 'assistant') {
      body.innerHTML = UI.assistantShell(window._examples || []);
      wireAssistant();
    } else if (id === 'insights') {
      body.innerHTML = UI.insights(overview);
      Charts.hourly('chart-hourly', overview.temporal.by_hour);
      Charts.causes('chart-causes', overview.causes);
      Charts.corridors('chart-corridors', overview.corridors);
    }
  }

  function hint(t) { return `<p class="text-slate-400 text-sm">${t}</p>`; }

  // ---- Run the full pipeline -------------------------------------------
  async function run() {
    const ev = eventFromForm();
    lastEvent = ev;
    const btn = $('run-btn');
    btn.disabled = true;
    $('run-status').textContent = 'Forecasting, simulating and optimizing...';
    try {
      const [predict, optimize, scenarios, diversions, emergency] = await Promise.all([
        API.predict(ev), API.optimize(ev), API.scenarios(ev),
        API.diversions(ev), API.emergency(ev),
      ]);
      lastResults = { predict, optimize, scenarios, diversions, emergency };

      // Map.
      TMap.drawEvent(ev);
      TMap.drawCorridors(predict.affected);
      TMap.drawResources(optimize.deployments);
      TMap.drawDiversions(diversions.plans);
      TMap.drawEmergency(emergency);
      const coords = [[ev.lat, ev.lon], ...predict.affected.map(c => [c.lat, c.lon])];
      TMap.fit(coords);

      // Panels.
      const best = { best: scenarios.best_label, pct: scenarios.best_improvement_pct };
      UI.kpis(predict.summary, { best });
      $('tabs').querySelector('.tab-btn').classList.add('active');
      renderTab(activeTab());
      $('run-status').textContent =
        `Done. ${predict.summary.severe_corridors} severe corridors; best plan: ${scenarios.best_label}.`;
    } catch (e) {
      $('run-status').textContent = 'Error: ' + e.message;
    } finally {
      btn.disabled = false;
    }
  }

  function activeTab() {
    const a = $('tabs').querySelector('.tab-btn.active');
    return a ? a.dataset.tab : 'forecast';
  }

  // ---- Assistant --------------------------------------------------------
  function wireAssistant() {
    const send = async () => {
      const inp = $('chat-input');
      const q = inp.value.trim();
      if (!q) return;
      UI.chatBubble(q, 'user');
      inp.value = '';
      try {
        const r = await API.assistant(q, lastEvent);
        UI.chatBubble(r.answer, 'bot');
      } catch (e) {
        UI.chatBubble('Sorry, I hit an error: ' + e.message, 'bot');
      }
    };
    $('chat-send').addEventListener('click', send);
    $('chat-input').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
    $('tab-body').querySelectorAll('.chip').forEach(c =>
      c.addEventListener('click', () => {
        $('chat-input').value = c.dataset.q;
        $('chat-send').click();
      }));
    if (!lastEvent) UI.chatBubble('Run a forecast first, then ask me anything about it.', 'bot');
    else UI.chatBubble(`Ready. Ask me about ${lastEvent.name}.`, 'bot');
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
