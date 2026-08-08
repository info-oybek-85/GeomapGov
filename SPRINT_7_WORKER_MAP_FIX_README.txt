SmartGeoAI Sprint 7 — Worker Map & Dashboard Fix

Asosiy o‘zgarishlar:
1. Xodim geoxaritasidagi cho‘zilgan ko‘k tile chiziqlari tuzatildi.
2. Leaflet tile rasmlari global Argon CSS qoidalaridan himoyalandi.
3. Xarita 150 ms va 650 ms dan keyin invalidateSize() bilan qayta hisoblanadi.
4. Bitta marker bo‘lsa zoom=15, ko‘p marker bo‘lsa fitBounds ishlaydi.
5. Markerlar statusga qarab rangli circleMarker ko‘rinishiga o‘tkazildi.
6. Xodim dashboardida faqat o‘zining faol vazifalari ko‘rsatiladi.
7. Vazifa kartasida fuqaro F.I.O., telefoni, biriktirilgan vaqt va deadline chiqadi.
8. Qo‘ng‘iroq va Google Maps tugmalari qo‘shildi.
9. Hal qilingan murojaatlar faol filtrdan chiqarildi va alohida bo‘limda qoladi.

Ishga tushirish:
  .\\env\\Scripts\\Activate.ps1
  python manage.py check
  python manage.py runserver

Brauzerda Ctrl+F5 bilan yangilang.
