# GeoAI-SMART ONLINE — Build 1

Ushbu build mavjud GeomapGov loyihasiga GeoAI ilmiy tahlil modulini qo‘shadi.

## Amalga oshirilgan qismlar

- `geoai` Django ilovasi yaratildi.
- 1-ilmiy yangilik uchun avtomatik klassifikatsiya va `Conf_i` hisoblash integratsiyasi qo‘shildi.
- 2-ilmiy yangilikning ishlaydigan GeoPriority yadrosi yaratildi:
  - hududiy zichlik `rho_i`;
  - takrorlanish chastotasi `f_i`;
  - vaqt bo‘yicha dolzarblik `q_i`;
  - muammo og‘irligi `W(C_i)`;
  - klassifikator ishonchliligi `Conf_i`;
  - qo‘shni hududlar ta’siri `n_i`;
  - integral ustuvorlik indeksi `P_i`.
- Natijalarni saqlash uchun `ComplaintAnalysis` modeli yaratildi.
- Interaktiv GeoAI Analytics sahifasi, xarita, dinamik filtr va TOP-20 jadvali qo‘shildi.
- 3- va 4-ilmiy yangiliklar uchun klaster, WKDE va risk maydonlari bazaga tayyorlandi.

## Ishga tushirish

Windows virtual muhitida:

```bat
env\Scripts\activate
python manage.py migrate
python manage.py analyze_geoai --radius 0.5 --days 30
python manage.py runserver
```

So‘ng superadministrator sifatida kiring va menyudan **GeoAI Analytics** bo‘limini oching:

```text
http://127.0.0.1:8000/geoai/
```

## Matematik formula

```text
P_i = 0.22*rho_i + 0.18*f_i + 0.18*q_i + 0.20*W(C_i) + 0.12*Conf_i + 0.10*n_i
```

Vaznlar keyingi buildda tajribaviy validatsiya va optimallashtirish orqali kalibrlanadi.

## Keyingi bosqich

Build 2 da Spatial–Temporal–Semantic Feature Fusion klassifikatori, cross-validation, confusion matrix, ROC-AUC va model taqqoslash moduli to‘liq qo‘shiladi.
