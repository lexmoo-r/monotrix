from aiogram import Router, types
from aiogram.filters import CommandStart, Command

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я Монотрикс — тот, кто будет портить тебе жизнь фантами.\n"
        "Готов испытать судьбу?"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🔪 Список команд для тех, кто всё ещё надеется выжить:\n\n"
        "👤 /join <имя> — записаться в список добровольных мучеников\n"
        "🚪 /leave — покинуть арену страданий\n"
        "🎲 /start_game — запустить колесо безумия\n"
        "📚 /fant — получить свой приговор (фант)\n"
        "🔨 /punish — если захотел самонаказания\n"
        "⏭️ /skip — пропустить ход другого (только для админов)\n"
        "🙅 /pass — пропустить свой ход\n"
        "📋 /status — посмотреть статус игры\n"
        "🛑 /end_game — принудительно завершить игру\n"
        "♻️ /rename <новое имя> — сменить имя в игре\n"
        "❓ /help — напоминание для потерянных\n\n"
        "Пиши команды как взрослый человек и не ной."
    )
