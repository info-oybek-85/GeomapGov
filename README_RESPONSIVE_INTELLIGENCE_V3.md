# SmartGeoAI Responsive Intelligence v3

Maqsad:
1. Platform Center kartalarini real holat kartalariga aylantirish.
2. Admin interfeysini telefon va planshetlarda chiroyli ko'rsatish.

## Fayllar
- templates/base.html
- templates/superadmin/dashboard.html
- templates/superadmin/platform_center.html
- templates/superadmin/gsor_center.html
- dashboard/platform_views.py
- dashboard/urls.py

## Mobil o'zgarishlar
- 1200px dan kichik ekranda sidebar yashiriladi.
- Navbar ichida hamburger menyu chiqadi.
- Fon overlay bilan sidebar ochiladi/yopiladi.
- KPI va modul kartalari telefonda 1 ustun.
- GSOR metrikalari 2x2 ko'rinish.
- Xarita balandligi mobilga mos.
- Dashboard filterlari bitta ustunga tushadi.
- Katta jadvallar gorizontal scroll bilan ishlaydi.

## O'rnatish
Avval backup:
```powershell
Copy-Item .\templates\base.html .\templates\base.html.bak
Copy-Item .\templates\superadmin\dashboard.html .\templates\superadmin\dashboard.html.bak
Copy-Item .\dashboard\urls.py .\dashboard\urls.py.bak
```

ZIP ichidagi fayllarni `workflow2` ustiga ko'chiring.

Keyin:
```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

Telefon test:
- Chrome DevTools → Toggle device toolbar
- 390x844 (iPhone/Android)
- 768x1024 (tablet)
yoki lokal serverni LAN IP orqali telefondan oching.
