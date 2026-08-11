
(function(){
  const root = document.getElementById("publicAnalytics");
  if(!root) return;

  const periodSelect = document.getElementById("publicAnalyticsPeriod");
  const exportLink = document.getElementById("publicAnalyticsExport");

  function loadAnalytics(days){
    const url = new URL(root.dataset.url, window.location.origin);
    url.searchParams.set("days", days);

    if(exportLink){
      const exportUrl = new URL(root.dataset.exportUrl, window.location.origin);
      exportUrl.searchParams.set("days", days);
      exportLink.href = exportUrl.toString();
    }

    root.classList.add("sg-loading");

    fetch(url.toString(), {headers:{"X-Requested-With":"XMLHttpRequest"}})
      .then(r=>r.json())
      .then(data=>{
        renderBars("publicCategoryBars", data.categories || []);
        renderBars("publicOrgBars", data.organizations || []);
        renderTrend(data.trend || []);

        setText("publicAnalyticsTotal", data.summary?.period_total ?? 0);
        setText("publicAnalyticsResolved", data.summary?.period_resolved ?? 0);
        setText("publicAnalyticsActive", data.summary?.period_active ?? 0);
        setText("publicAnalyticsResolvedPct",
                (data.summary?.period_resolved_percent ?? 0) + "%");

        setText("publicAnalyticsPeriodLabel", (data.period_days || days) + " kun");
        setText("publicAnalyticsAllTotal", data.summary?.all_total ?? 0);
        setText("publicAnalyticsAllResolvedPct",
                (data.summary?.all_resolved_percent ?? 0) + "%");

        const msg=document.getElementById("publicAnalyticsMessage");
        if(msg) msg.textContent="";
      })
      .catch(()=>{
        const msg=document.getElementById("publicAnalyticsMessage");
        if(msg) msg.textContent="Ochiq analitika ma'lumotlarini yuklab bo'lmadi.";
      })
      .finally(()=>root.classList.remove("sg-loading"));
  }

  if(periodSelect){
    periodSelect.addEventListener("change",()=>loadAnalytics(periodSelect.value));
  }

  loadAnalytics(periodSelect?.value || 30);

  function renderBars(id,items){
    const wrap=document.getElementById(id);
    if(!wrap) return;
    const max=Math.max(...items.map(x=>x.count),1);
    wrap.innerHTML=items.map(x=>`
      <div class="sg-bar-row">
        <div class="sg-bar-label" title="${esc(x.name)}">${esc(x.name)}</div>
        <div class="sg-bar-track">
          <div class="sg-bar-fill" style="width:${Math.max(3,(x.count/max)*100)}%"></div>
        </div>
        <div class="sg-bar-value">${x.count}</div>
      </div>
    `).join("") || '<div style="font-size:12px;color:#8898aa">Ma’lumot yo‘q.</div>';
  }

  function renderTrend(items){
    const wrap=document.getElementById("publicTrend30d");
    if(!wrap) return;
    const max=Math.max(...items.map(x=>x.total),1);
    wrap.innerHTML=items.map(x=>{
      const totalH=Math.max(2,(x.total/max)*100);
      const resolvedH=Math.max(0,(x.resolved/max)*100);
      return `<div class="sg-trend-col" title="${esc(x.date)} · jami ${x.total} · hal ${x.resolved}">
        <div class="sg-trend-resolved" style="height:${resolvedH}%"></div>
        <div class="sg-trend-total" style="height:${totalH}%"></div>
      </div>`;
    }).join("");
  }

  function setText(id,val){
    const el=document.getElementById(id);
    if(el) el.textContent=val;
  }

  function esc(v){
    return String(v||"")
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;")
      .replaceAll("'","&#039;");
  }
})();
