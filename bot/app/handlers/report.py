import os
import html
import json
import time
import asyncio
import aiohttp
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from ..states import ReportCreate
from ..keyboards import menu_kb, cancel_kb, media_kb, location_kb, confirm_kb
from ..keyboards import organizations_kb, OrgCb
from ..keyboards import (
    problem_categories_kb,
    problems_in_category_kb,
    ProbCatCb,
    ProbCb,
)
from ..problem_catalog import get_category
from ..db import BotDB
from ..api import ApiClient, ApiError, now_iso
from ..utils import guess_content_type, safe_filename
from .my_reports import maps_url

router = Router()

MAX_FILES = 10

ORG_PAGE_SIZE = 5
BILMAYMAN_NAME = "bilmayman"

# ✅ Siz xohlagandek 50MB
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# ✅ Redis yo‘q bo‘lsa ham “auto clear” qilish uchun (ixtiyoriy)
FLOW_TTL_SECONDS = int(os.getenv("REPORT_FLOW_TTL_SECONDS", "3600"))  # default 1 soat

# har user uchun expiry task saqlaymiz (MemoryStorage + 1 process bo‘lsa yetarli)
_EXPIRY_TASKS: dict[tuple[int, int], asyncio.Task] = {}


def _init_media_state():
    # files: [{file_id, filename, content_type, size}]
    return {"files": []}


def _fmt_mb(n: int | None) -> str:
    if not isinstance(n, int):
        return "-"
    return f"{n / (1024 * 1024):.1f}MB"


def _append_file(state_files: list, file_id: str, filename: str, content_type: str, size: int | None):
    state_files.append({"file_id": file_id, "filename": filename, "content_type": content_type, "size": size})


def _too_big(size: int | None) -> bool:
    return isinstance(size, int) and size > MAX_FILE_SIZE


def _task_key(message: Message) -> tuple[int, int]:
    return (message.chat.id, message.from_user.id)


async def _expire_after(bot, chat_id: int, user_id: int, state: FSMContext, expires_at: float):
    # expires_at kelganda state hanuz shu flow bo‘lsa tozalaymiz
    delay = max(0.0, expires_at - time.time())
    await asyncio.sleep(delay)

    try:
        data = await state.get_data()
        cur_expires = data.get("expires_at")
        cur_user = data.get("telegram_id")
        # faqat shu user flow’iga tegishli bo‘lsa
        if cur_user == user_id and isinstance(cur_expires, (int, float)) and cur_expires == expires_at:
            await state.clear()
            await bot.send_message(
                chat_id,
                "⏳ Murojaatni yuborish vaqti tugadi. Iltimos qaytadan boshlang.",
                reply_markup=menu_kb()
            )
    except Exception:
        # bot restart / state yo‘q / network xatolari — jim
        pass


async def _touch_ttl(message: Message, state: FSMContext, user_id: int | None = None):
    # TTL yangilash (Redis yo‘q bo‘lsa ham)
    # callback ichidan chaqirilganda message.from_user = bot bo'ladi,
    # shuning uchun user_id ni override qilish mumkin (call.from_user.id).
    uid = user_id if user_id is not None else message.from_user.id
    expires_at = time.time() + FLOW_TTL_SECONDS
    await state.update_data(expires_at=expires_at, telegram_id=uid)

    key = (message.chat.id, uid)
    old = _EXPIRY_TASKS.get(key)
    if old and not old.done():
        old.cancel()

    _EXPIRY_TASKS[key] = asyncio.create_task(
        _expire_after(message.bot, message.chat.id, uid, state, expires_at)
    )


