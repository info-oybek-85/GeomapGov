# SmartGeoAI Responsive Hotfix v3.1

Bu hotfix v3 dagi desktop dizayn buzilishini bekor qiladi.

Asos:
- oldingi ishlagan Main Navigation v2 desktop dizayni;
- responsive qoidalar faqat `max-width: 768px` da ishlaydi.

## Natija
Desktop:
- v2 ko'rinishi 100% saqlanadi;
- sidebar kontent ustiga chiqmaydi;
- Platform Center kartalari avvalgi chiroyli gridda qoladi.

Telefon:
- sidebar drawer sifatida yashirinadi;
- hamburger orqali ochiladi;
- overlay bosilganda yopiladi;
- kartalar bitta ustunga tushadi;
- xarita va filtrlar telefon ekraniga moslashadi;
- katta jadvallar horizontal scroll qiladi.

## O'rnatish

1. Hozirgi v3 fayllardan backup oling.
2. ZIP fayllarini `workflow2` ustiga ko'chiring.
3. Serverni qayta ishga tushiring:

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

4. Brauzerda Ctrl+F5 qiling.

Telefon test:
Chrome DevTools -> 390x844.
