from pathlib import Path
import shutil, sys

BASE = Path(__file__).resolve().parents[1]
URLS = BASE / "dashboard" / "urls.py"
BASE_HTML = BASE / "templates" / "base.html"
DASH_HTML = BASE / "templates" / "superadmin" / "dashboard.html"

def backup(p):
    b = p.with_suffix(p.suffix + ".before_main_navigation.bak")
    if not b.exists():
        shutil.copy2(p, b)
        print(f"Backup: {b}")

def patch_urls():
    p=URLS; backup(p); s=p.read_text(encoding="utf-8")
    if "from . import platform_views" not in s:
        s=s.replace("from . import views, organization_admin", "from . import views, organization_admin\nfrom . import platform_views")
    if 'name="platform_center"' not in s:
        s=s.replace("urlpatterns = [", 'urlpatterns = [\n    path("platform-center/", platform_views.platform_center, name="platform_center"),\n    path("gsor-center/", platform_views.gsor_center, name="gsor_center"),')
    p.write_text(s,encoding="utf-8"); print("OK: dashboard/urls.py")

def patch_base():
    p=BASE_HTML; backup(p); s=p.read_text(encoding="utf-8")
    if "SMARTGEOAI_INTELLIGENCE_NAV_BEGIN" in s:
        print("SKIP: base.html allaqachon patchlangan"); return
    anchor='''    <li class="nav-item">\n      <a class="nav-link {% if request.resolver_match.url_name == 'users' or request.resolver_match.url_name == 'user_detail' %}"'''
    block='''    <!-- SMARTGEOAI_INTELLIGENCE_NAV_BEGIN -->
    <li class="nav-item mt-3"><h6 class="ps-4 ms-2 text-uppercase text-xs font-weight-bolder opacity-6">AI va ilmiy boshqaruv</h6></li>
    <li class="nav-item"><a class="nav-link {% if request.resolver_match.url_name == 'platform_center' %}active{% endif %}" href="{% url 'dashboard:platform_center' %}"><div class="icon icon-shape icon-sm border-radius-md text-center me-2 d-flex align-items-center justify-content-center"><i class="ni ni-app text-primary text-sm opacity-10"></i></div><span class="nav-link-text ms-1">Platform markazi</span></a></li>
    <li class="nav-item"><a class="nav-link {% if request.resolver_match.url_name == 'system_evaluation' %}active{% endif %}" href="{% url 'geoai:system_evaluation' %}"><div class="icon icon-shape icon-sm border-radius-md text-center me-2 d-flex align-items-center justify-content-center"><i class="ni ni-sound-wave text-info text-sm opacity-10"></i></div><span class="nav-link-text ms-1">Tizim baholash</span></a></li>
    <li class="nav-item"><a class="nav-link {% if request.resolver_match.url_name == 'expert_validation_queue' or request.resolver_match.url_name == 'expert_validation_detail' %}active{% endif %}" href="{% url 'dashboard:expert_validation_queue' %}"><div class="icon icon-shape icon-sm border-radius-md text-center me-2 d-flex align-items-center justify-content-center"><i class="ni ni-check-bold text-warning text-sm opacity-10"></i></div><span class="nav-link-text ms-1">AI ekspert tekshiruvi</span></a></li>
    <li class="nav-item"><a class="nav-link {% if request.resolver_match.url_name == 'gsor_center' %}active{% endif %}" href="{% url 'dashboard:gsor_center' %}"><div class="icon icon-shape icon-sm border-radius-md text-center me-2 d-flex align-items-center justify-content-center"><i class="ni ni-compass-04 text-success text-sm opacity-10"></i></div><span class="nav-link-text ms-1">GSOR Routing</span></a></li>
    <!-- SMARTGEOAI_INTELLIGENCE_NAV_END -->

'''
    if anchor not in s: raise RuntimeError("base.html ichida superadmin Foydalanuvchilar anchor topilmadi.")
    s=s.replace(anchor,block+anchor,1); p.write_text(s,encoding="utf-8"); print("OK: templates/base.html")

