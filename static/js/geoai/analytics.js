(function () {
  'use strict';

  const byId = (id) => document.getElementById(id);
  const readJson = (id, fallback) => {
    const node = byId(id);
    if (!node) return fallback;
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      console.error(`GeoAI JSON parse error: #${id}`, error);
      return fallback;
    }
  };

  const validCoordinate = (lat, lng) =>
    Number.isFinite(lat) && Number.isFinite(lng) &&
    lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;

  const safePoints = (rows) => (Array.isArray(rows) ? rows : [])
    .map((row) => ({
      ...row,
      lat: Number(row.lat),
      lng: Number(row.lng),
      priority: Number(row.priority) || 0,
      confidence: Number(row.confidence) || 0,
    }))
    .filter((row) => validCoordinate(row.lat, row.lng));

  const fitMapToPoints = (map, rows, fallbackCenter, fallbackZoom) => {
    if (!map) return;
    if (rows.length) {
      const bounds = L.latLngBounds(rows.map((p) => [p.lat, p.lng]));
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [25, 25], maxZoom: 12 });
        return;
      }
    }
    map.setView(fallbackCenter, fallbackZoom);
  };

  const makePriorityNormalizer = (points) => {
    const values = points.map((p) => p.priority);
    const min = values.length ? Math.min(...values) : 0;
    const max = values.length ? Math.max(...values) : 1;
    return (value) => Math.max(0.15, (Number(value || 0) - min) / Math.max(max - min, 1e-9));
  };

  const priorityColors = { high: '#dc3545', medium: '#f59e0b', low: '#22a447' };
  const riskColors = { high: '#dc2626', medium: '#f59e0b', low: '#22c55e' };
  const palette = ['#3868e8', '#22a447', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#64748b'];

  const chartRegistry = new Map();
  const initializedPanels = new Set();
  let primaryMap = null;
  let smartMap = null;

  function resizeChartsIn(panelSelector) {
    const panel = document.querySelector(panelSelector);
    if (!panel) return;
    panel.querySelectorAll('canvas[id]').forEach((canvas) => {
      const chart = chartRegistry.get(canvas.id);
      if (chart) {
        chart.resize();
        chart.update('none');
      }
    });
  }

  function initializePrimaryMap(points, riskStats, normalizePriority) {
    const container = byId('geoaiMap');
    if (!container || typeof L === 'undefined') return null;

    const fallbackCenter = [41.3111, 69.2797];
    const center = points.length ? [points[0].lat, points[0].lng] : fallbackCenter;
    const map = L.map(container, { preferCanvas: true }).setView(center, 7);
    const baseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(map);

    const markerLayer = L.layerGroup().addTo(map);
    const heatLayer = L.heatLayer(
      points.map((p) => [p.lat, p.lng, normalizePriority(p.priority)]),
      {
        radius: 44,
        blur: 32,
        maxZoom: 12,
        minOpacity: 0.50,
        max: 1,
        gradient: {
          0.0: '#0000ff', 0.2: '#00bfff', 0.4: '#00ff66',
          0.6: '#ffff00', 0.8: '#ff7f00', 1.0: '#ff0000',
        },
      },
    );
    const riskLayer = L.layerGroup();

    (riskStats.clusters || []).forEach((cluster) => {
      if (!cluster || !Array.isArray(cluster.points)) return;
      const color = riskColors[cluster.risk_level] || '#64748b';
      const clusterPoints = cluster.points
        .map((pair) => [Number(pair[0]), Number(pair[1])])
        .filter(([lat, lng]) => validCoordinate(lat, lng));

      if (clusterPoints.length >= 3) {
        L.polygon(clusterPoints, {
          color,
          fillColor: color,
          fillOpacity: 0.24,
          weight: 3,
        }).bindPopup(
          `<b>K${cluster.label}</b><br>` +
          `Hₖ: <b>${Number(cluster.risk_index || 0).toFixed(3)}</b><br>` +
          `Nuqtalar: ${cluster.count || 0}<br>` +
          `O‘rtacha Pᵢ: ${Number(cluster.avg_priority || 0).toFixed(3)}`,
        ).addTo(riskLayer);
      }

      const centerPoint = Array.isArray(cluster.center)
        ? [Number(cluster.center[0]), Number(cluster.center[1])]
        : null;
      if (centerPoint && validCoordinate(centerPoint[0], centerPoint[1])) {
        L.circleMarker(centerPoint, {
          radius: 10,
          color,
          fillColor: color,
          fillOpacity: 0.92,
          weight: 3,
        }).bindTooltip(`K${cluster.label}: H=${Number(cluster.risk_index || 0).toFixed(3)}`)
          .addTo(riskLayer);
      }
    });

    points.forEach((point) => {
      const components = point.components || {};
      const details = `
        <div class="component-grid">
          <div class="component-pill">ρᵢ<br><b>${components.density ?? '—'}</b></div>
          <div class="component-pill">fᵢ<br><b>${components.frequency ?? '—'}</b></div>
          <div class="component-pill">qᵢ<br><b>${components.recency ?? '—'}</b></div>
          <div class="component-pill">W(Cᵢ)<br><b>${components.severity ?? '—'}</b></div>
          <div class="component-pill">Confᵢ<br><b>${point.confidence}</b></div>
          <div class="component-pill">nᵢ<br><b>${components.neighbor ?? '—'}</b></div>
        </div>`;
      const color = priorityColors[point.level] || '#3868e8';
      L.circleMarker([point.lat, point.lng], {
        radius: 7,
        color,
        fillColor: color,
        fillOpacity: 0.82,
        weight: 2,
      }).bindPopup(
        `<b>${point.category || 'Noma’lum'}</b><br>` +
        `Pᵢ: <b>${point.priority}</b> &nbsp; Confᵢ: ${point.confidence}<hr>` +
        `${point.description || ''}<hr>` +
        `<small>Sana: ${point.created_at || '—'}<br>` +
        `Tashkilot: ${point.organization || '—'}</small>${details}`,
        { maxWidth: 460 },
      ).addTo(markerLayer);
    });

    L.control.layers(
      { OpenStreetMap: baseLayer },
      {
        'Ustuvorlik markerlari': markerLayer,
        'Priority heatmap': heatLayer,
        'DBSCAN + Risk zonalari': riskLayer,
      },
      { collapsed: false },
    ).addTo(map);

    heatLayer.addTo(map);
    riskLayer.addTo(map);
    fitMapToPoints(map, points, fallbackCenter, 6);
    setTimeout(() => map.invalidateSize(true), 200);
    document.querySelector('[data-bs-target="#map-tab"]')
      ?.addEventListener('shown.bs.tab', () => setTimeout(() => map.invalidateSize(true), 100));
    return map;
  }

  function initializeSmartMap(points, riskStats, normalizePriority) {
    const container = byId('smartMap');
    if (!container || typeof L === 'undefined') return null;

    const fallbackCenter = [41.3111, 69.2797];
    const center = points.length ? [points[0].lat, points[0].lng] : fallbackCenter;
    const map = L.map(container, { preferCanvas: true }).setView(center, 7);
    const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(map);
    const humanitarian = L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors, Tiles HOT',
    });
    const dark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 20,
      attribution: '© OpenStreetMap © CARTO',
    });

    const complaintLayer = L.layerGroup().addTo(map);
    const riskLayer = L.layerGroup().addTo(map);
    const queryLayer = L.layerGroup().addTo(map);
    const heatLayer = L.heatLayer(
      points.map((p) => [p.lat, p.lng, normalizePriority(p.priority)]),
      {
        radius: 38,
        blur: 28,
        maxZoom: 12,
        minOpacity: 0.42,
        gradient: {
          0: '#172554', 0.25: '#0ea5e9', 0.5: '#22c55e',
          0.72: '#fde047', 0.87: '#f97316', 1: '#991b1b',
        },
      },
    ).addTo(map);

    (riskStats.clusters || []).forEach((cluster) => {
      const color = riskColors[cluster.risk_level] || '#64748b';
      const clusterPoints = (cluster.points || [])
        .map((pair) => [Number(pair[0]), Number(pair[1])])
        .filter(([lat, lng]) => validCoordinate(lat, lng));
      if (clusterPoints.length >= 3) {
        L.polygon(clusterPoints, {
          color,
          fillColor: color,
          fillOpacity: 0.22,
          weight: 3,
        }).bindPopup(
          `<b>K${cluster.label}</b><br>` +
          `Hₖ=${Number(cluster.risk_index || 0).toFixed(3)}<br>` +
          `Nuqtalar=${cluster.count || 0}<br>Xavf=${cluster.risk_level || 'low'}`,
        ).addTo(riskLayer);
      }
    });

    points.forEach((point) => {
      const color = priorityColors[point.level] || '#3868e8';
      L.circleMarker([point.lat, point.lng], {
        radius: 5,
        color,
        fillColor: color,
        fillOpacity: 0.75,
        weight: 1.5,
      }).bindTooltip(`${point.category || 'Noma’lum'}: P=${point.priority}`)
        .addTo(complaintLayer);
    });

    L.control.layers(
      { OpenStreetMap: osm, Humanitarian: humanitarian, 'Dark CARTO': dark },
      {
        Murojaatlar: complaintLayer,
        'Risk poligonlari': riskLayer,
        'SMART heatmap': heatLayer,
        'Fazoviy qidiruv': queryLayer,
      },
      { collapsed: false },
    ).addTo(map);

    fitMapToPoints(map, points, fallbackCenter, 6);
    document.querySelector('[data-bs-target="#smart-tab"]')
      ?.addEventListener('shown.bs.tab', () => setTimeout(() => map.invalidateSize(true), 100));

    const qLat = byId('queryLat');
    const qLng = byId('queryLng');
    const qRadius = byId('queryRadius');
    const resultCount = byId('spatialResultCount');
    const haversine = (lat1, lng1, lat2, lng2) => {
      const earthRadius = 6371;
      const toRadians = (value) => value * Math.PI / 180;
      const deltaLat = toRadians(lat2 - lat1);
      const deltaLng = toRadians(lng2 - lng1);
      const h = Math.sin(deltaLat / 2) ** 2 +
        Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) *
        Math.sin(deltaLng / 2) ** 2;
      return 2 * earthRadius * Math.asin(Math.sqrt(h));
    };

    map.on('click', (event) => {
      if (qLat) qLat.value = event.latlng.lat.toFixed(6);
      if (qLng) qLng.value = event.latlng.lng.toFixed(6);
    });

    byId('applySpatialQuery')?.addEventListener('click', () => {
      const lat = Number(qLat?.value);
      const lng = Number(qLng?.value);
      const radius = Math.max(1, Number(qRadius?.value) || 50);
      if (!validCoordinate(lat, lng)) {
        window.alert('Xaritadan markazni tanlang yoki koordinatalarni kiriting.');
        return;
      }
      queryLayer.clearLayers();
      const queryCircle = L.circle([lat, lng], {
        radius: radius * 1000,
        color: '#7c3aed',
        fillColor: '#8b5cf6',
        fillOpacity: 0.12,
        weight: 3,
      }).addTo(queryLayer);
      let count = 0;
      points.forEach((point) => {
        if (haversine(lat, lng, point.lat, point.lng) <= radius) {
          count += 1;
          L.circleMarker([point.lat, point.lng], {
            radius: 8,
            color: '#7c3aed',
            fillColor: '#c4b5fd',
            fillOpacity: 0.95,
            weight: 3,
          }).bindPopup(
            `<b>${point.category || 'Noma’lum'}</b><br>` +
            `Pᵢ=${point.priority}<br>${point.description || ''}`,
          ).addTo(queryLayer);
        }
      });
      if (resultCount) resultCount.textContent = `Radius ichida: ${count} ta`;
      map.fitBounds(queryCircle.getBounds(), { padding: [25, 25] });
    });

    byId('clearSpatialQuery')?.addEventListener('click', () => {
      queryLayer.clearLayers();
      if (qLat) qLat.value = '';
      if (qLng) qLng.value = '';
      if (resultCount) resultCount.textContent = 'Barcha natijalar';
      fitMapToPoints(map, points, fallbackCenter, 6);
    });

    return map;
  }

  function createChart(elementId, configuration) {
    const canvas = byId(elementId);
    if (!canvas) {
      console.warn(`GeoAI canvas topilmadi: #${elementId}`);
      return null;
    }
    if (typeof Chart === 'undefined') {
      console.error('Chart.js yuklanmagan. static/js/plugins/chartjs.min.js mavjudligini tekshiring.');
      return null;
    }
    const existing = chartRegistry.get(elementId);
    if (existing) existing.destroy();
    const chart = new Chart(canvas.getContext('2d'), configuration);
    chartRegistry.set(elementId, chart);
    return chart;
  }

  function initializeMetricsCharts(metrics) {
    if (!metrics || !metrics.available) return;
    const rocDatasets = (metrics.roc_series || []).map((series, index) => ({
      label: `${series.label} (AUC=${Number(series.auc || 0).toFixed(3)})`,
      data: (series.fpr || []).map((x, pointIndex) => ({ x, y: series.tpr[pointIndex] })),
      borderColor: palette[index % palette.length],
      backgroundColor: 'transparent',
      pointRadius: 1.5,
      tension: 0.18,
    }));
    rocDatasets.push({
      label: 'Tasodifiy model',
      data: [{ x: 0, y: 0 }, { x: 1, y: 1 }],
      borderColor: '#94a3b8',
      borderDash: [6, 5],
      pointRadius: 0,
    });
    createChart('rocChart', {
      type: 'line',
      data: { datasets: rocDatasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'False Positive Rate' } },
          y: { min: 0, max: 1, title: { display: true, text: 'True Positive Rate' } },
        },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  function initializeFeatureCharts(metrics) {
    if (!metrics || !metrics.available) return;
    const groups = metrics.group_importance || {};
    createChart('groupChart', {
      type: 'doughnut',
      data: {
        labels: ['Semantik', 'Fazoviy', 'Vaqtli'],
        datasets: [{
          data: [groups.semantic || 0, groups.spatial || 0, groups.temporal || 0],
          backgroundColor: ['#8b5cf6', '#3868e8', '#f59e0b'],
        }],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
    });

    const topFeatures = (metrics.top_features || []).slice().reverse();
    createChart('featureChart', {
      type: 'bar',
      data: {
        labels: topFeatures.map((item) => item.feature),
        datasets: [{
          label: 'Feature importance',
          data: topFeatures.map((item) => item.importance),
          backgroundColor: '#3868e8',
        }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } },
      },
    });
  }

  function initializePriorityCharts(stats) {
    if (!stats) return;
    createChart('priorityLevelChart', {
      type: 'doughnut',
      data: {
        labels: stats.level_labels || [],
        datasets: [{ data: stats.level_values || [], backgroundColor: ['#dc3545', '#f59e0b', '#22a447'] }],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
    });
    createChart('priorityHistogram', {
      type: 'bar',
      data: {
        labels: stats.histogram_labels || [],
        datasets: [{ label: 'Murojaatlar soni', data: stats.histogram_values || [], backgroundColor: '#3868e8' }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
    createChart('componentChart', {
      type: 'radar',
      data: {
        labels: stats.component_labels || [],
        datasets: [{
          label: 'O‘rtacha qiymat',
          data: stats.component_values || [],
          backgroundColor: 'rgba(139,92,246,.18)',
          borderColor: '#8b5cf6',
          pointBackgroundColor: '#8b5cf6',
        }],
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { r: { beginAtZero: true, max: 1 } } },
    });
    const categories = (stats.category_labels || []).map(
      (label, index) => `${label} (n=${(stats.category_counts || [])[index] || 0})`,
    );
    createChart('priorityCategoryChart', {
      type: 'bar',
      data: {
        labels: categories,
        datasets: [{ label: 'O‘rtacha Pᵢ', data: stats.category_values || [], backgroundColor: '#06b6d4' }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        scales: { x: { beginAtZero: true, max: 1 } },
      },
    });
    createChart('priorityTimelineChart', {
      type: 'line',
      data: {
        labels: stats.timeline_labels || [],
        datasets: [{
          label: 'O‘rtacha Pᵢ',
          data: stats.timeline_values || [],
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245,158,11,.15)',
          fill: true,
          tension: 0.3,
          pointRadius: 2,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, max: 1 } },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  function initializeRiskCharts(stats) {
    if (!stats) return;
    createChart('riskLevelChart', {
      type: 'doughnut',
      data: {
        labels: ['Yuqori', 'O‘rta', 'Past'],
        datasets: [{
          data: [stats.high_count || 0, stats.medium_count || 0, stats.low_count || 0],
          backgroundColor: ['#dc2626', '#f59e0b', '#22c55e'],
        }],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
    });
    createChart('clusterRiskChart', {
      type: 'bar',
      data: {
        labels: stats.risk_labels || [],
        datasets: [{
          label: 'Hₖ',
          data: stats.risk_values || [],
          backgroundColor: (stats.risk_values || []).map(
            (value) => value >= 0.7 ? '#dc2626' : value >= 0.4 ? '#f59e0b' : '#22c55e',
          ),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, max: 1, title: { display: true, text: 'Hₖ' } } },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  function initializeResourceChart(stats) {
    if (!stats) return;
    createChart('resourceChart', {
      type: 'bar',
      data: {
        labels: stats.resource_labels || [],
        datasets: [{
          label: 'Resurs ulushi, %',
          data: stats.resource_values || [],
          backgroundColor: (stats.resource_values || []).map(
            (_, index) => ['#dc2626', '#f59e0b', '#3868e8', '#22c55e', '#8b5cf6'][index % 5],
          ),
        }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, title: { display: true, text: 'Foiz' } } },
      },
    });
  }

  function initializePanel(targetSelector, data) {
    switch (targetSelector) {
      case '#map-tab':
        if (!primaryMap) {
          primaryMap = initializePrimaryMap(data.points, data.riskStats, data.normalizePriority);
        }
        setTimeout(() => primaryMap?.invalidateSize(true), 160);
        break;
      case '#metrics-tab':
        if (!initializedPanels.has(targetSelector)) {
          initializeMetricsCharts(data.metrics);
          initializedPanels.add(targetSelector);
        }
        setTimeout(() => resizeChartsIn(targetSelector), 160);
        break;
      case '#features-tab':
        if (!initializedPanels.has(targetSelector)) {
          initializeFeatureCharts(data.metrics);
          initializedPanels.add(targetSelector);
        }
        setTimeout(() => resizeChartsIn(targetSelector), 160);
        break;
      case '#priority-tab':
        if (!initializedPanels.has(targetSelector)) {
          initializePriorityCharts(data.priorityStats);
          initializedPanels.add(targetSelector);
        }
        setTimeout(() => resizeChartsIn(targetSelector), 160);
        break;
      case '#risk-tab':
        if (!initializedPanels.has(targetSelector)) {
          initializeRiskCharts(data.riskStats);
          initializedPanels.add(targetSelector);
        }
        setTimeout(() => resizeChartsIn(targetSelector), 160);
        break;
      case '#smart-tab':
        if (!smartMap) {
          smartMap = initializeSmartMap(data.points, data.riskStats, data.normalizePriority);
        }
        if (!initializedPanels.has(targetSelector)) {
          initializeResourceChart(data.smartStats);
          initializedPanels.add(targetSelector);
        }
        setTimeout(() => {
          smartMap?.invalidateSize(true);
          resizeChartsIn(targetSelector);
        }, 220);
        break;
      default:
        break;
    }
  }

  function wireTabLifecycle(data) {
    const buttons = document.querySelectorAll('[data-bs-toggle="pill"][data-bs-target]');
    buttons.forEach((button) => {
      const target = button.getAttribute('data-bs-target');
      button.addEventListener('shown.bs.tab', () => initializePanel(target, data));
      // Bootstrap hodisasi yuklanmagan holatda ham tugma bosilishi ishlaydi.
      button.addEventListener('click', () => setTimeout(() => initializePanel(target, data), 80));
    });
  }

  function initialize() {
    const points = safePoints(readJson('geoai-points', []));
    const metrics = readJson('geoai-metrics', {});
    const priorityStats = readJson('priority-stats', {});
    const riskStats = readJson('risk-stats', { clusters: [] });
    const smartStats = readJson('smart-stats', {});
    const normalizePriority = makePriorityNormalizer(points);
    const data = { points, metrics, priorityStats, riskStats, smartStats, normalizePriority };

    wireTabLifecycle(data);
    initializePanel('#map-tab', data);

    window.addEventListener('resize', () => {
      primaryMap?.invalidateSize(false);
      smartMap?.invalidateSize(false);
      chartRegistry.forEach((chart) => chart.resize());
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }

})();
