import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..api import ApiClient, ApiError, now_iso
from ..db import BotDB
from ..states import StaffLogin
from ..keyboards import menu_kb, staff_menu_kb, staff_tasks_kb, staff_task_kb

router = Router()


async def show_staff_home(target, db: BotDB, telegram_id: int, api: ApiClient | None = None):
    staff = await db.get_staff_session(telegram_id)
    if not staff:
        text = "🔐 Xodim kabinetiga kirish uchun tizimdagi loginingizni yuboring:"
        if isinstance(target, Message):
            await target.answer(text)
        else:
            await target.message.answer(text)
        return False
    text = (
        f"👷 <b>Xodim kabineti</b>\n"
        f"Xodim: {staff['full_name']}\n"
        f"Tashkilot: {staff['organization_name']}\n\n"
        "Kerakli davrni tanlang:"
    )
    map_url = ""
    if api:
        async with aiohttp.ClientSession() as session:
            try:
                map_url = (await api.staff_map_link(session, staff["access_token"])).get("url", "")
            except ApiError:
                pass
    if isinstance(target, Message):
        await target.answer(text, reply_markup=staff_menu_kb(map_url), parse_mode="HTML")
    else:
        await target.message.answer(text, reply_markup=staff_menu_kb(map_url), parse_mode="HTML")
    return True


