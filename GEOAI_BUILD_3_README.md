# GeoAI SMART ONLINE — Build 3

Build 3 ikkinchi ilmiy yangilikni dasturda vizual va interaktiv ko‘rsatadi:

- GeoPriority formulasi va olti komponent;
- yuqori/o‘rta/past ustuvorlik taqsimoti;
- P_i histogrammasi;
- kategoriya bo‘yicha o‘rtacha P_i;
- vaqt bo‘yicha ustuvorlik dinamikasi;
- komponentlar radar diagrammasi;
- xaritada markerlar va Priority heatmap qatlamlari;
- marker popupida rho_i, f_i, q_i, W(C_i), Conf_i, n_i va P_i;
- CSV eksport.

## Ishga tushirish

```powershell
py -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py analyze_geoai --radius 0.5 --days 30
python manage.py runserver
```

Brauzer: http://127.0.0.1:8000/geoai/

CSV: GeoAI Analytics > Ustuvorlik tahlili > CSV eksport.
