# SmartGeoAI Public Map v2 + Platform Status v2

Bu delta patch v4.1 ishlayotgan portal ustiga qo'yiladi.

## Public Map v2
- marker cluster;
- kategoriya bo'yicha rang;
- kategoriya filterlari;
- top tashkilotlar;
- ko'rinayotgan markerlar soni;
- privacy saqlanadi;
- faqat `resolved`.

## Platform Status v2
- Healthy / Warning / Critical summary;
- AI/GSOR reference dataset hajmi;
- Telegram konfiguratsiyasi;
- GIS qamrovi;
- DB real SELECT 1 tekshiruvi.

## Almashtiriladigan fayllar
- dashboard/portal_views.py
- templates/public/portal.html
- static/css/smartgeoai-portal.css
- static/js/smartgeoai-public-map.js

URL o'zgarmaydi.

## O'rnatish
ZIPni `workflow2` ustiga ko'chiring.

Keyin:
```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

Brauzer:
Ctrl+F5

Test:
- `/portal/`
- `/portal/map-data/`
