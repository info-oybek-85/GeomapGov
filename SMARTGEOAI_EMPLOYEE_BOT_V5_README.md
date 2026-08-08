# SmartGeoAI Employee Telegram Cabinet V5

## Yangi imkoniyatlar
- Telegram menyusida `👷 Xodim kabineti`.
- Xodim tizim login/paroli bilan bir marta autentifikatsiya qilinadi.
- Fuqaro Telegram profili va xodim Telegram profili alohida bog'lanadi.
- Jami, bugungi, haftalik va oylik vazifalar filtri.
- Vazifa tafsiloti va Google Maps tugmasi.
- Xodimga murojaat biriktirilganda tugmali Telegram push-xabar.
- Xodim sessiyasidan chiqish.
- Tashkilot a'zosi o'zi yuborgan murojaatni fuqaro sifatida tasdiqlashiga to'sqinlik qilgan `user_type` cheklovi olib tashlandi. Egalik `report.user == request.user` orqali tekshiriladi.

## O'rnatish
```powershell
cd workflow2
.\env\Scripts\Activate.ps1
python manage.py migrate organizations
python manage.py check
python manage.py runserver
```

Botni boshqa terminalda qayta ishga tushiring:
```powershell
cd workflow2\bot
..\env\Scripts\python.exe main.py
```

## Birinchi ulanish
Xodim botda `👷 Xodim kabineti` tugmasini bosadi va tizimdagi login/parolini kiritadi. Shundan keyin Telegram ID xodim profiliga bog'lanadi va yangi biriktirishlar bo'yicha push-xabarlar keladi.
