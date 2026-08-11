# SmartGeoAI v1.0 FINAL — Manual E2E Test

## Maqsad
Production deploydan keyin bitta real murojaatni boshidan oxirigacha tekshirish.

## Test ID
E2E-FINAL-001

## 1. Public Portal
[ ] `https://fastappeal.uz/` ochiladi
[ ] Portal dizayni to'g'ri
[ ] Telegram tugmasi botni ochadi
[ ] Login modal ochiladi
[ ] Public map ochiladi
[ ] Public analytics ochiladi
[ ] Research Transparency ochiladi

## 2. Citizen Bot
[ ] Fuqaro botga `/start` yuboradi
[ ] Murojaat yuborish menyusi ishlaydi
[ ] Matn yuboriladi
[ ] Lokatsiya yuboriladi
[ ] "Bilmayman" orqali AI routing sinov qilinadi
[ ] Tizim tashkilotni tavsiya qiladi
[ ] Murojaat DBga yoziladi

Test matni:
`Mahallamizda ikki kundan beri elektr yo'q.`

## 3. Dispatcher
[ ] Dispatcher login qiladi
[ ] Yangi murojaat ko'rinadi
[ ] Murojaat qabul qilinadi
[ ] Xodimga biriktiriladi
[ ] Worker botga notification keladi

## 4. Worker
[ ] Worker login qiladi
[ ] Vazifa ko'rinadi
[ ] Fuqaro telefoni kerakli joyda ko'rinadi
[ ] Lokatsiya/xarita ochiladi
[ ] "Ishni boshlash" ishlaydi
[ ] "Ish bajarildi / tasdiqlashga yuborish" ishlaydi

## 5. Citizen confirmation
[ ] Fuqaroga tasdiqlash xabari keladi
[ ] "Tasdiqlayman" bosiladi
[ ] Report yakuniy `resolved` bo'ladi

## 6. Dashboard
[ ] Superadmin dashboardda murojaat resolved ko'rinadi
[ ] Tashkilot statistikasi yangilanadi
[ ] SLA / vaqt ko'rsatkichlari buzilmaydi

## 7. Public layer
[ ] Public mapda anonim resolved marker ko'rinadi
[ ] FIO public ko'rinmaydi
[ ] Telefon public ko'rinmaydi
[ ] Telegram ID public ko'rinmaydi
[ ] Ichki report ID public ko'rinmaydi

## 8. Final result

Agar barcha kritik bandlar PASS bo'lsa:

`E2E STATUS: PASSED`

Shundan keyin:

`SmartGeoAI v1.0 FINAL`
