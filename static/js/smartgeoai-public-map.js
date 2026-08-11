
(function(){
  const mapEl = document.getElementById("publicResolvedMap");
  if(!mapEl || typeof L === "undefined") return;

  const categoryColors = {};
  const palette = [
    "#2dce89","#5e72e4","#11cdef","#fb6340",
    "#f5365c","#825ee4","#20c997","#ff9f43",
    "#344767","#8898aa"
  ];

  const map = L.map("publicResolvedMap", {
    scrollWheelZoom: false
  }).setView([41.3111, 69.2797], 6);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap"
  }).addTo(map);

  // MarkerCluster plugin if loaded, otherwise fallback to layerGroup
  const clusterGroup = (L.markerClusterGroup)
    ? L.markerClusterGroup({
        showCoverageOnHover:false,
        maxClusterRadius:48,
        spiderfyOnMaxZoom:true
      })
    : L.layerGroup();

  clusterGroup.addTo(map);

  const markers = [];
  let allPoints = [];

  fetch(mapEl.dataset.url, {
    headers: {"X-Requested-With":"XMLHttpRequest"}
  })
  .then(r => r.json())
  .then(data => {
    allPoints = data.points || [];
    buildCategoryFilter(data.categories || []);
    renderPoints(allPoints);

    const count = document.getElementById("publicMapCount");
    if(count) count.textContent = data.count || 0;

    renderTopOrganizations(data.top_organizations || []);
  })
  .catch(() => {
    const msg = document.getElementById("publicMapMessage");
    if(msg) msg.textContent = " Geoxarita ma'lumotlarini yuklashda xatolik yuz berdi.";
  });

  function getColor(category){
    if(!categoryColors[category]){
      const idx = Object.keys(categoryColors).length % palette.length;
      categoryColors[category] = palette[idx];
    }
    return categoryColors[category];
  }

  function renderPoints(points){
    clusterGroup.clearLayers();
    markers.length = 0;

    points.forEach(p => {
      const color = getColor(p.category || "Boshqa");

      const marker = L.circleMarker([p.lat, p.lng], {
        radius:8,
        weight:2,
        color:"#ffffff",
        fillColor:color,
        fillOpacity:.94
      });

      marker._sgCategory = p.category || "Boshqa";

      marker.bindPopup(`
        <div style="min-width:220px">
          <div style="font-size:11px;color:#2dce89;font-weight:800;margin-bottom:5px">✓ HAL QILINGAN</div>
          <div style="font-weight:800;color:#172b4d;margin-bottom:7px">${escapeHtml(p.category || "Murojaat")}</div>
          <div style="font-size:12px;color:#525f7f;margin-bottom:6px">${escapeHtml(p.summary || "")}</div>
          <div style="font-size:11px;color:#8898aa">${escapeHtml(p.organization || "")}</div>
        </div>`);

      markers.push(marker);
      clusterGroup.addLayer(marker);
    });

    if(points.length){
      const bounds = L.latLngBounds(points.map(p => [p.lat,p.lng]));
      map.fitBounds(bounds, {padding:[35,35], maxZoom:12});
    }
  }

  function buildCategoryFilter(categories){
    const wrap = document.getElementById("publicMapCategories");
    if(!wrap) return;
    wrap.innerHTML = "";

    const allBtn = makeFilterButton("Barchasi", categories.reduce((a,b)=>a+b.count,0), "");
    allBtn.classList.add("active");
    wrap.appendChild(allBtn);

    categories.forEach(item => {
      const btn = makeFilterButton(item.name, item.count, item.name);
      btn.style.setProperty("--sg-cat-color", getColor(item.name));
      wrap.appendChild(btn);
    });
  }

  function makeFilterButton(label,count,category){
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "sg-map-filter";
    btn.dataset.category = category;
    btn.innerHTML = `<span class="sg-map-filter-dot"></span>${escapeHtml(label)} <b>${count}</b>`;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".sg-map-filter").forEach(x=>x.classList.remove("active"));
      btn.classList.add("active");
      const filtered = category
        ? allPoints.filter(p => (p.category || "Boshqa") === category)
        : allPoints;
      renderPoints(filtered);
      const countEl = document.getElementById("publicMapVisibleCount");
      if(countEl) countEl.textContent = filtered.length;
    });
    return btn;
  }

  function renderTopOrganizations(items){
    const wrap = document.getElementById("publicMapTopOrgs");
    if(!wrap) return;
    wrap.innerHTML = items.map((x,i)=>`
      <div class="sg-top-org-row">
        <span>${i+1}. ${escapeHtml(x.name)}</span>
        <b>${x.count}</b>
      </div>`).join("");
  }

  function escapeHtml(value){
    return String(value || "")
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;")
      .replaceAll("'","&#039;");
  }
})();
