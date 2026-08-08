from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from .config import get_settings


def menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Murojaat yuborish")],
            [KeyboardButton(text="Murojaatlarim")],
            [KeyboardButton(text="Tugallangan murojaatlarim")],
            [KeyboardButton(text="👷 Xodim kabineti")],
            [KeyboardButton(text="Ishlatish bo‘yicha qo‘llanma")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def media_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Joylashuv yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
    )


def location_kb() -> ReplyKeyboardMarkup:
    webapp_url = get_settings().webapp_location_url
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joriy lokatsiya", request_location=True)],
            [KeyboardButton(text="🔎 Manzilni qidirish va tanlash", web_app=WebAppInfo(url=webapp_url))],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ------------ Inline browse keyboards ------------

def reports_nav_kb(
    has_prev: bool,
    has_next: bool,
    can_resolve: bool,
    access_token: str | None = None,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    row1: list[InlineKeyboardButton] = []
    if has_prev:
        row1.append(InlineKeyboardButton(text="⬅️", callback_data="repnav:prev"))
    row1.append(InlineKeyboardButton(text="📎 Fayllar", callback_data="repnav:files"))
    if has_next:
        row1.append(InlineKeyboardButton(text="➡️", callback_data="repnav:next"))
    b.row(*row1)

    if access_token:
        webapp_url = f"{get_settings().webapp_my_reports_map_url}?token={access_token}"
        b.row(InlineKeyboardButton(
            text="🗺 Xaritada ko‘rish",
            web_app=WebAppInfo(url=webapp_url),
        ))

    if can_resolve:
        b.row(InlineKeyboardButton(text="✅ Hal bo‘ldi", callback_data="repnav:resolve"))

    b.row(InlineKeyboardButton(text="🔙 Menyuga", callback_data="repnav:menu"))
    return b.as_markup()


def resolve_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tasdiqlayman", callback_data="represolve:yes")
    b.button(text="❌ Bekor", callback_data="represolve:no")
    b.adjust(2)
    return b.as_markup()


def files_list_kb(attachments_count: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    for i in range(attachments_count):
        b.button(text=f"📎 {i+1}", callback_data=f"repfile:{i}")

    b.adjust(4)

    b.row(
        InlineKeyboardButton(text="📤 Hammasini yuborish", callback_data="repfile:all"),
        InlineKeyboardButton(text="⬅️ Ortga", callback_data="repfile:back"),
    )
    return b.as_markup()




class OrgSuggestionCb(CallbackData, prefix="orgsuggest"):
    action: str  # pick | other | cancel
    org_id: str | None = None


def organization_suggestion_kb(recommendations: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for index, item in enumerate(recommendations[:3], start=1):
        org_id = item.get("id")
        if not org_id:
            continue
        confidence = round(float(item.get("confidence") or 0) * 100)
        name = str(item.get("name") or "Tashkilot")
        b.row(InlineKeyboardButton(
            text=f"{index}. {name} — {confidence}%",
            callback_data=OrgSuggestionCb(action="pick", org_id=str(org_id)).pack(),
        ))
    b.row(InlineKeyboardButton(
        text="🏢 Boshqa tashkilotni tanlash",
        callback_data=OrgSuggestionCb(action="other", org_id=None).pack(),
    ))
    b.row(InlineKeyboardButton(
        text="❌ Bekor qilish",
        callback_data=OrgSuggestionCb(action="cancel", org_id=None).pack(),
    ))
    return b.as_markup()


class OrgCb(CallbackData, prefix="org"):
    action: str          # "pick" | "page" | "cancel"
    page: int            # 1,2,3...
    org_id: str | None = None


def organizations_kb(
    orgs: list[dict],
    page: int,
    has_prev: bool,
    has_next: bool,
    bilmayman_id: str | int | None = None,
) -> InlineKeyboardMarkup:
    """
    orgs: [{"id": "...", "name": "..."}] — sahifadagi tashkilotlar (5 tagacha)
    bilmayman_id: agar berilsa, har sahifada 1-tugma "🤷 Bilmayman" bo'ladi
    """
    kb = InlineKeyboardBuilder()

    if bilmayman_id is not None:
        kb.row(InlineKeyboardButton(
            text="🤷 Bilmayman",
            callback_data=OrgCb(action="pick", page=page, org_id=str(bilmayman_id)).pack(),
        ))

    for org in orgs:
        kb.row(InlineKeyboardButton(
            text=f"🏢 {org['name']}",
            callback_data=OrgCb(action="pick", page=page, org_id=str(org["id"])).pack(),
        ))

    nav_buttons: list[InlineKeyboardButton] = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Oldingi",
            callback_data=OrgCb(action="page", page=page - 1).pack(),
        ))
    if has_next:
        nav_buttons.append(InlineKeyboardButton(
            text="Keyingi ➡️",
            callback_data=OrgCb(action="page", page=page + 1).pack(),
        ))
    if nav_buttons:
        kb.row(*nav_buttons)

    kb.row(InlineKeyboardButton(
        text="❌ Bekor qilish",
        callback_data=OrgCb(action="cancel", page=page).pack(),
    ))

    return kb.as_markup()

def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def staff_menu_kb(map_url: str = "") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 Jami", callback_data="staff:list:all:all")
    b.button(text="📅 Bugungi", callback_data="staff:list:day:all")
    b.button(text="📆 Haftalik", callback_data="staff:list:week:all")
    b.button(text="📈 Oylik", callback_data="staff:list:month:all")
    b.button(text="🗓 Yillik", callback_data="staff:list:year:all")
    b.button(text="🟠 Jarayonda", callback_data="staff:list:all:in_progress")
    b.button(text="✅ Hal qilingan", callback_data="staff:list:all:resolved")
    b.button(text="⏰ Muddati o‘tgan", callback_data="staff:list:all:overdue")
    if map_url:
        b.row(InlineKeyboardButton(text="🗺 Vazifalarim geoxaritasi", url=map_url))
    b.row(InlineKeyboardButton(text="🚪 Xodim kabinetidan chiqish", callback_data="staff:logout"))
    b.adjust(2, 2, 2, 2)
    return b.as_markup()


def staff_tasks_kb(items: list[dict], period: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item in items[:20]:
        title = (item.get("title") or item.get("description") or "Murojaat")[:35]
        b.row(InlineKeyboardButton(
            text=f"{item.get('status_label', '')} · {title}",
            callback_data=f"staff:task:{item['report_id']}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Filtrlarga qaytish", callback_data="staff:home"))
    return b.as_markup()


def staff_task_kb(report_id: str, latitude=None, longitude=None, status: str = "", phone: str = "") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if latitude is not None and longitude is not None:
        b.row(InlineKeyboardButton(text="📍 Xaritada ochish", url=f"https://www.google.com/maps?q={latitude},{longitude}"))
    if phone:
        normalized = phone.replace(" ", "").replace("-", "")
        b.row(InlineKeyboardButton(text=f"☎️ Fuqaroga qo‘ng‘iroq: {phone}", url=f"tel:{normalized}"))
    if status in {"assigned", "reopened"}:
        b.row(InlineKeyboardButton(text="▶️ Ishni boshlash", callback_data=f"staff:start:{report_id}"))
    if status == "in_progress":
        b.row(InlineKeyboardButton(text="✅ Ish bajarildi — tasdiqlashga yuborish", callback_data=f"staff:complete:{report_id}"))
    b.row(InlineKeyboardButton(text="📋 Vazifalarim", callback_data="staff:home"))
    return b.as_markup()


def staff_evidence_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Dalillar tayyor")],
        [KeyboardButton(text="❌ Bekor qilish")],
    ], resize_keyboard=True)
