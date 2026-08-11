# GeoAI SMART-ONLINE — Build 6 (Stability Release)

Build 6 Build 5 dagi SMART-ONLINE monitoring modulini loyiha bazasining haqiqiy sana tipi bilan moslashtiradi.

## Tuzatilgan muammolar

- `datetime.datetime - datetime.date` TypeError bartaraf etildi.
- `BaseModel.created_at` DateField va kelajakdagi DateTimeField bilan bir xil ishlaydi.
- timezone-aware va timezone-naive qiymatlar xavfsiz qayta ishlanadi.
- kelajak sanalari “so‘nggi 24 soat” statistikasi ichiga kiritilmaydi.
- sana bo‘yicha dinamik filtr DateField uchun to‘g‘ri `__gte` / `__lte` so‘rovlaridan foydalanadi.
- SMART panelga `last_7d` ko‘rsatkichi qo‘shildi.
- sana mosligi uchun avtomatik unit-testlar qo‘shildi.

## Ishga tushirish

```powershell
py -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py analyze_geoai --radius 0.5 --days 30
python manage.py analyze_risk --eps 35 --min-samples 3 --bandwidth 45
python manage.py test geoai
python manage.py runserver
```

Brauzer: `http://127.0.0.1:8000/geoai/`

## Eslatma

Yangi model yoki jadval qo‘shilmagan. Build 4/5 migratsiyalari qo‘llangan bo‘lsa, qo‘shimcha `makemigrations` talab qilinmaydi.
