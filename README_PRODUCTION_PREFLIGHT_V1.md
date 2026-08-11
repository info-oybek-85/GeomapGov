# SmartGeoAI Production Preflight v1

Bu SmartGeoAI v1.0 FINAL oldidan oxirgi avtomatik production tekshiruv.

## Muhim
Lokal developmentda `DEBUG=True` bilan `check --deploy` security warninglar berishi normal.

Haqiqiy production preflightni `DEBUG=False` va production settings bilan bajaring.

## Ishga tushirish

`workflow2` papkasida:

```powershell
powershell -ExecutionPolicy Bypass -File .\release\smartgeoai_production_preflight.ps1
```

Skript ketma-ket:

1. `manage.py check`
2. `manage.py check --deploy`
3. `manage.py migrate --check`
4. `smartgeoai_final_audit`
5. `smartgeoai_smoke_test`
6. static/media
7. GSOR/final audit artifactlarini

tekshiradi.

Ideal yakun:

```text
STATUS: PRODUCTION PREFLIGHT PASSED
```

## Production settings

Kamida:

```python
DEBUG = False

ALLOWED_HOSTS = [
    "fastappeal.uz",
    "www.fastappeal.uz",
]

CSRF_TRUSTED_ORIGINS = [
    "https://fastappeal.uz",
    "https://www.fastappeal.uz",
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)
```

HTTPS to'liq ishlagandan keyin:

```python
SECURE_SSL_REDIRECT = True
```

HSTS ni birdan katta qiymatda yoqmang. Avval kichik qiymat bilan sinab,
keyin oshirish xavfsizroq.

## Deploydan keyingi manual E2E

Bitta murojaat:

Citizen bot
→ AI routing
→ Dispatcher
→ Worker
→ Citizen confirmation
→ RESOLVED
→ Public anonymous map

to'liq o'tishi kerak.

Shundan keyin:

`SmartGeoAI v1.0 FINAL`