@router.message(F.text == "👷 Xodim kabineti")
async def staff_entry(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    await state.clear()
    if not await show_staff_home(message, db, message.from_user.id, api):
        await state.set_state(StaffLogin.waiting_username)


@router.callback_query(F.data == "staff:home")
async def staff_home_cb(callback: CallbackQuery, db: BotDB, api: ApiClient):
    await callback.answer()
    await show_staff_home(callback, db, callback.from_user.id, api)


@router.callback_query(F.data.startswith("staff:task:"))
async def staff_task_callback(callback: CallbackQuery, state: FSMContext, db: BotDB, api: ApiClient):
    await callback.answer()
    report_id = callback.data.split(":", 2)[2]
    staff = await db.get_staff_session(callback.from_user.id)
    if not staff:
        await state.update_data(pending_staff_report_id=report_id)
        await state.set_state(StaffLogin.waiting_username)
        await callback.message.answer("🔐 Vazifani ochish uchun tizimdagi loginingizni yuboring:")
        return
    await send_task_detail(callback.message, staff, report_id, api)


@router.message(StaffLogin.waiting_username, F.text)
async def staff_username(message: Message, state: FSMContext):
    await state.update_data(staff_username=message.text.strip())
    await state.set_state(StaffLogin.waiting_password)
    await message.answer("🔑 Parolingizni yuboring:\n\n⚠️ Xavfsizlik uchun xabar login tugagach o‘chiriladi.")


@router.message(StaffLogin.waiting_password, F.text)
async def staff_password(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    data = await state.get_data()
    username = data.get("staff_username", "")
    password = message.text
    try:
        await message.delete()
    except Exception:
        pass
    async with aiohttp.ClientSession() as session:
        try:
            result = await api.staff_login(session, message.from_user.id, username, password)
        except ApiError as exc:
            await state.set_state(StaffLogin.waiting_username)
            await message.answer(f"❌ {exc}\n\nLoginni qayta kiriting:")
            return
    await db.upsert_staff_session(
        telegram_id=message.from_user.id,
        username=result["user"]["username"],
        full_name=result["user"]["full_name"],
        organization_name=result["organization"]["name"],
        access_token=result["tokens"]["access"],
        refresh_token=result["tokens"]["refresh"],
        updated_at_iso=now_iso(),
    )
    pending = data.get("pending_staff_report_id")
    await state.clear()
    await message.answer("✅ Xodim kabinetiga muvaffaqiyatli kirdingiz.", reply_markup=menu_kb())
    staff = await db.get_staff_session(message.from_user.id)
    if pending:
        await send_task_detail(message, staff, pending, api)
    else:
        await show_staff_home(message, db, message.from_user.id, api)


@router.callback_query(F.data.startswith("staff:list:"))
async def staff_list(callback: CallbackQuery, db: BotDB, api: ApiClient):
    await callback.answer()
    parts = callback.data.split(":")
    period = parts[2] if len(parts) > 2 else "all"
    task_status = parts[3] if len(parts) > 3 else "all"
    staff = await db.get_staff_session(callback.from_user.id)
    if not staff:
        await callback.message.answer("Sessiya topilmadi. 👷 Xodim kabineti orqali qayta kiring.")
        return
    async with aiohttp.ClientSession() as session:
        try:
            data = await api.staff_tasks(session, staff["access_token"], period, task_status)
        except ApiError as exc:
            await callback.message.answer(f"❌ {exc}")
            return
    names = {"all": "Jami", "day": "Bugungi", "week": "Haftalik", "month": "Oylik", "year": "Yillik"}
    status_names = {"all":"barcha", "in_progress":"jarayondagi", "resolved":"hal qilingan", "overdue":"muddati o‘tgan"}
    text = f"📋 <b>{names.get(period, period)} — {status_names.get(task_status, task_status)} vazifalar</b>\nTopildi: {data['count']} ta"
    if not data["results"]:
        text += "\n\nBu davrda sizga biriktirilgan vazifa yo‘q."
    await callback.message.answer(text, reply_markup=staff_tasks_kb(data["results"], period), parse_mode="HTML")


async def send_task_detail(message: Message, staff: dict, report_id: str, api: ApiClient):
    async with aiohttp.ClientSession() as session:
        try:
            r = await api.staff_task_detail(session, staff["access_token"], report_id)
        except ApiError as exc:
            await message.answer(f"❌ Vazifani ochib bo‘lmadi: {exc}")
            return
    deadline = r.get("deadline_at") or "Belgilanmagan"
    # API ISO format qaytarsa, xodim uchun o‘qilishi qulay ko‘rinishga keltiramiz.
    if deadline != "Belgilanmagan":
        try:
            from datetime import datetime
            parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            deadline = parsed.astimezone().strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError):
            pass

    citizen_name = r.get("citizen_name") or "Ko‘rsatilmagan"
    citizen_phone = r.get("citizen_phone") or "Ko‘rsatilmagan"
    text = (
        f"🧾 <b>{r.get('title') or 'Murojaat'}</b>\n\n"
        f"📌 Holat: {r['status_label']}\n"
        f"👤 Kimdan: {citizen_name}\n"
        f"📞 Telefoni: {citizen_phone}\n"
        f"🏢 Tashkilot: {r['organization']}\n"
        f"⏰ Muddat: {deadline}\n\n"
        f"📝 {r['description']}"
    )
    await message.answer(
        text,
        reply_markup=staff_task_kb(
            report_id,
            r.get("latitude"),
            r.get("longitude"),
            status=r.get("status", ""),
            phone=r.get("citizen_phone", ""),
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "staff:logout")
async def staff_logout(callback: CallbackQuery, db: BotDB):
    await db.delete_staff_session(callback.from_user.id)
    await callback.answer("Xodim sessiyasi yakunlandi")
    await callback.message.answer("🚪 Xodim kabinetidan chiqdingiz.", reply_markup=menu_kb())

from ..states import StaffWork
from ..keyboards import staff_evidence_kb


@router.callback_query(F.data.startswith("staff:start:"))
async def staff_start_task(callback: CallbackQuery, db: BotDB, api: ApiClient):
    await callback.answer()
    report_id = callback.data.split(":", 2)[2]
    staff = await db.get_staff_session(callback.from_user.id)
    if not staff:
        await callback.message.answer("Sessiya topilmadi. Xodim kabinetiga qayta kiring.")
        return
    async with aiohttp.ClientSession() as session:
        try:
            await api.staff_start_task(session, staff["access_token"], report_id)
        except ApiError as exc:
            await callback.message.answer(f"❌ {exc}")
            return
    await callback.message.answer("▶️ Ish boshlandi. Fuqaroga ham xabar yuborildi.")
    await send_task_detail(callback.message, staff, report_id, api)


@router.callback_query(F.data.startswith("staff:complete:"))
async def staff_complete_begin(callback: CallbackQuery, state: FSMContext, db: BotDB):
    await callback.answer()
    report_id = callback.data.split(":", 2)[2]
    if not await db.get_staff_session(callback.from_user.id):
        await callback.message.answer("Sessiya topilmadi. Xodim kabinetiga qayta kiring.")
        return
    await state.clear()
    await state.update_data(staff_complete_report_id=report_id, staff_evidence=[])
    await state.set_state(StaffWork.collecting_evidence)
    await callback.message.answer(
        "📷 Bajarilgan ishni tasdiqlovchi foto yoki fayllarni yuboring.\n"
        "Kamida bitta dalil majburiy. Tugatgach “✅ Dalillar tayyor”ni bosing.",
        reply_markup=staff_evidence_kb(),
    )


async def _save_staff_file(message: Message, state: FSMContext, file_id: str, filename: str, content_type: str):
    data = await state.get_data()
    items = data.get("staff_evidence", [])
    if len(items) >= 10:
        await message.answer("Maksimal 10 ta dalil yuborish mumkin.")
        return
    file = await message.bot.get_file(file_id)
    buffer = await message.bot.download_file(file.file_path)
    items.append({"filename": filename, "content": buffer.read(), "content_type": content_type})
    await state.update_data(staff_evidence=items)
    await message.answer(f"✅ Dalil qo‘shildi: {len(items)} ta.", reply_markup=staff_evidence_kb())


@router.message(StaffWork.collecting_evidence, F.photo)
async def staff_evidence_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await _save_staff_file(message, state, photo.file_id, f"evidence_{message.message_id}.jpg", "image/jpeg")


@router.message(StaffWork.collecting_evidence, F.document)
async def staff_evidence_document(message: Message, state: FSMContext):
    doc = message.document
    await _save_staff_file(message, state, doc.file_id, doc.file_name or f"evidence_{message.message_id}", doc.mime_type or "application/octet-stream")


@router.message(StaffWork.collecting_evidence, F.text == "✅ Dalillar tayyor")
async def staff_evidence_done(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("staff_evidence"):
        await message.answer("❌ Kamida bitta foto yoki fayl yuboring.", reply_markup=staff_evidence_kb())
        return
    await state.set_state(StaffWork.waiting_note)
    await message.answer("📝 Bajarilgan ish haqida kamida 10 belgidan iborat izoh yozing:")


@router.message(StaffWork.collecting_evidence, F.text == "❌ Bekor qilish")
@router.message(StaffWork.waiting_note, F.text == "❌ Bekor qilish")
async def staff_complete_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=menu_kb())


@router.message(StaffWork.waiting_note, F.text)
async def staff_complete_submit(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    note = message.text.strip()
    if len(note) < 10:
        await message.answer("Izoh kamida 10 ta belgidan iborat bo‘lsin.")
        return
    data = await state.get_data()
    report_id = data.get("staff_complete_report_id")
    evidence = data.get("staff_evidence", [])
    staff = await db.get_staff_session(message.from_user.id)
    if not staff:
        await state.clear()
        await message.answer("Sessiya topilmadi. Qayta kiring.", reply_markup=menu_kb())
        return
    files = [(x["filename"], x["content"], x["content_type"]) for x in evidence]
    async with aiohttp.ClientSession() as session:
        try:
            await api.staff_complete_task(session, staff["access_token"], report_id, note, files)
        except ApiError as exc:
            await message.answer(f"❌ {exc}")
            return
    await state.clear()
    await message.answer("✅ Ish bajarildi va fuqaro tasdig‘iga yuborildi.", reply_markup=menu_kb())
    await send_task_detail(message, staff, report_id, api)
