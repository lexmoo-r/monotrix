from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
import logging
from config import TOKEN
from handlers import add_fants, general, settings, fant, join_leave, game_control

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# Подключение роутеров
dp.include_router(general.router)
dp.include_router(add_fants.router)
dp.include_router(settings.router)
dp.include_router(fant.router)
dp.include_router(join_leave.router)
dp.include_router(game_control.router)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="help", description="Справка")
    ])
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
