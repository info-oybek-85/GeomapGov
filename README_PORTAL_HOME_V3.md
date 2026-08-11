# SmartGeoAI Portal Home Integration v3

Maqsad:
- `http://127.0.0.1:8000/` anonim foydalanuvchiga SmartGeoAI Portalni ochadi.
- Login qilingan foydalanuvchi roliga qarab o'z ish kabinetiga yo'naltiriladi.
- Hozirgi superadmin dashboard yo'qolmaydi: `/dashboard/`.
- `/portal/` ham ishlashda davom etadi.
- `/login/` o'zgarmaydi.

## Yangi fayl
`dashboard/entry_views.py`

## Yangilanadigan fayl
`dashboard/urls.py`

## Route logikasi

Anonymous:
`/` -> Public Portal

Superadmin:
`/` -> `/dashboard/`

Worker / staff:
`/` -> `/worker/tasks/`

Dispatcher:
`/` -> `/org/`

## O'rnatish

Avval:
```powershell
Copy-Item .\dashboard\urls.py .\dashboard\urls.py.before_portal_home_v3.bak
```

So'ng ZIP tarkibini `workflow2` ustiga ko'chiring.

Tekshirish:
```powershell
.\venv\Scripts\python.exe manage.py check
```

Server:
```powershell
.\venv\Scripts\python.exe manage.py runserver
```

### Test 1 — incognito
Chrome Incognito oynasida:
`http://127.0.0.1:8000/`

Portal chiqishi kerak.

### Test 2 — superadmin
Login qiling.
`http://127.0.0.1:8000/`
ochilganda `/dashboard/` ga o'tishi kerak.

### Test 3 — /portal/
`http://127.0.0.1:8000/portal/`
har doim public portalni ko'rsatadi.

## Muhim
Agar sizning joriy `dashboard/urls.py` faylingizga v2 dan keyin boshqa yangi route qo'shilgan bo'lsa,
faylni to'liq almashtirishdan oldin u route'larni saqlab qoling.
