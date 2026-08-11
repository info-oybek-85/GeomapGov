# SmartGeoAI V7 — Worker Bot and Menu Fix

Tuzatildi:

1. Tashkilot a'zoligi `role=staff` bo'lgan foydalanuvchiga xodim menyusi ko'rsatiladi, hatto eski bazada `user_type=DISPATCHER` bo'lib qolgan bo'lsa ham.
2. Xodim menyusida `Xodimlar` bo'limi ko'rinmaydi; `Hal qilingan murojaatlar` mavjud.
3. Botdagi vazifa tafsilotida fuqaroning F.I.O. va telefon raqami ko'rsatiladi.
4. Telefon mavjud bo'lsa `Fuqaroga qo'ng'iroq` tugmasi chiqadi.
5. `assigned/reopened` holatida `Ishni boshlash`, `in_progress` holatida `Ish bajarildi — tasdiqlashga yuborish` tugmasi chiqadi.
6. Deadline ISO formatdan o'qilishi qulay sana-vaqt formatiga o'tkaziladi.

Ishga tushirish:

```powershell
.\env\Scripts\Activate.ps1
python manage.py check
python manage.py runserver
```

Botni qayta ishga tushirish:

```powershell
cd bot
..\env\Scripts\python.exe main.py
```
