# GeoAI SMART-ONLINE — Build 7

Build 7 frontend barqarorlashtirish va modullashtirish versiyasidir.

## Asosiy o‘zgarishlar

- `Unexpected token ']'` JavaScript sintaksis xatosi bartaraf etildi.
- GeoAI xaritasi, SMART-ONLINE xaritasi va barcha Chart.js grafiklari alohida funksiyalarga ajratildi.
- Asosiy frontend kodi `static/js/geoai/analytics.js` fayliga ko‘chirildi.
- JSON ma’lumotlari Django `json_script` orqali xavfsiz o‘qiladi.
- Bo‘sh filtr natijalari, noto‘g‘ri koordinatalar va bo‘sh klasterlar uchun himoya qo‘shildi.
- `fitBounds()` faqat haqiqiy chegaralar mavjud bo‘lganda bajariladi.
- Xarita tablari ochilganda `invalidateSize()` avtomatik ishlaydi.
- Build belgisi `GeoAI SMART-ONLINE v7.0` ga yangilandi.
- Filtrlar va SMART qidiruv maydonlari accessibility atributlari bilan to‘ldirildi.

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

Brauzer:

```text
http://127.0.0.1:8000/geoai/
```

## Tekshiruv

Brauzerda `F12 → Console` oynasida `Unexpected token` xatosi bo‘lmasligi kerak.

Frontend sintaksisi Build tayyorlash vaqtida quyidagi buyruq bilan tekshirildi:

```text
node --check static/js/geoai/analytics.js
```

## Muhim fayllar

- `templates/geoai/analytics.html`
- `static/js/geoai/analytics.js`
