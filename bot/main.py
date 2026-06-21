import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from bot.config.settings import get_settings
from bot.database.init_db import init_db
from bot.handlers import user, admin
from bot.services.reminders import setup_scheduler

async def main() -> None:
    settings = get_settings()
    await init_db(seed=True)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(user.router)
    scheduler = setup_scheduler(bot) if settings.reminders_enabled else None
    try:
        await dp.start_polling(bot)
    finally:
        if scheduler: scheduler.shutdown(wait=False)
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
