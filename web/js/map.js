/* Map abstraction for TraffiSense.
   Rendering engine: Leaflet. Base tiles: Mappls (MapMyIndia) raster tiles
   when a key is configured, with OpenStreetMap as an always-available
   fallback so the command picture never goes blank during a demo. */

const TMap = (() => {
  let map, layers = {}, base = {};
  let mapplsOn = false;

  function init(center, zoom, mapplsKey) {
    map = L.map('map', { zoomControl: true, attributionControl: true })
      .setView(center, zoom);

    base.osm = L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      { maxZoom: 19, attribution: '&copy; OpenStreetMap' });

    if (mapplsKey) {
      base.mappls = L.tileLayer(
        `https://apis.mappls.com/advancedmaps/v1/${mapplsKey}/map_tiles/{z}/{x}/{y}.png`,
        { maxZoom: 18, attribution: 'Maps &copy; MapMyIndia (Mappls)' });
      base.mappls.addTo(map);
      mapplsOn = true;
      // If Mappls tiles error out, silently fall back to OSM.
      base.mappls.on('tileerror', () => {
        if (mapplsOn) {
          map.removeLayer(base.mappls);
          base.osm.addTo(map);
          mapplsOn = false;
          setMode('OpenStreetMap (Mappls tiles unavailable)');
        }
      });
      L.control.layers({ 'Mappls': base.mappls, 'OpenStreetMap': base.osm }).addTo(map);
      setMode('MapMyIndia / Mappls');
    } else {
      base.osm.addTo(map);
      setMode('OpenStreetMap (add a Mappls key for MapMyIndia tiles)');
    }

    // Pane-style layer groups.
    ['heat', 'event', 'corridors', 'junctions', 'resources',
     'diversions', 'emergency'].forEach(n => { layers[n] = L.layerGroup().addTo(map); });
    return map;
  }

  function setMode(text) {
    const el = document.getElementById('map-mode');
    if (el) el.textContent = text;
  }

  function clear(name) { if (layers[name]) layers[name].clearLayers(); }
  function clearAll() { Object.keys(layers).forEach(clear); }
  function toggle(name, on) {
    if (!layers[name]) return;
    if (on) map.addLayer(layers[name]); else map.removeLayer(layers[name]);
  }

  function drawHeat(points) {
    clear('heat');
    const heat = L.heatLayer(points, {
      radius: 18, blur: 22, maxZoom: 14,
      gradient: { 0.2: '#22d3ee', 0.4: '#34d399', 0.6: '#fbbf24', 0.8: '#fb923c', 1.0: '#ef4444' },
    });
    layers.heat.addLayer(heat);
  }

  function drawEvent(ev) {
    clear('event');
    const icon = L.divIcon({
      className: '', html:
        `<div style="background:#22d3ee;color:#06121f;font-weight:800;
          padding:4px 8px;border-radius:8px;border:2px solid #fff;
          box-shadow:0 2px 8px rgba(0,0,0,.5);white-space:nowrap;font-size:12px">
          ${ev.name}</div>`,
      iconAnchor: [0, 12],
    });
    L.marker([ev.lat, ev.lon], { icon }).addTo(layers.event);
    L.circle([ev.lat, ev.lon], { radius: 350, color: '#22d3ee',
      fillColor: '#22d3ee', fillOpacity: 0.15, weight: 1 }).addTo(layers.event);
  }

  function drawCorridors(affected) {
    clear('corridors');
    affected.forEach(c => {
      const col = congestionColor(c.congestion);
      const r = 250 + c.congestion * 7;
      L.circle([c.lat, c.lon], {
        radius: r, color: col, fillColor: col, fillOpacity: 0.25, weight: 2,
      }).bindPopup(
        `<b>${c.corridor}</b><br>Saturation: <b style="color:${col}">${c.congestion}%</b>
         (${c.severity})<br>Delay: ${c.delay_min} min<br>
         Event vehicles: ${c.demand_vehicles.toLocaleString()}<br>
         Closure risk: ${(c.closure_risk*100).toFixed(0)}%`
      ).addTo(layers.corridors);
    });
  }

  function drawJunctions(junctions) {
    clear('junctions');
    junctions.forEach(j => {
      L.circleMarker([j.lat, j.lon], {
        radius: 4 + Math.min(j.incidents / 12, 8), color: '#a78bfa',
        fillColor: '#a78bfa', fillOpacity: 0.6, weight: 1,
      }).bindPopup(`<b>${j.junction}</b><br>${j.incidents} historical incidents<br>
        High-priority rate: ${(j.high_priority_rate*100).toFixed(0)}%`)
        .addTo(layers.junctions);
    });
  }

  function drawResources(deployments) {
    clear('resources');
    deployments.forEach(d => {
      const a = d.allocation;
      const total = a.officers + a.barricades + a.marshals + a.tow_trucks;
      const icon = L.divIcon({ className: '', html:
        `<div style="background:#1e293b;border:2px solid #34d399;border-radius:50%;
          width:30px;height:30px;display:grid;place-items:center;font-size:11px;
          font-weight:800;color:#34d399">${total}</div>`,
        iconAnchor: [15, 15] });
      L.marker([d.lat, d.lon], { icon }).bindPopup(
        `<b>${d.id}</b> (${d.kind})<br>Officers: ${a.officers} ·
         Barricades: ${a.barricades}<br>Marshals: ${a.marshals} ·
         Tow trucks: ${a.tow_trucks}<br>
         <span style="color:#34d399">Est. relief: ${d.expected_relief_pct}%</span>`
      ).addTo(layers.resources);
    });
  }

  function drawDiversions(plans) {
    clear('diversions');
    plans.forEach(p => {
      L.polyline([[p.from_lat, p.from_lon], [p.to_lat, p.to_lon]], {
        color: '#fbbf24', weight: 3, dashArray: '8 6',
      }).bindPopup(p.rationale).addTo(layers.diversions);
      L.marker([p.to_lat, p.to_lon], { icon: L.divIcon({ className: '',
        html: '<div style="color:#fbbf24;font-size:18px">&#9656;</div>' }) })
        .addTo(layers.diversions);
    });
  }

  function drawEmergency(ec) {
    clear('emergency');
    if (!ec.path || !ec.path.length) return;
    L.polyline(ec.path, { color: '#f87171', weight: 4 })
      .bindPopup(ec.summary).addTo(layers.emergency);
  }

  function fit(coords) {
    if (!coords.length) return;
    map.fitBounds(L.latLngBounds(coords).pad(0.2));
  }

  return { init, drawHeat, drawEvent, drawCorridors, drawJunctions,
    drawResources, drawDiversions, drawEmergency, toggle, clearAll, fit };
})();
