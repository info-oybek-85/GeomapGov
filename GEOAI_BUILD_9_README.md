# GeoAI SMART-ONLINE Build 9

Build 9 adds two production-oriented modules:

1. **Model retraining**
   - Admin-only POST action.
   - Runs `ml/train_geoai_fusion.py` using the active Python environment.
   - Updates model, metrics, confusion matrix data, ROC data and feature importance.
   - Stores the latest old/new metric comparison in `ml/geoai_model_history.json`.
   - Prevents concurrent retraining with a lock file.

2. **PDF reports**
   - Model results: `/geoai/reports/model.pdf`
   - System results: `/geoai/reports/system.pdf`
   - The system report respects current category, priority, risk and date filters.

## Run

```powershell
py -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py analyze_geoai --radius 0.5 --days 30
python manage.py analyze_risk --eps 35 --min-samples 3 --bandwidth 45
python manage.py runserver
```

Open `http://127.0.0.1:8000/geoai/` as a superadministrator.

## Important scientific note

Retraining uses `ml/dataset.csv`, which must contain labelled examples. New unlabelled complaints do not automatically become training samples until an expert assigns verified categories and they are added to the labelled dataset.
