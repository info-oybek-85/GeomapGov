# GeoAI SMART ONLINE — Build 2

## Build 2 tarkibi

- Fazoviy, vaqtli va semantik belgilarni birlashtiruvchi `GeoAI Fusion v2.0` klassifikatori.
- TF-IDF bigramlar + latitude/longitude + siklik vaqt belgilaridan yagona xususiyatlar matritsasi.
- Random Forest klassifikatsiyasi va `Conf_i` ehtimolligi.
- Accuracy, weighted Precision, Recall, F1 va multiclass ROC-AUC.
- Confusion Matrix, sinflar kesimidagi Classification Report.
- ROC egri chiziqlari, qatlamlar ahamiyati va TOP-20 feature importance.
- Xarita marker popupida `rho_i`, `f_i`, `q_i`, `W(C_i)`, `Conf_i`, `n_i`, `P_i` ko‘rsatkichlari.
- Kichik belgilangan dataset bo‘lsa, ilmiy ehtiyotkorlik ogohlantirishi.

## Ishga tushirish

PowerShell:

```powershell
.\env\Scripts\Activate.ps1
python ml\train_geoai_fusion.py
python manage.py analyze_geoai --radius 0.5 --days 30
python manage.py runserver
```

Brauzer:

```text
http://127.0.0.1:8000/geoai/
```

## Muhim ilmiy izoh

Joriy `ml/dataset.csv` 50 ta belgilangan yozuvdan iborat. Metrikalar dasturiy modulni tekshirish uchun chiqariladi. Dissertatsiya va maqoladagi yakuniy xulosalar kattaroq mustaqil test to‘plami yoki stratified k-fold cross-validation bilan tasdiqlanishi kerak.
