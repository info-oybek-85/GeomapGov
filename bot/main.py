import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.db import BotDB
from app.api import ApiClient
from app.handlers.init import get_routers

async def main():
    settings = get_settings()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    db = BotDB()
    await db.init()
    await db.staff_init()

    api = ApiClient(settings.api_base_url)

    # dependencies (oddiy usul: dp["db"]=..., handlerda parametr sifatida ishlatamiz)
    dp["db"] = db
    dp["api"] = api

    for r in get_routers():
        dp.include_router(r)

    @dp.errors()
    async def global_error_handler(event: ErrorEvent):
        # Handlerdagi bitta xato polling jarayonini “jim qotib qolgandek”
        # ko‘rsatmasligi uchun terminalga aniq xatoni chiqaramiz.
        print(f"BOT HANDLER ERROR: {event.exception!r}")
        try:
            update = event.update
            message = getattr(update, "message", None)
            if message:
                await message.answer(
                    "⚠️ Vaqtinchalik xatolik yuz berdi. /menu ni bosing va qayta urinib ko‘ring."
                )
        except Exception:
            pass
        return True

    await dp.start_polling(bot, db=db, api=api)

if __name__ == "__main__":
    asyncio.run(main())
