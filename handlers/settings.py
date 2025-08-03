from aiogram import Router, types
from aiogram.filters import Command
from utils import session_scope, is_bot_admin, safe_answer, get_settings

router = Router()

# Показать текущие настройки
@router.message(Command("show_settings"))
async def show_settings(message: types.Message):
    with session_scope() as db:
        settings = get_settings(db)
        text = (
            f"⚙️ Текущие настройки:\n\n"
            f"👥 Минимум игроков: {settings.min_players}\n"
            f"⏳ Время ожидания перед пингом: {settings.reminder_delay} секунд\n"
            f"📝 Кто может добавлять фанты: {'Все' if settings.add_mode == 'all' else 'Только админ'}"
        )
        await safe_answer(message, text)

# Установить минимальное количество игроков
@router.message(Command("set_min_players"))
async def set_min_players(message: types.Message):
    if message.chat.type != "private":
        await safe_answer(message, "Эта команда работает только в личке с ботом.")
        return

    if not await is_bot_admin(message.from_user.id):
        await safe_answer(message, "Ты не в списке админов. Нет доступа.")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer(
            "Формат команды:\n"
            "`/set_min_players <число>`\nПример:\n`/set_min_players 5`",
            parse_mode="Markdown"
        )
        return

    min_players = int(args[1])
    if min_players < 2:
        await safe_answer(message, "Минимум игроков — 2.")
        return

    with session_scope() as db:
        settings = get_settings(db)
        settings.min_players = min_players
        db.commit()
        await safe_answer(message, f"✅ Минимальное количество игроков установлено: `{min_players}`")

# Установить задержку перед пингом
@router.message(Command("set_reminder_delay"))
async def set_reminder_delay(message: types.Message):
    if message.chat.type != "private":
        await safe_answer(message, "Эта команда работает только в личке с ботом.")
        return

    if not await is_bot_admin(message.from_user.id):
        await safe_answer(message, "Ты не в списке админов. Нет доступа.")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer(
            "Формат команды:\n"
            "`/set_reminder_delay <секунды>`\nПример:\n`/set_reminder_delay 120`",
            parse_mode="Markdown"
        )
        return

    delay = int(args[1])
    if delay < 10:
        await safe_answer(message, "Меньше 10 секунд? Серьёзно?")
        return

    with session_scope() as db:
        settings = get_settings(db)
        settings.reminder_delay = delay
        db.commit()
        await safe_answer(message, f"✅ Время ожидания перед пингом установлено: `{delay}` секунд.")

# Установить режим добавления фантов
@router.message(Command("set_add_mode"))
async def set_add_mode(message: types.Message):
    if message.chat.type != "private":
        await safe_answer(message, "Эта команда работает только в личке с ботом.")
        return

    if not await is_bot_admin(message.from_user.id):
        await safe_answer(message, "Нет доступа к изменению режима.")
        return

    args = message.text.split()
    if len(args) != 2 or args[1] not in ("all", "admin_only"):
        await message.answer(
            "Формат команды:\n"
            "`/set_add_mode all` или `/set_add_mode admin_only`",
            parse_mode="Markdown"
        )
        return

    mode = args[1]

    with session_scope() as db:
        settings = get_settings(db)
        settings.add_mode = mode
        db.commit()
        readable_mode = "все могут добавлять фанты" if mode == "all" else "только админы могут добавлять фанты"
        await safe_answer(message, f"✅ Режим добавления фантов установлен: `{readable_mode}`")
