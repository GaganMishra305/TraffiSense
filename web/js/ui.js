/* DOM rendering helpers. Pure-ish: each function takes data and paints a
   target element. Orchestration lives in app.js. */

const UI = (() => {
  const $ = (id) => document.getElementById(id);

  function badges(ov) {
    $('data-badges').innerHTML = `
      <span class="badge">Incidents <b>${ov.totals.incidents.toLocaleString()}</b></span>
      <span class="badge">Corridors <b>${ov.totals.corridors}</b></span>
      <span class="badge">Hotspots <b>${ov.totals.junction_hotspots}</b></span>
      <span class="badge">Model AUC <b>${ov.model_card.holdout_auc}</b></span>`;
  }

  function kpis(summary, scen) {
    const s = summary, best = scen ? scen.best : null;
    const cards = [
      ['Total vehicles', s.total_vehicles.toLocaleString(), '#22d3ee'],
      ['Corridors hit', `${s.corridors_affected}`, '#60a5fa'],
      ['Severe', `${s.severe_corridors}`, '#fb923c'],
      ['Worst sat.', `${s.worst_congestion}%`, congestionColor(s.worst_congestion)],
      ['Avg delay', `${s.avg_delay_min}m`, '#fbbf24'],
      ['Radius', `${s.congestion_radius_km}km`, '#a78bfa'],
    ];
    $('kpi-strip').innerHTML = cards.map(([k, v, c]) =>
      `<div class="kpi"><div class="v" style="color:${c}">${v}</div><div class="k">${k}</div></div>`
    ).join('');
  }

  function legend() {
    $('map-legend').innerHTML = `
      <div><b>Legend</b></div>
      <div><span style="color:#ef4444">&#9679;</span> gridlock &nbsp;
           <span style="color:#fb923c">&#9679;</span> severe</div>
      <div><span style="color:#fbbf24">&#9679;</span> heavy &nbsp;
           <span style="color:#34d399">&#9679;</span> moderate</div>
      <div><span style="color:#a78bfa">&#9679;</span> junction hotspot</div>
      <div><span style="color:#34d399">&#9711;</span> resources &nbsp;
           <span style="color:#f87171">&#9472;</span> emergency</div>`;
  }

  function layerToggles(onChange) {
    const items = [
      ['heat', 'Historical heatmap', true],
      ['corridors', 'Predicted congestion', true],
      ['junctions', 'Junction hotspots', false],
      ['resources', 'Resource deployment', true],
      ['diversions', 'Diversions', true],
      ['emergency', 'Emergency corridor', true],
      ['event', 'Event marker', true],
    ];
    $('layer-toggles').innerHTML = items.map(([id, lbl, on]) =>
      `<label class="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" data-layer="${id}" ${on ? 'checked' : ''}
          class="accent-cyan-400"> <span>${lbl}</span></label>`
    ).join('');
    $('layer-toggles').querySelectorAll('input').forEach(cb =>
      cb.addEventListener('change', () => onChange(cb.dataset.layer, cb.checked)));
  }

  function tabs(names, onSelect) {
    $('tabs').innerHTML = names.map((n, i) =>
      `<button class="tab-btn ${i === 0 ? 'active' : ''}" data-tab="${n.id}">${n.label}</button>`
    ).join('');
    $('tabs').querySelectorAll('.tab-btn').forEach(b =>
      b.addEventListener('click', () => {
        $('tabs').querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        onSelect(b.dataset.tab);
      }));
  }

  // ---- Tab bodies -------------------------------------------------------
  function forecast(pred) {
    const s = pred.summary;
    const rows = pred.affected.map(c => `
      <div class="card">
        <div class="flex justify-between items-center">
          <span class="font-semibold">${c.corridor}</span>
          <span class="pill ${sevClass(c.severity)}">${c.congestion}% ${c.severity}</span>
        </div>
        <div class="text-xs text-slate-400 mt-1">${c.rationale}</div>
        <div class="text-[11px] mt-1 flex gap-3 text-slate-300">
          <span>Delay <b>${c.delay_min}m</b></span>
          <span>Veh <b>${c.demand_vehicles.toLocaleString()}</b></span>
          <span>Closure <b>${(c.closure_risk*100).toFixed(0)}%</b></span>
          <span>${c.distance_km}km</span>
        </div>
      </div>`).join('');
    return `<div class="card" style="border-color:#22d3ee">
        <div class="text-sm font-semibold text-cyan-300">Forecast headline</div>
        <div class="text-sm mt-1">${s.headline}</div>
        <div class="text-xs text-slate-400 mt-1">Peak ${s.peak_period} ·
          ${s.corridors_affected} corridors · avg delay ${s.avg_delay_min} min</div>
      </div>${rows || '<p class="text-slate-400 text-sm">No corridors in range.</p>'}`;
  }

  function resources(opt) {
    const t = opt.totals;
    const head = `<div class="card" style="border-color:#34d399">
        <div class="text-sm font-semibold text-emerald-300">Deployment plan</div>
        <div class="text-xs mt-1">${opt.summary}</div>
        <div class="grid grid-cols-4 gap-1 mt-2 text-center">
          ${[['Officers', t.officers], ['Barricades', t.barricades],
             ['Marshals', t.marshals], ['Tow', t.tow_trucks]]
            .map(([k, v]) => `<div class="kpi"><div class="v">${v}</div><div class="k">${k}</div></div>`).join('')}
        </div></div>`;
    const rows = opt.deployments.map(d => `
      <div class="card">
        <div class="flex justify-between items-center">
          <span class="font-semibold text-sm">${d.id}</span>
          <span class="pill sev-moderate">${d.kind}</span>
        </div>
        <div class="text-[11px] mt-1 flex gap-2 flex-wrap text-slate-300">
          <span>Off <b>${d.allocation.officers}</b></span>
          <span>Bar <b>${d.allocation.barricades}</b></span>
          <span>Mar <b>${d.allocation.marshals}</b></span>
          <span>Tow <b>${d.allocation.tow_trucks}</b></span>
          <span class="text-emerald-300">Relief ${d.expected_relief_pct}%</span>
        </div>
        <div class="text-xs text-slate-400 mt-1">${d.rationale}</div>
      </div>`).join('');
    return head + rows;
  }

  function scenarios(scen) {
    const runs = scen.runs;
    const best = `<div class="card" style="border-color:#fbbf24">
      <div class="text-sm font-semibold text-amber-300">Best strategy</div>
      <div class="text-sm mt-1">${scen.best_label} &mdash;
        <b>${scen.best_improvement_pct}%</b> faster than no intervention.</div></div>`;
    const chart = `<div class="card"><div style="height:170px">
      <canvas id="chart-scen"></canvas></div></div>`;
    const table = `<div class="card"><table class="w-full text-xs">
      <thead><tr class="text-slate-400 text-left">
        <th class="pb-1">Strategy</th><th>Travel</th><th>Queue</th>
        <th>Emerg</th><th>CO2</th><th>Impr</th></tr></thead><tbody>
      ${runs.map(r => `<tr class="border-t border-slate-700/50">
        <td class="py-1">${r.label}</td>
        <td>${r.metrics.avg_travel_time_min}m</td>
        <td>${r.metrics.max_queue_m}m</td>
        <td>${r.metrics.emergency_response_min}m</td>
        <td>${r.metrics.emissions_kg}kg</td>
        <td class="${r.improvement_pct>0?'text-emerald-300':'text-slate-400'}">${r.improvement_pct}%</td>
      </tr>`).join('')}</tbody></table></div>`;
    return best + chart + table;
  }

  function insights(ov) {
    const m = ov.model_card;
    return `
      <div class="card"><div class="text-sm font-semibold text-cyan-300 mb-1">ML Model Card</div>
        <div class="text-xs text-slate-300 leading-relaxed">
          <b>${m.algorithm}</b><br>Target: ${m.target}<br>
          Holdout AUC <b>${m.holdout_auc}</b> · Avg precision <b>${m.avg_precision}</b>
          (base rate ${m.base_rate})<br>
          Trained on ${m.train_samples.toLocaleString()} incidents,
          tested on ${m.test_samples.toLocaleString()}.<br>
          Features: ${m.features.join(', ')}</div></div>
      <div class="card"><div class="text-xs font-semibold mb-1">Incidents by hour (IST)</div>
        <div style="height:130px"><canvas id="chart-hourly"></canvas></div></div>
      <div class="card"><div class="text-xs font-semibold mb-1">Top incident causes</div>
        <div style="height:150px"><canvas id="chart-causes"></canvas></div></div>
      <div class="card"><div class="text-xs font-semibold mb-1">Corridor risk ranking</div>
        <div style="height:240px"><canvas id="chart-corridors"></canvas></div></div>`;
  }

  function assistantShell(examples) {
    const chips = examples.map(q => `<button class="chip" data-q="${q}">${q}</button>`).join('');
    return `
      <div id="chat-log" class="flex flex-col gap-2 mb-3"></div>
      <div class="flex flex-wrap gap-1.5 mb-2">${chips}</div>
      <div class="flex gap-1.5">
        <input id="chat-input" class="inp" placeholder="Ask about this event..." />
        <button id="chat-send" class="btn-primary px-3">Ask</button>
      </div>`;
  }

  function chatBubble(text, who) {
    const log = $('chat-log');
    const div = document.createElement('div');
    div.className = `chat-bubble ${who === 'user' ? 'chat-user' : 'chat-bot'}`;
    div.textContent = text;
    log.appendChild(div);
    log.parentElement.scrollTop = log.parentElement.scrollHeight;
  }

  return { badges, kpis, legend, layerToggles, tabs, forecast, resources,
    scenarios, insights, assistantShell, chatBubble };
})();
