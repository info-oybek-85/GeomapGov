# GeoAI SMART ONLINE — Build 4

## Qo‘shilgan imkoniyatlar

- Priority heatmap uchun min–max vizual normalizatsiya, kuchli gradient, radius va blur sozlamalari.
- DBSCAN klasterlash (`eps`, `MinPts`).
- Ustuvorlik indeksi bilan vaznlangan Gaussian KDE (WKDE).
- Klasterlar bo‘yicha integral xavf indeksi `H_k`.
- Yuqori, o‘rta va past xavf darajalari.
- Xarita uchun DBSCAN + risk zonalari qatlami.
- Xavf tahlili paneli, diagrammalar va klasterlar jadvali.

## Ishga tushirish

```powershell
python manage.py migrate
python manage.py analyze_geoai --radius 0.5 --days 30
python manage.py analyze_risk --eps 35 --min-samples 3 --bandwidth 45
python manage.py runserver
```

Brauzer:

```text
http://127.0.0.1:8000/geoai/
```

## Parametrlarni kalibrlash

Murojaatlar bir shahar doirasida bo‘lsa:

```powershell
python manage.py analyze_risk --eps 2 --min-samples 3 --bandwidth 3
```

Murojaatlar respublika bo‘ylab tarqalgan bo‘lsa:

```powershell
python manage.py analyze_risk --eps 35 --min-samples 3 --bandwidth 45
```

`eps` va `bandwidth` qiymatlari ma’lumotlarning fazoviy masshtabiga qarab tajribada tanlanadi.
