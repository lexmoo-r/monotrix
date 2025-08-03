from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.exc import IntegrityError
from database import SessionPlayer, SessionState
from utils import session_scope, safe_answer

router = Router()

@router.message(Command("join"))
async def join_game(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await safe_answer(message, "Присоединяться к игре можно только в группах.")
        return

    character_name = message.text.replace("/join", "", 1).strip()

    if not character_name:
        await safe_answer(
            message,
            "Ну-ка, кто это у нас тут? Напиши своё имя, чтобы я занёс его в реестр безумцев.\n"
            "Пример: /join Киригири Кёко"
        )
        return

    if len(character_name) < 2 or len(character_name) > 50:
        await safe_answer(message, "Если твоё имя из одной буквы — поздравляю, ты не проходишь кастинг.")
        return

    with session_scope() as db:
        # Проверяем, есть ли уже игрок с таким именем
        existing_name = db.query(SessionPlayer).filter_by(name=character_name).first()
        if existing_name:
            await safe_answer(message, f"'{character_name}' уже есть в списке. Поговори с родителями о творчестве.")
            return

        # Проверяем, есть ли уже игрок с таким Telegram ID
        existing_player = db.query(SessionPlayer).filter_by(tg_id=message.from_user.id).first()
        if existing_player:
            await safe_answer(message, "Ты уже в игре, гений.")
            return

        try:
            new_player = SessionPlayer(
                tg_id=message.from_user.id,
                name=character_name,
                username=message.from_user.username
            )
            db.add(new_player)
            db.commit()

            # Проверка на запущенность игры
            state = db.query(SessionState).filter_by(chat_id=message.chat.id, started=True).first()
            if state:
                await safe_answer(
                    message,
                    f"{character_name} записан в списки ожидания! 📝 Присоединишься в новом раунде."
                )
            else:
                await safe_answer(
                    message,
                    f"{character_name} подписывает контракт. Приветствуем нового искателя приключений!"
                )
        except IntegrityError:
            db.rollback()
            await safe_answer(message, "Ошибка базы данных. Даже база данных от тебя офигела.")

@router.message(Command("leave"))
async def leave_game(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await safe_answer(message, "Покидать игру можно только в группах.")
        return

    with session_scope() as db:
        player = db.query(SessionPlayer).filter_by(tg_id=message.from_user.id).first()
        if not player:
            await safe_answer(message, "Ты даже не зашёл, но уже сваливаешь? Позорище.")
            return

        db.delete(player)
        db.commit()
        await safe_answer(message, f"{player.name} покидает арену, спасаясь от позора.")

@router.message(Command("rename"))
async def rename_player(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await safe_answer(message, "Переименование доступно только в группе.")
        return

    args = message.text.strip().split(maxsplit=1)
    if len(args) != 2:
        await safe_answer(message, "Формат команды:\n`/rename <новое_имя>`", parse_mode="Markdown")
        return

    new_name = args[1].strip()
    if len(new_name) < 2 or len(new_name) > 50:
        await safe_answer(message, "Имя должно быть от 2 до 50 символов.")
        return

    with session_scope() as db:
        player = db.query(SessionPlayer).filter_by(tg_id=message.from_user.id).first()
        if not player:
            await safe_answer(message, "Ты не в игре. Нечего переименовывать.")
            return

        player.name = new_name
        db.commit()
        await safe_answer(message, f"✅ Теперь ты известен как {new_name}. Красиво звучит, да?")