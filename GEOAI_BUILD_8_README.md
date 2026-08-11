# GeoAI SMART-ONLINE — Build 8

Build 8 yashirin Bootstrap tablarida Chart.js va Leaflet komponentlarining noto‘g‘ri o‘lchamda yaratilishi muammosini tuzatadi.

## Asosiy tuzatishlar

- model, belgilar, ustuvorlik va xavf grafiklari faqat tegishli tab ochilganda yaratiladi;
- barcha Chart.js obyektlari registrda saqlanadi va tab qayta ochilganda resize qilinadi;
- SMART-ONLINE xaritasi faqat SMART tab ochilganda yaratiladi;
- Leaflet xaritalari `invalidateSize()` orqali qayta hisoblanadi;
- Chart.js CDN o‘rniga loyihadagi lokal `static/js/plugins/chartjs.min.js` fayli ishlatiladi;
- bo‘sh yoki noto‘g‘ri JSON, koordinata va canvas holatlari xavfsiz qayta ishlanadi.

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

Brauzerda sahifani `Ctrl+F5` bilan yangilang.
