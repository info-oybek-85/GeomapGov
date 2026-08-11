# SmartGeoAI Public Portal v2 — Delta Patch

Bu patch v1 ishlayotgan portal ustiga faqat 3 ta faylni almashtiradi:

- `dashboard/portal_views.py`
- `templates/public/portal.html`
- `static/css/smartgeoai-portal.css`

`dashboard/urls.py`, login view, settings va banner rasmiga tegmaydi.

## Yangiliklar
- kattaroq hero/banner
- premium ikki ustunli login modal
- CTA mikroanimatsiyalari
- real Platform Status:
  - AI / GSOR Engine
  - Telegram Bot
  - GIS Monitoring
  - Database
- desktop/tablet/mobile responsive

## O'rnatish
ZIP tarkibini `workflow2` ustiga ko'chiring.

Keyin:
```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

Brauzerda:
`Ctrl + F5`

Oching:
`http://127.0.0.1:8000/portal/`
