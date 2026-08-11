# SmartGeoAI Mobile Workforce V6

## Yangiliklar
- EXECUTOR web menyusidan Xodimlar olib tashlandi.
- Xodim asosiy sahifasi faqat o'ziga biriktirilgan faol murojaatlarni ko'rsatadi.
- Hal qilingan murojaatlar alohida `/worker/resolved/` sahifasida.
- Telegram xabari: fuqaro FIO, telefon, muddat, xarita va Ishni boshlash tugmasi.
- Bot orqali Ishni boshlash.
- Bot orqali foto/fayl dalil va izoh yuborib fuqaro tasdig'iga topshirish.
- Fuqaro lokatsiyasi: joriy lokatsiya yoki qidiruvli xarita.

## Ishga tushirish
```powershell
.\env\Scripts\Activate.ps1
python manage.py check
python manage.py runserver
```
Bot:
```powershell
cd bot
..\env\Scripts\python.exe main.py
```

Yangi model qo'shilmagan, migratsiya talab qilinmaydi.

## Eslatma
Manzil qidiruvi OpenStreetMap Nominatim xizmatidan foydalanadi va internet talab qiladi.