def patch_dashboard():
    p=DASH_HTML; backup(p); s=p.read_text(encoding="utf-8")
    if "SMARTGEOAI_MODULE_CARDS_BEGIN" in s:
        print("SKIP: dashboard allaqachon patchlangan"); return
    anchor="<!-- ===================== MAP SECTION ===================== -->"
    block='''<!-- SMARTGEOAI_MODULE_CARDS_BEGIN -->
<div class="card mb-4"><div class="card-header pb-0"><div class="d-flex justify-content-between align-items-center"><div><h6 class="mb-1">SmartGeoAI intellektual boshqaruv modullari</h6><p class="text-sm text-secondary mb-0">Ilmiy tahlil, sifat nazorati va routing modullariga tezkor kirish.</p></div><a href="{% url 'dashboard:platform_center' %}" class="btn btn-sm btn-outline-primary mb-0">Barchasini ochish →</a></div></div><div class="card-body"><div class="row g-3">
<div class="col-xl-3 col-md-6"><a href="{% url 'geoai:analytics' %}" class="text-decoration-none"><div class="border-radius-lg p-3 h-100" style="border:1px solid rgba(0,0,0,.06);background:#f8f9fe"><div class="d-flex align-items-center gap-3"><div class="icon icon-shape bg-gradient-info shadow text-center rounded-circle"><i class="ni ni-chart-bar-32 text-white"></i></div><div><div class="font-weight-bold text-dark">GeoAI Analytics</div><div class="text-xs text-secondary">Xarita, hotspot, risk</div></div></div></div></a></div>
<div class="col-xl-3 col-md-6"><a href="{% url 'geoai:system_evaluation' %}" class="text-decoration-none"><div class="border-radius-lg p-3 h-100" style="border:1px solid rgba(0,0,0,.06);background:#f8f9fe"><div class="d-flex align-items-center gap-3"><div class="icon icon-shape bg-gradient-primary shadow text-center rounded-circle"><i class="ni ni-sound-wave text-white"></i></div><div><div class="font-weight-bold text-dark">Tizim baholash</div><div class="text-xs text-secondary">12 modul + K-Fold</div></div></div></div></a></div>
<div class="col-xl-3 col-md-6"><a href="{% url 'dashboard:expert_validation_queue' %}" class="text-decoration-none"><div class="border-radius-lg p-3 h-100" style="border:1px solid rgba(0,0,0,.06);background:#f8f9fe"><div class="d-flex align-items-center gap-3"><div class="icon icon-shape bg-gradient-warning shadow text-center rounded-circle"><i class="ni ni-check-bold text-white"></i></div><div><div class="font-weight-bold text-dark">Expert Validation</div><div class="text-xs text-secondary">AI taxminlarini tekshirish</div></div></div></div></a></div>
<div class="col-xl-3 col-md-6"><a href="{% url 'dashboard:gsor_center' %}" class="text-decoration-none"><div class="border-radius-lg p-3 h-100" style="border:1px solid rgba(0,0,0,.06);background:#f8f9fe"><div class="d-flex align-items-center gap-3"><div class="icon icon-shape bg-gradient-success shadow text-center rounded-circle"><i class="ni ni-compass-04 text-white"></i></div><div><div class="font-weight-bold text-dark">GSOR Routing</div><div class="text-xs text-secondary">Top-1 / Top-3 / MRR</div></div></div></div></a></div>
</div></div></div>
<!-- SMARTGEOAI_MODULE_CARDS_END -->

'''
    if anchor not in s: raise RuntimeError("superadmin/dashboard.html ichida MAP SECTION anchor topilmadi.")
    s=s.replace(anchor,block+anchor,1); p.write_text(s,encoding="utf-8"); print("OK: templates/superadmin/dashboard.html")

if __name__=="__main__":
    for p in (URLS,BASE_HTML,DASH_HTML):
        if not p.exists(): print("ERROR:",p); sys.exit(1)
    patch_urls(); patch_base(); patch_dashboard()
    print("\nMain Navigation Integration muvaffaqiyatli qo'shildi.")
