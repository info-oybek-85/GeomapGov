SMARTGEOAI — FUQARO TASDIG‘I XAVFSIZLIK TUZATMASI

1. Tashkilot admini va xodim yakuniy “Hal qilindi” statusini bera olmaydi.
2. Xodim faqat “Ish bajarildi” orqali pending_confirmation holatiga o‘tkazadi.
3. Botdagi tasdiqlash tugmasi faqat pending_confirmation holatida ko‘rinadi.
4. API /reports/<id>/resolve/ boshqa holatlarda HTTP 409 qaytaradi.
5. Fuqaro tasdiqlaganda citizen_confirmed_at, resolved_at va audit izohi yoziladi.
6. Tashkilot sahifasidagi qo‘lda “Fuqaro tasdiqladi” formasi olib tashlandi.

Ishga tushirish:
  python manage.py check
  python manage.py runserver
Botni qayta ishga tushiring:
  cd bot
  python main.py

Migratsiya talab qilinmaydi.
