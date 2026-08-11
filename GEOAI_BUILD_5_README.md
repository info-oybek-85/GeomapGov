# GeoAI SMART-ONLINE — Build 5

Build 5 dissertatsiyaning 4-ilmiy yangiligini dasturda amalga oshiradi:

- ko‘p qatlamli interaktiv Web-GIS (OSM, Humanitarian, Dark CARTO);
- kategoriya, ustuvorlik, xavf va sana bo‘yicha dinamik filtrlash;
- xarita nuqtasi va radius bo‘yicha fazoviy qidiruv;
- real vaqt monitoring KPIlari;
- klaster xavfi asosida avtomatik qaror tavsiyalari;
- javob muddati va mas’ul tashkilotni ko‘rsatish;
- integral xavfga mutanosib resurs taqsimoti;
- SMART-ONLINE tavsiyalarini CSV formatida eksport qilish;
- JSON API: `/geoai/api/smart-online/`.

## Ishga tushirish

```powershell
py -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py analyze_geoai --radius 0.5 --days 30
python manage.py analyze_risk --eps 35 --min-samples 3 --bandwidth 45
python manage.py runserver
```

Brauzerda: `http://127.0.0.1:8000/geoai/`

## 4-ilmiy yangilik zanjiri

`Risk_k → GeoLayers → SpatialQuery → DynamicFilter → SmartMonitoring → DecisionSupport → ResourceAllocation → SMART-ONLINE`

## Eslatma

Build 5 yangi ma’lumotlar bazasi jadvalini talab qilmaydi. Build 4 migratsiyalari qo‘llangan bo‘lsa, qo‘shimcha migration zarur emas.