async def _ensure_not_expired(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    expires_at = data.get("expires_at")
    if isinstance(expires_at, (int, float)) and time.time() > expires_at:
        await state.clear()
        await message.answer(
            "⏳ Murojaat jarayoni eskirib ketdi. Qaytadan boshlang.",
            reply_markup=menu_kb()
        )
        return False
    return True


async def _refresh_tokens(db: BotDB, api: ApiClient, telegram_id: int, user: dict) -> str:
    async with aiohttp.ClientSession() as session2:
        auth = await api.auth_telegram(
            session=session2,
            telegram_id=telegram_id,
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone_number=user["phone_number"],
        )
    access = auth["tokens"]["access"]
    refresh = auth["tokens"]["refresh"]
    await db.upsert_user_tokens(
        telegram_id=telegram_id,
        first_name=user["first_name"],
        last_name=user["last_name"],
        phone_number=user["phone_number"],
        access_token=access,
        refresh_token=refresh,
        updated_at_iso=now_iso(),
    )
    return access


async def _fetch_all_orgs(db: BotDB, api: ApiClient, telegram_id: int, user: dict) -> list[dict]:
    """Barcha tashkilotlarni sahifama-sahifa yig'ib qaytaradi."""
    all_items: list[dict] = []
    page = 1

    async def fetch_page(access_token: str, p: int):
        async with aiohttp.ClientSession() as session:
            return await api.list_organizations(
                session=session, access_token=access_token, page=p, page_size=50,
            )

    access = user["access_token"]
    while True:
        try:
            data = await fetch_page(access, page)
        except ApiError as e:
            if str(e) == "UNAUTHORIZED":
                access = await _refresh_tokens(db, api, telegram_id, user)
                data = await fetch_page(access, page)
            else:
                raise

        results = data.get("results") or data.get("items") or data.get("data") or []
        for o in results:
            all_items.append({
                "id": o.get("id"),
                "name": o.get("name") or o.get("title") or str(o.get("id")),
            })

        if not data.get("next"):
            break
        page += 1
        if page > 100:  # xavfsizlik
            break

    return all_items


async def _load_org_page(
    message: Message,
    state: FSMContext,
    db: BotDB,
    api: ApiClient,
    page: int,
    telegram_id: int,
    edit_from: Message | None = None,
):
    data = await state.get_data()
    all_orgs = data.get("all_orgs")
    bilmayman_id = data.get("bilmayman_org_id")

    if all_orgs is None:
        user = await db.get_user(telegram_id)
        if not user:
            await state.clear()
            await message.answer("Avval /start qilib ro‘yxatdan o‘ting.", reply_markup=menu_kb())
            return

        try:
            items = await _fetch_all_orgs(db, api, telegram_id, user)
        except ApiError as e:
            await message.answer(f"❌ Tashkilotlar yuklanmadi: {e}", reply_markup=menu_kb())
            await state.clear()
            return

        # "Bilmayman" tashkilotini ajratib olamiz
        bilmayman_id = None
        filtered: list[dict] = []
        for o in items:
            if (o["name"] or "").strip().lower() == BILMAYMAN_NAME:
                bilmayman_id = o["id"]
                continue
            filtered.append(o)

        all_orgs = filtered
        await state.update_data(all_orgs=all_orgs, bilmayman_org_id=bilmayman_id)

    total = len(all_orgs)
    total_pages = max(1, (total + ORG_PAGE_SIZE - 1) // ORG_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ORG_PAGE_SIZE
    page_orgs = all_orgs[start:start + ORG_PAGE_SIZE]
    has_prev = page > 1
    has_next = page < total_pages

    await state.update_data(org_page=page)

    text = "🏢 Muammo qaysi tashkilotga tegishli? Tanlang:"
    kb = organizations_kb(
        orgs=page_orgs,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        bilmayman_id=bilmayman_id,
    )

    if edit_from:
        try:
            await edit_from.edit_text(text, reply_markup=kb)
        except Exception:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.message(F.text.startswith("Murojaat yuborish"))
async def report_start(message: Message, state: FSMContext, db: BotDB):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.")
        return

    await state.clear()
    await state.set_state(ReportCreate.waiting_description)
    await state.update_data(media=_init_media_state())
    await _touch_ttl(message, state)

    # Reply keyboard — bekor qilish
    await message.answer(
        "📝 <b>Muammoni yozing yoki tanlang</b>\n\n"
        "Muammoni matn ko‘rinishida yozib yuboring, "
        "yoki quyidagi tayyor ro‘yxatdan tanlang:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    # Inline keyboard — kategoriyalar
    await message.answer(
        "Muammo kategoriyasini tanlang:",
        reply_markup=problem_categories_kb(page=1),
    )


@router.message(ReportCreate.waiting_description, F.text == "❌ Bekor qilish")
async def cancel_from_description(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


async def _proceed_to_media(message: Message, state: FSMContext, description: str):
    """Description saqlanadi va media yig'ish bosqichiga o'tadi."""
    await state.update_data(description=description)
    await state.set_state(ReportCreate.collecting_media)
    await message.answer(
        f"✅ Muammo tanlandi:\n<i>{html.escape(description)}</i>\n\n"
        "Endi xohlasangiz rasm/video/ovoz/audio/pdf/file yuboring.\n"
        "Tayyor bo‘lsangiz: ✅ Joylashuv yuborish ni bosing.",
        reply_markup=media_kb(),
        parse_mode="HTML",
    )


@router.callback_query(ReportCreate.waiting_description, ProbCatCb.filter())
async def problem_category_callback(call: CallbackQuery, callback_data: ProbCatCb, state: FSMContext):
    if not await _ensure_not_expired(call.message, state):
        await call.answer()
        return
    await _touch_ttl(call.message, state, user_id=call.from_user.id)

    if callback_data.action == "page":
        try:
            await call.message.edit_reply_markup(
                reply_markup=problem_categories_kb(page=callback_data.page)
            )
        except Exception:
            pass
        await call.answer()
        return

    if callback_data.action == "pick":
        cat = get_category(callback_data.key)
        if not cat:
            await call.answer("Kategoriya topilmadi", show_alert=True)
            return
        try:
            await call.message.edit_text(
                f"<b>{html.escape(cat['title'])}</b>\nMuammoni tanlang:",
                reply_markup=problems_in_category_kb(cat["key"], page=1),
                parse_mode="HTML",
            )
        except Exception:
            await call.message.answer(
                f"<b>{html.escape(cat['title'])}</b>\nMuammoni tanlang:",
                reply_markup=problems_in_category_kb(cat["key"], page=1),
                parse_mode="HTML",
            )
        await call.answer()
        return

    await call.answer()


@router.callback_query(ReportCreate.waiting_description, ProbCb.filter())
async def problem_pick_callback(call: CallbackQuery, callback_data: ProbCb, state: FSMContext):
    if not await _ensure_not_expired(call.message, state):
        await call.answer()
        return
    await _touch_ttl(call.message, state, user_id=call.from_user.id)

    if callback_data.action == "back":
        try:
            await call.message.edit_text(
                "Muammo kategoriyasini tanlang:",
                reply_markup=problem_categories_kb(page=1),
            )
        except Exception:
            await call.message.answer(
                "Muammo kategoriyasini tanlang:",
                reply_markup=problem_categories_kb(page=1),
            )
        await call.answer()
        return

    if callback_data.action == "page":
        try:
            await call.message.edit_reply_markup(
                reply_markup=problems_in_category_kb(callback_data.key, page=callback_data.page)
            )
        except Exception:
            pass
        await call.answer()
        return

    if callback_data.action == "pick":
        cat = get_category(callback_data.key)
        if not cat or callback_data.idx < 0 or callback_data.idx >= len(cat["problems"]):
            await call.answer("Muammo topilmadi", show_alert=True)
            return
        problem_text = cat["problems"][callback_data.idx]
        await call.answer("✅ Tanlandi")
        try:
            await call.message.delete()
        except Exception:
            pass
        await _proceed_to_media(call.message, state, problem_text)
        return

    await call.answer()


@router.message(ReportCreate.waiting_description, F.text)
async def report_got_description(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("Matn juda qisqa. Iltimos muammoni batafsilroq yozing.", reply_markup=cancel_kb())
        return

    await _proceed_to_media(message, state, text)


@router.message(ReportCreate.collecting_media, F.text == "❌ Bekor qilish")
async def report_cancel_media(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


@router.message(ReportCreate.collecting_media, F.text == "✅ Joylashuv yuborish")
async def report_ask_location(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    await state.set_state(ReportCreate.waiting_location)
    await message.answer(
        "🗺 Xaritadan muammo joylashuvini tanlang.\n"
        "Tugmani bosing va xaritadan kerakli nuqtani belgilang.",
        reply_markup=location_kb(),
    )


async def _reject_big(message: Message, size: int | None):
    await message.answer(
        f"❌ Fayl qabul qilinmadi.\n"
        f"Maksimal: {MAX_FILE_SIZE_MB}MB\n"
        f"Siz yuborgan: {_fmt_mb(size)}\n\n"
        f"Iltimos kichikroq fayl yuboring.",
        reply_markup=media_kb()
    )


@router.message(ReportCreate.collecting_media, F.photo)
async def report_collect_photo(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    photo = message.photo[-1]
    size = getattr(photo, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    _append_file(files, photo.file_id, safe_filename(f"photo_{len(files)+1}.jpg"), "image/jpeg", size)
    await state.update_data(media=media)
    await message.answer(f"✅ Rasm qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.video)
async def report_collect_video(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    v = message.video
    size = getattr(v, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    filename = safe_filename(v.file_name or f"video_{len(files)+1}.mp4")
    _append_file(files, v.file_id, filename, v.mime_type or "video/mp4", size)
    await state.update_data(media=media)
    await message.answer(f"✅ Video qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.voice)
async def report_collect_voice(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    v = message.voice
    size = getattr(v, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    _append_file(files, v.file_id, safe_filename(f"voice_{len(files)+1}.ogg"), v.mime_type or "audio/ogg", size)
    await state.update_data(media=media)
    await message.answer(f"✅ Ovozli xabar qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.audio)
async def report_collect_audio(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    a = message.audio
    size = getattr(a, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    filename = safe_filename(a.file_name or f"audio_{len(files)+1}.mp3")
    _append_file(files, a.file_id, filename, a.mime_type or guess_content_type(filename), size)
    await state.update_data(media=media)
    await message.answer(f"✅ Audio qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.document)
async def report_collect_document(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    d = message.document
    size = getattr(d, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    filename = safe_filename(d.file_name or f"file_{len(files)+1}")
    _append_file(files, d.file_id, filename, d.mime_type or guess_content_type(filename), size)
    await state.update_data(media=media)
    await message.answer(f"✅ Fayl qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.waiting_location, F.text == "❌ Bekor qilish")
async def report_cancel_location(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


async def _accept_location(message: Message, state: FSMContext, db: BotDB, api: ApiClient, lat: float, lon: float):
    await state.update_data(latitude=lat, longitude=lon)
    link = maps_url(lat, lon)
    await state.set_state(ReportCreate.waiting_organization)
    await message.answer(
        f"📍 Joylashuv qabul qilindi: {link}\n\nEndi tashkilotni tanlang:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await _load_org_page(message, state, db, api, page=1, telegram_id=message.from_user.id)


@router.message(ReportCreate.waiting_location, F.web_app_data)
async def report_location_from_webapp(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    try:
        payload = json.loads(message.web_app_data.data)
        lat = float(payload["lat"])
        lon = float(payload["lon"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        await message.answer(
            "❌ Xaritadan qabul qilingan ma'lumot noto‘g‘ri. Qayta urinib ko‘ring.",
            reply_markup=location_kb(),
        )
        return

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        await message.answer(
            "❌ Koordinatalar noto‘g‘ri. Qayta urinib ko‘ring.",
            reply_markup=location_kb(),
        )
        return

    await _accept_location(message, state, db, api, lat, lon)


@router.message(ReportCreate.waiting_location, F.location)
async def report_after_location_ask_org(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    await _accept_location(message, state, db, api, lat, lon)


@router.callback_query(ReportCreate.waiting_organization, OrgCb.filter())
async def org_pick_or_page(call: CallbackQuery, callback_data: OrgCb, state: FSMContext, db: BotDB, api: ApiClient):
    # MUHIM: callback ichida call.message.from_user = bot bo'ladi.
    # Haqiqiy foydalanuvchi id sini call.from_user dan olamiz.
    msg = call.message
    telegram_id = call.from_user.id

    if not await _ensure_not_expired(msg, state):
        await call.answer()
        return
    await _touch_ttl(msg, state, user_id=telegram_id)

    action = callback_data.action
    page = int(callback_data.page or 1)

    if action == "cancel":
        await state.clear()
        await msg.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())
        await call.answer()
        return

    if action == "page":
        await call.answer()
        await _load_org_page(msg, state, db, api, page=page, telegram_id=telegram_id, edit_from=msg)
        return

    if action == "pick":
        org_id = callback_data.org_id
        if not org_id:
            await call.answer("Xatolik: org_id yo‘q", show_alert=True)
            return

        await state.update_data(organization_id=org_id)
        await call.answer("✅ Tashkilot tanlandi")

        data = await state.get_data()
        files = (data.get("media") or _init_media_state())["files"]
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
        link = maps_url(lat, lon)

        # Tanlangan tashkilot nomini state cache dan topamiz
        org_name = None
        if str(data.get("bilmayman_org_id")) == str(org_id):
            org_name = "Bilmayman"
        else:
            for o in (data.get("all_orgs") or []):
                if str(o.get("id")) == str(org_id):
                    org_name = o.get("name")
                    break

        preview_text = (
            "📄 Murojaatni tasdiqlash\n\n"
            f"📝 Matn:\n{data.get('description','')}\n\n"
            f"📎 Fayllar soni: {len(files)}\n"
            f"📍 Joylashuv: {link}\n"
            f"🏢 Tashkilot: {org_name or org_id}\n\n"
            "Agar hammasi to‘g‘ri bo‘lsa: ✅ Yuborish\n"
            "Aks holda: ❌ Bekor qilish"
        )

        await state.set_state(ReportCreate.confirm)
        await msg.answer(preview_text, reply_markup=confirm_kb())
        return

    await call.answer()


@router.message(ReportCreate.confirm, F.text == "❌ Bekor qilish")
async def report_cancel_confirm(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi. Saqlanmadi.", reply_markup=menu_kb())


@router.message(ReportCreate.confirm, F.text == "✅ Yuborish")
async def report_submit_confirmed(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await state.clear()
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.")
        return

    data = await state.get_data()
    description = data.get("description", "")
    lat = float(data.get("latitude"))
    lon = float(data.get("longitude"))
    organization_id = data.get("organization_id")

    if not organization_id:
        await state.clear()
        await message.answer("❌ Tashkilot tanlanmagan. Qaytadan urinib ko‘ring.", reply_markup=menu_kb())
        return

    files_meta = (data.get("media") or _init_media_state())["files"]

    # tanlangan tashkilot nomini state cache dan topamiz (chiroyli xabar uchun)
    org_name = None
    if str(data.get("bilmayman_org_id")) == str(organization_id):
        org_name = "Bilmayman"
    else:
        for o in (data.get("all_orgs") or []):
            if str(o.get("id")) == str(organization_id):
                org_name = o.get("name")
                break

    await message.answer("⏳ Yuborilyapti… iltimos biroz kuting.")

    tg_files = []
    for item in files_meta:
        file_id = item["file_id"]
        filename = item["filename"]
        ctype = item["content_type"]
        size = item.get("size")

        # yana bir marta tekshiruv
        if _too_big(size):
            await message.answer(
                f"❌ {filename} qabul qilinmadi. ({_fmt_mb(size)})\nMaks: {MAX_FILE_SIZE_MB}MB",
                reply_markup=menu_kb()
            )
            await state.clear()
            return

        f = await message.bot.get_file(file_id)

        # get_file dan ham file_size chiqishi mumkin — yana tekshiramiz
        f_size = getattr(f, "file_size", None)
        if _too_big(f_size):
            await message.answer(
                f"❌ {filename} juda katta. ({_fmt_mb(f_size)})\nMaks: {MAX_FILE_SIZE_MB}MB",
                reply_markup=menu_kb()
            )
            await state.clear()
            return

        stream = BytesIO()
        await message.bot.download_file(f.file_path, stream)
        tg_files.append((filename, stream.getvalue(), ctype))

    async def submit(access_token: str):
        async with aiohttp.ClientSession() as session:
            return await api.create_report(
                session=session,
                access_token=access_token,
                description=description,
                latitude=lat,
                longitude=lon,
                organization_id=organization_id,
                files=tg_files,
            )

    try:
        created = await submit(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            new_access = await _refresh_tokens(db, api, telegram_id, user)
            created = await submit(new_access)
        else:
            await message.answer(f"❌ Murojaat yuborilmadi: {e}", reply_markup=menu_kb())
            await state.clear()
            return

    await state.clear()

    _STATUS_TITLE = {
        "new": "🟥 Yangi",
        "in_progress": "🟨 Jarayonda",
        "resolved": "🟩 Hal qilindi",
        "rejected": "⬛ Rad etildi",
    }
    rid = str(created.get("id") or "")
    short = rid[:8] if rid else "—"
    status_raw = str(created.get("status") or "new").lower()
    status_pretty = _STATUS_TITLE.get(status_raw, status_raw)

    success_text = (
        "🎉 <b>Murojaatingiz muvaffaqiyatli qabul qilindi!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{short}</code>\n"
        f"📊 Holati: <b>{status_pretty}</b>\n"
        f"📎 Fayllar: <b>{len(files_meta)}</b> ta\n"
        f"🏢 Tashkilot: <b>{html.escape(str(org_name or organization_id))}</b>\n"
        f"📍 Joylashuv: <a href=\"{maps_url(lat, lon)}\">Xaritada ko‘rish</a>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🙏 Murojaatingiz uchun rahmat! Ko‘rib chiqilgach xabar beramiz.\n"
        "Holatini kuzatish uchun <b>«Murojaatlarim»</b> bo‘limiga kiring."
    )
    await message.answer(
        success_text,
        reply_markup=menu_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
