# SmartGeoAI v1.0 FINAL — Release Checklist

## Release holati

Final Audit:
- 31 check
- 30 PASS
- Critical: 0
- Errors: 0
- Warning: DEBUG=True (local development)
- STATUS: RELEASE CANDIDATE

Final Smoke Test v1.1:
- 25 check
- 23 PASS
- Critical: 0
- Errors: 0
- Warning: 2
- STATUS: SMOKE TEST PASSED

Ikki smoke warning:
- avtomatik DISPATCHER test user topilmadi;
- avtomatik EXECUTOR test user topilmadi.

Bu warninglar release'ni bloklamaydi.

---

## 1. FEATURE FREEZE

SmartGeoAI v1.0 uchun yangi funksiya qo'shilmaydi.

Faqat:
- kritik bug fix;
- production config;
- deploy fix;
- hujjat.

---

## 2. FINAL BACKUP

`release/make_final_backup.ps1` ni workflow2 papkasida ishga tushiring:

```powershell
powershell -ExecutionPolicy Bypass -File .\release\make_final_backup.ps1
```

Backup ichida kamida:
- db.sqlite3
- .env
- data/gsor
- data/problem_datasets
- data/final_audit
- media
- requirements.freeze.txt
- migrations.txt

bo'lishi kerak.

---

## 3. PRODUCTION SETTINGS

Production:
- DEBUG=False
- ALLOWED_HOSTS:
  - fastappeal.uz
  - www.fastappeal.uz
- CSRF_TRUSTED_ORIGINS:
  - https://fastappeal.uz
  - https://www.fastappeal.uz
- SESSION_COOKIE_SECURE=True
- CSRF_COOKIE_SECURE=True
- SECURE_SSL_REDIRECT=True (HTTPS ishlagandan keyin)

`SECRET_KEY` maxfiy saqlansin.

---

## 4. STATIC / MEDIA

Deploy serverda:

```bash
python manage.py collectstatic --noinput
```

Tekshiring:
- portal CSS
- portal JS
- banner
- uploaded attachments
- Leaflet xaritalar

---

## 5. MIGRATIONS

```bash
python manage.py migrate
python manage.py showmigrations
```

Barcha kerakli migration `[X]` bo'lishi kerak.

---

## 6. PRODUCTION SMOKE TEST

Deploydan keyin brauzer orqali:

Public:
- /
- /portal/
- /login/
- /portal/map-data/
- /portal/analytics-data/?days=30
- /portal/research-data/

Superadmin:
- /dashboard/
- /platform-center/
- /gsor-center/
- /geoai-lab/
- /expert-validation/
- /geoai/
- /geoai/system-evaluation/

Operational:
- Dispatcher login
- Worker login
- Citizen Telegram bot

---

## 7. END-TO-END MANUAL TEST

Bitta yangi real test murojaat:

1. Citizen bot -> murojaat
2. AI organization prediction
3. Dispatcher -> accept/assign
4. Worker -> start
5. Worker -> confirmationga yuborish
6. Citizen -> Tasdiqlayman
7. Dashboard -> resolved
8. Public map -> anonim resolved marker

Shu oqim bir marta to'liq o'tsa v1.0 release tasdiqlanadi.

---

## 8. VERSION FREEZE

Release nomi:

`SmartGeoAI v1.0 FINAL`

Tavsiya etilgan Git tag:

```bash
git tag -a v1.0.0 -m "SmartGeoAI v1.0 FINAL"
git push origin v1.0.0
```

Agar Git ishlatilmasa, master papkaning read-only nusxasini saqlang.

---

## 9. ILMIY ESLATMA

`verified_routing_dataset.csv` hozir juda kichik.

Bu dastur release'iga to'sqinlik qilmaydi, ammo:
- GSOR Top-1 / Top-3 / MRR natijalarini final ilmiy natija sifatida berishdan oldin
  verified dataset kengaytirilishi kerak.

Bu v1.0 software release'dan keyingi ilmiy eksperiment bosqichi hisoblanadi.

---

# FINAL STATUS

Software:
**RELEASE CANDIDATE / SMOKE TEST PASSED**

Production deploy + manual E2E o'tgach:
**SmartGeoAI v1.0 FINAL**
