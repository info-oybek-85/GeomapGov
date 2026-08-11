SMARTGEOAI — TASHKILOT VA IJROCHI WORKFLOW MVP
================================================

Qo‘shilgan imkoniyatlar:
1. Tashkilot administratori murojaatni xodimga biriktiradi.
2. Bajarish muddati (soat) belgilanadi.
3. Xodim /worker/tasks/ kabinetida faqat o‘z vazifalarini ko‘radi.
4. Vazifalar geoxaritada ko‘rsatiladi.
5. Xodim “Ishni boshlash” tugmasini bosadi.
6. Xodim bajarilgan ish izohini kiritib, tasdiqqa yuboradi.
7. Murojaat “Fuqaro tasdig‘i kutilmoqda” holatiga o‘tadi.
8. Tashkilot administratori fuqaro tasdig‘ini qayd etib murojaatni yopadi.
9. Fuqaro rozi bo‘lmasa murojaat “Qayta ishga yuborildi” holatiga o‘tadi.
10. Qabul, biriktirish, boshlash, bajarish, tasdiqlash va yakunlash vaqtlari saqlanadi.

ISHGA TUSHIRISH:
----------------
1. Virtual muhitni faollashtiring.
2. Loyiha papkasida quyidagilarni bajaring:

   python manage.py migrate
   python manage.py check
   python manage.py runserver

3. Tashkilot administratori:
   /org/

4. Ijrochi xodim kabineti:
   /worker/tasks/

MUHIM:
------
- Xodim UserChoices.EXECUTOR turida bo‘lishi kerak.
- Xodim OrganizationMember orqali tegishli tashkilotga ROLE_STAFF sifatida bog‘langan bo‘lishi kerak.
- Tashkilot administratori ROLE_ADMIN bo‘lishi kerak.
- Productionga chiqarishdan oldin .env ichidagi token va SECRET_KEYlarni almashtiring.
