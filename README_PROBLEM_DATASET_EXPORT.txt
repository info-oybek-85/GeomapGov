SMARTGEOAI — REAL MUROJAATLARNI DATASETGA EKSPORT QILISH

1. Patchdagi faylni master loyihaga nusxalang:
   organizations/management/commands/export_problem_datasets.py

2. Ishga tushiring:
   .\venv\Scripts\python.exe manage.py export_problem_datasets

3. Natijalar:
   data/problem_datasets/electricity_real.csv
   data/problem_datasets/ecology_real.csv
   data/problem_datasets/complex_cases_real.csv
   data/problem_datasets/unlabeled_for_expert.csv
   data/problem_datasets/all_real_reports.csv
   data/problem_datasets/dataset_stats.json

Qo‘shimcha buyruqlar:

- Faqat 100 ta yozuv bilan sinov:
  .\venv\Scripts\python.exe manage.py export_problem_datasets --limit 100

- Faqat AI tavsiyasini fuqaro qabul qilgan yozuvlar:
  .\venv\Scripts\python.exe manage.py export_problem_datasets --only-verified

Eslatma:
- Eksport real murojaatlarni o‘zgartirmaydi.
- CSV UTF-8 BOM formatida, Excelda o‘zbek harflari to‘g‘ri ochiladi.
- expert_verified=Yo‘q yozuvlari ekspert tomonidan tekshirilishi kerak.
- Lug‘atlar command faylidagi PROBLEM_RULES bo‘limida kengaytiriladi.
