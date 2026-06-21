/* Chart.js wrappers. Each chart is wrapped in a fixed-height container
   (set in the HTML it renders into) because Chart.js responsive mode
   ignores the canvas height attribute. */

const Charts = (() => {
  const store = {};
  const grid = '#243150';
  const tick = '#94a3b8';
  Chart.defaults.color = tick;
  Chart.defaults.font.size = 10;

  function _destroy(id) { if (store[id]) { store[id].destroy(); delete store[id]; } }
  function _ctx(id) { return document.getElementById(id); }

  function scenarios(canvasId, runs) {
    _destroy(canvasId);
    store[canvasId] = new Chart(_ctx(canvasId), {
      type: 'bar',
      data: {
        labels: runs.map(r => r.label),
        datasets: [
          { label: 'Avg travel (min)', data: runs.map(r => r.metrics.avg_travel_time_min),
            backgroundColor: '#22d3ee' },
          { label: 'Emergency resp (min)', data: runs.map(r => r.metrics.emergency_response_min),
            backgroundColor: '#f87171' },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { boxWidth: 10 } } },
        scales: { x: { grid: { color: grid }, ticks: { maxRotation: 30, minRotation: 0 } },
                  y: { grid: { color: grid } } },
      },
    });
  }

  function hourly(canvasId, byHour) {
    _destroy(canvasId);
    store[canvasId] = new Chart(_ctx(canvasId), {
      type: 'line',
      data: {
        labels: byHour.map((_, h) => h + 'h'),
        datasets: [{ label: 'Incidents by hour', data: byHour,
          borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,.15)',
          fill: true, tension: 0.35, pointRadius: 0 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { color: grid } }, y: { grid: { color: grid } } },
      },
    });
  }

  function causes(canvasId, items) {
    _destroy(canvasId);
    store[canvasId] = new Chart(_ctx(canvasId), {
      type: 'doughnut',
      data: {
        labels: items.map(i => i.cause),
        datasets: [{ data: items.map(i => i.count),
          backgroundColor: ['#22d3ee', '#34d399', '#fbbf24', '#fb923c',
            '#f87171', '#a78bfa', '#60a5fa', '#f472b6', '#4ade80', '#facc15'] }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { boxWidth: 10, font: { size: 9 } } } },
      },
    });
  }

  function corridors(canvasId, profiles) {
    _destroy(canvasId);
    const top = profiles.filter(p => p.corridor !== 'Non-corridor').slice(0, 10);
    store[canvasId] = new Chart(_ctx(canvasId), {
      type: 'bar',
      data: {
        labels: top.map(p => p.corridor),
        datasets: [{ label: 'Risk score', data: top.map(p => p.risk_score),
          backgroundColor: top.map(p => congestionColor(p.risk_score)) }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { color: grid } }, y: { grid: { color: grid } } },
      },
    });
  }

  return { scenarios, hourly, causes, corridors };
})();
