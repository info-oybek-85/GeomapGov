SmartGeoAI Organization ML Self-learning V3

Faqat ushbu yangi/o'zgargan fayllarni master loyihaga ko'chiring:
- organizations/organization_classifier.py
- organizations/management/__init__.py
- organizations/management/commands/__init__.py
- organizations/management/commands/export_organization_feedback.py
- organizations/management/commands/train_organization_classifier.py

Migratsiya kerak emas.

1) Dataset eksporti:
python manage.py export_organization_feedback

Natija:
data/organization_feedback.csv

2) Modelni o'qitish (kamida 30 ta feedback, kamida 2 sinf):
python manage.py train_organization_classifier

Model:
ml/organization_classifier.pkl
Metadata va metrikalar:
ml/organization_classifier_meta.json

3) Server/botni qayta ishga tushiring.
Yangi model mavjud va TOP-1 confidence >= 45% bo'lsa, tavsiya avval shu modeldan olinadi.
Aks holda oldingi gibrid ML + kalit iboralar mexanizmi ishlashda davom etadi.
