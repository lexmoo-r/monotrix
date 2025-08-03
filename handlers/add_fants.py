from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from fsm import AddFant
from database import SessionLocal, Fant
from keyboards import stop_adding_keyboard
from utils import is_private_chat, safe_answer, session_scope, safe_answer, is_bot_admin

router = Router()

@router.message(Command("add_fant"))
async def cmd_add_fant(message: types.Message, state: FSMContext):
    if not is_private_chat(message):
        await safe_answer(message, "Добавлять фанты можно только в ЛС с ботом.")
        return

    await message.answer(
        "Время стать автором унижений! Кидай текст фанта — одно сообщение, один фант.\n"
        "Когда устанешь — нажми кнопку ниже или пиши /stop.",
        reply_markup=stop_adding_keyboard()
    )
    await state.set_state(AddFant.waiting_for_fant)

@router.callback_query(F.data == "stop_adding")
async def stop_adding_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()  # Убираем кнопку после нажатия
    await callback.message.answer("Всё, нагенерился? Добавление фантов завершено.")
    await state.clear()
    await callback.answer()  # Закрыть кружок загрузки у кнопки

@router.message(Command("stop"))
async def cmd_stop_adding(message: types.Message, state: FSMContext):
    if not is_private_chat(message):
        await safe_answer(message, "Добавлять фанты можно только в ЛС с ботом.")
        return

    await message.answer("Окей, фантазия иссякла. Добавление фантов завершено.")
    await state.clear()

@router.message(AddFant.waiting_for_fant, F.text)
async def process_fant(message: types.Message, state: FSMContext):
    if not is_private_chat(message):
        await safe_answer(message, "Добавлять фанты можно только в ЛС с ботом.")
        return

    fant_text = message.text.strip()
    if not fant_text:
        await message.answer("Пустые фанты? Серьёзно? Попробуй хотя бы изобразить мысль.")
        return

    db = SessionLocal()
    try:
        new_fant = Fant(
            text=fant_text,
            used=False,
            author_id=message.from_user.id,
            author_tag=message.from_user.username
        )
        db.add(new_fant)
        db.commit()
        await message.answer(
            "Записал твой великий труд. Кидай следующий шедевр или команду /stop, если ручки устали."
        )
    finally:
        db.close()

@router.message(Command("clear_fants"))
async def clear_fants(message: types.Message):
    if message.chat.type != "private":
        return

    if not await is_bot_admin(message.from_user.id):
        await safe_answer(message, "Нет доступа. Ты не админ Монократии.")
        return

    with session_scope() as db:
        db.query(Fant).delete()
        db.commit()
    await safe_answer(message, "✅ Все фанты удалены.")

@router.message(Command("reset_fants"))
async def reset_fants(message: types.Message):
    if message.chat.type != "private":
        return

    if not await is_bot_admin(message.from_user.id):
        await safe_answer(message, "Нет доступа. Только админы могут сбрасывать фанты.")
        return

    with session_scope() as db:
        db.query(Fant).update({Fant.used: False})
        db.commit()
    await safe_answer(message, "✅ Все фанты сброшены. Они снова в игре.")

@router.message(Command("list_fants"))
async def list_fants(message: types.Message):
    if message.chat.type != "private":
        return

    if not await is_bot_admin(message.from_user.id):
        await safe_answer(message, "Нет доступа.")
        return

    with session_scope() as db:
        fants = db.query(Fant).all()
        if not fants:
            await safe_answer(message, "В базе нет фантов.")
            return

        text = "📜 Список фантов:\n\n"
        for fant in fants:
            text += f"ID: {fant.id}\nТекст: {fant.text}\n\n"

        # Ограничение Telegram на размер сообщений
        for i in range(0, len(text), 4000):
            await safe_answer(message, text[i:i+4000])

@router.message(Command("delete_fant"))
async def delete_fant(message: types.Message):
    if message.chat.type != "private":
        return

    if not await is_bot_admin(message.from_user.id):
        await safe_answer(message, "Нет доступа.")
        return

    args = message.text.strip().split()
    if len(args) != 2 or not args[1].isdigit():
        await safe_answer(message, "Формат команды: `/delete_fant <ID>`", parse_mode="Markdown")
        return

    fant_id = int(args[1])

    with session_scope() as db:
        fant = db.query(Fant).filter_by(id=fant_id).first()
        if not fant:
            await safe_answer(message, f"Фант с ID {fant_id} не найден.")
            return

        db.delete(fant)
        db.commit()
        await safe_answer(message, f"✅ Фант с ID {fant_id} удалён.")