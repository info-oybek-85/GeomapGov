# SmartGeoAI Final Smoke Test v1

Yangi funksiya qo'shmaydi va ma'lumotlarni o'zgartirmaydi.

## Tekshiradi

### Public
- `/`
- `/portal/`
- `/login/`
- public map JSON
- public analytics JSON
- analytics CSV
- research transparency JSON

### Security
Anonim foydalanuvchi ichki sahifalarni 200 bilan ochib yubormasligi tekshiriladi.

### Superadmin
- dashboard
- Platform Center
- GSOR
- GeoAI Lab
- Expert Validation
- GeoAI Analytics
- System Evaluation
- complaints / organizations / users

### Dispatcher
Agar faol DISPATCHER mavjud bo'lsa:
- org dashboard
- reports
- users

### Worker
Agar faol EXECUTOR mavjud bo'lsa:
- tasks
- resolved

Hech qanday parol kerak emas.
Django test client `force_login` orqali read-only GET test qiladi.

## O'rnatish

Fayl:
`dashboard/management/commands/smartgeoai_smoke_test.py`

## Ishga tushirish

```powershell
.\venv\Scripts\python.exe manage.py smartgeoai_smoke_test
```

Natija:
`data/final_audit/smartgeoai_smoke_test.json`

Ideal yakun:
`STATUS: SMOKE TEST PASSED`

Dispatcher yoki Worker test user topilmasa WARN bo'lishi mumkin.
Bu release'ni to'xtatmaydi, lekin qo'lda rol testi qilish tavsiya etiladi.
