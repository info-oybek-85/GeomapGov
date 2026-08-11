
(function(){
  const root = document.getElementById("researchTransparency");
  if(!root) return;

  fetch(root.dataset.url, {headers:{"X-Requested-With":"XMLHttpRequest"}})
    .then(r=>r.json())
    .then(data=>{
      setText("rtTop1", fmt(data.metrics?.top1_accuracy));
      setText("rtTop3", fmt(data.metrics?.top3_accuracy));
      setText("rtMrr", fmt(data.metrics?.mrr));
      setText("rtReference", data.metrics?.reference_records ?? 0);
      setText("rtRecommendation", data.model?.recommendation || "—");
      setText("rtMetricsUpdated", prettyDate(data.freshness?.gsor_metrics_updated_at));
      setText("rtLatestReport", prettyDate(data.freshness?.latest_report_at));

      const level = document.getElementById("rtLevel");
      if(level){
        level.textContent = "Ilmiy baholash darajasi: " + (data.model?.evaluation_level_label || "—");
        level.className = "sg-research-level " + (data.model?.evaluation_level || "pilot");
      }

      const tags = document.getElementById("rtMethodTags");
      if(tags){
        tags.innerHTML = (data.methodology?.principles || [])
          .map(x=>`<span class="sg-method-tag">${esc(x)}</span>`).join("");
      }
    })
    .catch(()=>{
      setText("rtRecommendation","Ilmiy shaffoflik ma’lumotlarini yuklab bo‘lmadi.");
    });

  function fmt(v){
    if(v === null || v === undefined || v === "") return "—";
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(3) : String(v);
  }
  function prettyDate(v){
    if(!v) return "—";
    try{return new Date(v).toLocaleString("uz-UZ")}catch(e){return v}
  }
  function setText(id,val){
    const el=document.getElementById(id); if(el) el.textContent=val;
  }
  function esc(v){
    return String(v||"")
      .replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")
      .replaceAll('"',"&quot;").replaceAll("'","&#039;");
  }
})();
