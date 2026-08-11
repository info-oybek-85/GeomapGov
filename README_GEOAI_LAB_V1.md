# SmartGeoAI GeoAI Lab v1

Bu patch mavjud ishlayotgan Platform Center va Dashboardni buzmasdan yangi ilmiy workspace qo'shadi.

## Yangi sahifa
`/geoai-lab/`

## Yangi fayllar
- `dashboard/lab_views.py`
- `templates/superadmin/geoai_lab.html`
- `static/css/smartgeoai-design-system.css`

## Yangilanadigan fayl
- `dashboard/urls.py`

## Platform Center kartasi
`GEOAI_LAB_PLATFORM_CENTER_CARD_SNIPPET.html` ichidagi blokni mavjud
`templates/superadmin/platform_center.html` grid ichiga qo'shish mumkin.

## O'rnatish
ZIP ichidagi fayllarni `workflow2` ustiga ko'chiring.

Keyin:
```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

Oching:
`http://127.0.0.1:8000/geoai-lab/`

## v1 imkoniyatlari
- GeoAI Analytics link
- Model Evaluation
- Expert Validation
- GSOR Top-1/Top-3/MRR
- Verified dataset count
- Ablation Study placeholder
- Research Evidence placeholder
- ilmiy pipeline

Keyingi v2:
- GSOR real ablation study
- experiment history
- SHAP explainability
- downloadable research report
