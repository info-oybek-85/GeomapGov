# SmartGeoAI Public Portal v1

Mavjud login va autentifikatsiya logikasiga tegmaydigan public portal.

## Yangi sahifa
`/portal/`

## Nima ishlaydi?
- Tanlangan SmartGeoAI banner
- Real DB statistikasi
- Responsive desktop/tablet/mobile dizayn
- Premium login modal
- Modal POST mavjud `dashboard:login` endpointiga yuboradi
- Telegram CTA
- Platforma imkoniyatlari

## O'rnatish
ZIP ichidagi:
- `dashboard/portal_views.py`
- `templates/public/portal.html`
- `static/css/smartgeoai-portal.css`
- `static/img/smartgeoai-portal-banner.png`

fayllarini `workflow2` ga ko'chiring.

`dashboard/urls.py` ga `DASHBOARD_URLS_SNIPPET.txt` dagi qatorlarni qo'shing.

`config/settings.py` ga:
```python
SMARTGEOAI_TELEGRAM_BOT_URL = "https://t.me/YOUR_BOT_USERNAME"
```
qo'shing va haqiqiy bot username yozing.

Keyin:
```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

Oching:
`http://127.0.0.1:8000/portal/`

## Muhim
v1 portal eski `/login/` sahifasini o'chirmaydi. Avval portalni tekshirib olamiz.
Keyingi bosqichda xohlasangiz `/` yoki `/login/` ni portalga yo'naltiramiz.
