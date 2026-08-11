# SmartGeoAI Main Navigation v2

Bu patch aynan yuborilgan master fayllar asosida tayyorlangan.

## Almashtiriladigan fayllar
- `templates/base.html`
- `templates/superadmin/dashboard.html`
- `dashboard/urls.py`

## Yangi / yangilanadigan fayllar
- `dashboard/platform_views.py`
- `templates/superadmin/platform_center.html`
- `templates/superadmin/gsor_center.html`

## O'rnatish
Avval master fayllardan backup oling.

Patch papka strukturasini saqlagan holda `workflow2` ustiga ko'chiring.

Keyin:
```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

## Expert Validation xatosi bo'lsa
Agar:
`no such table: organizations_organizationpredictionfeedback`
chiqsa, bu navigatsiya xatosi emas — Expert Validation migratsiyasi bazada yo'q.

Tekshirish:
```powershell
.\venv\Scripts\python.exe manage.py showmigrations organizations
```

So'ng:
```powershell
.\venv\Scripts\python.exe manage.py makemigrations organizations
.\venv\Scripts\python.exe manage.py migrate
```

`platform_center` ushbu jadval mavjud bo'lmasa ham 500 bermaydi; kartada migratsiya zarurligi ko'rsatiladi.
