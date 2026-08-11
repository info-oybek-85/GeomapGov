# SmartGeoAI — GSOR v1

Geo Semantic Organization Routing (GSOR) ning alohida ilmiy baseline moduli.

## Asosiy vazifalar
- matnni normalizatsiya qilish;
- muammo signallarini ajratish;
- tashkilotlarni `Score = ws*S + wc*C + wg*G + wh*H` bo'yicha rank qilish;
- Top-1 / Top-3 natijalarni berish;
- `auto_recommend`, `expert_review`, `citizen_clarification` qarorini chiqarish;
- Top-1 Accuracy, Top-3 Accuracy va MRR ni hisoblash.

## O'rnatish
Patchdagi fayllarni master `workflow2` loyihasiga papka tuzilmasini saqlab ko'chiring.
Migratsiya kerak emas.

## Sinov
```powershell
.\venv\Scripts\python.exe manage.py evaluate_gsor_dataset data\gsor\gsor_dataset_template.csv
```

Verified dataset bilan:
```powershell
.\venv\Scripts\python.exe manage.py evaluate_gsor_dataset data\problem_datasets\verified_routing_dataset.csv
```

Natijalar:
- `data/gsor/gsor_evaluation.json`
- `data/gsor/gsor_predictions.csv`

Muhim: v1 — lexical/semantic baseline. Geo va Historical komponentlar uchun hooklar mavjud, real scorerlar keyingi bosqichda ulanadi.
