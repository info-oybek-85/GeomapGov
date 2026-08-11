SMARTGEOAI — TASHKILOTNI ML ORQALI TAVSIYA QILISH PATCHI

FAQAT QUYIDAGI FAYLLARNI MASTER LOYIHAGA KO‘CHIRING:

1) organizations/organization_classifier.py   (yangi fayl)
2) organizations/views.py
3) organizations/urls.py
4) bot/app/api.py
5) bot/app/keyboards.py
6) bot/app/handlers/report.py

O‘RNATISH:
- ZIP ichidagi papka tuzilishini saqlagan holda workflow2 ustiga nusxalang.
- venv, db.sqlite3 va .env fayllariga tegmang.
- Yangi model yoki DB maydoni qo‘shilmagan, migratsiya kerak emas.

TEKSHIRISH:
1. .\venv\Scripts\python.exe manage.py check
2. .\venv\Scripts\python.exe manage.py runserver
3. Ikkinchi terminal:
   .\venv\Scripts\python.exe .\bot\main.py

BOT SINOVI:
- “Murojaat yuborish”
- Matn: “Mahallamizda ikki kundan beri svet yo‘q, transformator ishlamayapti”
- Media va lokatsiya bosqichidan o‘ting.
- Bot “Energetika vazirligi”ni tavsiya qilishi kerak.

- Matn: “Ko‘chamizdagi chiqindilar bir haftadan beri olib ketilmayapti”
- Bot Ekologiya tashkilotini tavsiya qilishi kerak.

ISH JARAYONI:
- Ishonchlilik >= 48%: tashkilot tavsiyasi chiqadi.
- “Tavsiya etilgan tashkilotni tanlash”: shu tashkilot tanlanadi.
- “Boshqa tashkilotni tanlash”: eski ro‘yxat ochiladi, “Bilmayman” ham saqlanadi.
- Past ishonchlilik: to‘g‘ridan-to‘g‘ri eski tashkilotlar ro‘yxati ochiladi.

ESLATMA:
Bu birinchi gibrid MVP: mavjud TF-IDF/RandomForest kategoriya modeli + tashkilot vakolatlari qoidalari.
Keyingi bosqichda ekspert tasdiqlagan “murojaat matni -> tashkilot” dataset yig‘ilgach,
to‘g‘ridan-to‘g‘ri tashkilot klassifikatori qayta o‘qitiladi.
