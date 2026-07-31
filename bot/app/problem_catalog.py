# Foydalanuvchi murojaat yozish o'rniga tanlashi mumkin bo'lgan tayyor muammolar ro'yxati.
# Ikki bosqichli menyu: KATEGORIYA -> MUAMMO
# Har bir tugma sahifasida 4 tadan chiqadi (pagination).

PROBLEM_CATALOG: list[dict] = [
    {
        "key": "electricity",
        "title": "⚡ Elektr energiyasi",
        "problems": [
            "Elektr hisoblagichlari bilan bog'liq muammolar",
            "Elektr tarmoq/shchit uskunasining shikastlanishi",
            "Elektr energiya past kuchlanishda",
            "Elektr energiyasi yo'q",
            "Elektr energiya yuqori kuchlanishda",
            "Shaxmat tartibda elektr energiyasining o'chishi (faza yo'q)",
        ],
    },
    {
        "key": "water",
        "title": "💧 Suv masalasi",
        "problems": [
            "Sovuq batareyalar (isitish tizimidagi nosozlik)",
            "Issiq suv haroratining me'yoridan pastligi",
            "Sifatsiz (zangli, loyqa, qumli) sovuq suv",
            "Sovuq suv past bosimda",
            "Issiq suv past bosimda",
            "Issiq suv quvuri yorilgan",
            "Ichimlik suv quvuri yorilgan",
            "Issiq suv yo'q",
            "Sovuq suv yo'q",
            "Sovuq suv o'rniga issiq suv kelayapti",
            "Zangli, loyqa issiq suv",
        ],
    },
    {
        "key": "sidewalk",
        "title": "🚶 Piyodalar yo'lagi (Trotuar)",
        "problems": [
            "Trotuar qoplamasi buzilganligi",
            "Ta'mirtalab asfalt (o'nqir-cho'nqirlar)",
            "Mahalladagi (xususiy sektor) ta'mirtalab asfalt",
            "Ko'p xonadonli uylar atrofidagi ta'mirtalab asfalt",
            "Markaziy ko'chalarda ta'mirtalab asfalt",
            "O'ZAVTOYO'L tizimidagi yo'llarning ta'mirtalabligi",
            "Tumanlararo yo'llardagi asfalt ta'mirtalab",
            "«Yagona Buyurtmachi Xizmati» obektlaridagi shikastlangan asfalt",
        ],
    },
    {
        "key": "road",
        "title": "🛣 Yo'l",
        "problems": [
            "Yo'l qismini suv bosishi",
            "O'chib ketgan yo'l chiziqlari",
            "Nosoz svetofor",
            "Shikastlangan/o'qib bo'lmaydigan yo'l belgilari",
            "Yo'l belgilarini o'rnatishdagi qarama-qarshiliklar",
            "Yo'l qismidagi nosoz yoritish vositalari",
            "Yo'l belgilari bilan bog'liq muammolar",
            "«YBX» obektlarida yo'l harakati xavfsizligi masalalari",
        ],
    },
    {
        "key": "pedestrian",
        "title": "🚸 Piyodalar o'tish joylari",
        "problems": [
            "O'chib ketgan piyodalar yo'l chiziqlari",
            "Yo'l usti va osti piyodalar o'tish joylariga xizmat sifatsizligi",
            "Takomillashtirishni talab qilayotgan piyodalar o'tish joylari",
        ],
    },
    {
        "key": "ecology",
        "title": "🌿 Ekologiya",
        "problems": [
            "Belgilanmagan joylarga axlat (qurilish/maishiy/sanoat) tashlash",
            "Shahar kanallari va havzalarining ifloslanishi",
            "Daraxtlarning noqonuniy kesilishi",
            "Betonlangan daraxt tanasi",
            "Daraxt shohlarining noto'g'ri kesilishi",
            "Ko'chada yoqimsiz hid mavjudligi",
            "Bahor mavsumida ekiladigan joylar mavjudligi",
        ],
    },
    {
        "key": "bus",
        "title": "🚌 Avtobus",
        "problems": [
            "Validator ishlamaydi (nosoz)",
            "Kartadan to'lashdagi muammolar",
            "Haydovchi/konduktor tomonidan qo'pol munosabat",
            "O'tirish uchun joylar shikastlanishi/yo'qligi",
            "Elektron axborot tablosida yo'nalish ma'lumoti yo'qligi",
            "To'lov bilan bog'liq muammolar (kontaktsiz to'lov)",
            "Haydovchi bekatda to'xtamadi",
            "Haydovchilar avtobus salonida chekishi",
            "Harakat paytida telefonda gaplashishi",
            "Oraliq bekatlarda uzoq vaqt turishi",
            "Xavfli boshqaruv (tezlik rejimiga rioya qilmaslik)",
            "Yo'nalish chizmasiga rioya qilmaslik",
        ],
    },
    {
        "key": "bus_stops",
        "title": "🚏 Jamoat transport bekatlari",
        "problems": [
            "Infokiosk ishlamaydi (nosoz)",
            "Jadval/yo'nalishga rioya qilmaslik",
            "Qoniqarsiz texnik/sanitariya holati",
        ],
    },
]


def get_category(key: str) -> dict | None:
    for c in PROBLEM_CATALOG:
        if c["key"] == key:
            return c
    return None
