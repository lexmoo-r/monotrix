import asyncio
import random
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.sql import func
from database import SessionPlayer, SessionState, Fant
from sqlalchemy.orm.attributes import flag_modified
from utils import session_scope, safe_answer, get_settings, is_admin

router = Router()

# 🆕 глобальная переменная для хранения текущего таска
current_ping_task = {}

def is_group_chat(message: types.Message) -> bool:
    return message.chat.type in ("group", "supergroup")

@router.message(Command("fant"))
async def get_fant(message: types.Message):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда работает только в группе.")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    with session_scope() as db:
        state = db.query(SessionState).filter_by(chat_id=chat_id, started=True).first()
        if not state:
            await safe_answer(message, "Веселье ещё не началось. Сиди ровно.")
            return

        if state.player_order[state.current_index] != user_id:
            await safe_answer(message, "Сначала дождись своей очереди, скорострел.")
            return

        fant = db.query(Fant).filter_by(used=False).order_by(func.random()).first()
        if not fant:
            await safe_answer(message, "Фанты закончились. Безумие тоже когда-то кончается.")
            state.started = False
            db.commit()
            return

        fant.used = True
        db.commit()

        # Информация про следующего игрока и количество фантов
        players = db.query(SessionPlayer).filter(SessionPlayer.tg_id.in_(state.player_order)).all()
        players_dict = {player.tg_id: player for player in players}
        next_index = (state.current_index + 1) % len(state.player_order)
        next_player_id = state.player_order[next_index]
        next_player = players_dict.get(next_player_id)

        total_fants = db.query(Fant).filter_by(used=False).count()

        if next_player:
            next_player_info = f"⏳ Следующий игрок: {next_player.name}"
        else:
            next_player_info = "⏳ Следующий игрок: неизвестно (возможно, новый участник)"

        await message.answer(
            f"Твоё задание:\n\n"
            f"{fant.text}\n\n"
            f"📚 Осталось фантов: {total_fants}\n"
            f"{next_player_info}"
        )

        # ⬇️ Сдвиг индекса сделаем в start_turn
        await start_turn(message, db, advance_turn=True)

@router.message(Command("punish"))
async def punish_self(message: types.Message):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда работает только в группе.")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    with session_scope() as db:
        state = db.query(SessionState).filter_by(chat_id=chat_id, started=True).first()
        if not state:
            await safe_answer(message, "Игра ещё не началась. Сначала устрой себе веселье, потом уже страдай.")
            return

        if user_id not in state.player_order:
            await safe_answer(message, "Ты не в игре. Сначала подпишись на страдания, потом проси фант.")
            return

        fant = db.query(Fant).filter_by(used=False).order_by(func.random()).first()
        if not fant:
            await safe_answer(message, "Фанты закончились. Даже наказать тебя нечем.")
            return

        fant.used = True
        db.commit()

        player = db.query(SessionPlayer).filter_by(tg_id=user_id).first()

        await message.answer(
            f"🔨 @{player.name}, сам напросился! Получи штрафной фант:\n\n"
            f"⚡️ {fant.text}\n\n"
            f"Страдай красиво."
        )

@router.message(Command("skip"))
async def skip_turn(message: types.Message):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда работает только в группе.")
        return

    chat_id = message.chat.id

    with session_scope() as db:
        state = db.query(SessionState).filter_by(chat_id=chat_id, started=True).first()
        if not state:
            await safe_answer(message, "Игра ещё не началась. Кого ты там хочешь скипнуть?")
            return

        if not await is_admin(message):
            await safe_answer(message, "Ты что, админ? Нет? Тогда тихо сиди.")
            return

        players = db.query(SessionPlayer).filter(SessionPlayer.tg_id.in_(state.player_order)).all()
        players_dict = {player.tg_id: player for player in players}
        next_index = (state.current_index + 1) % len(state.player_order)
        next_player = players_dict.get(state.player_order[next_index])

        await safe_answer(message, f"Ход пропущен. Следующий к эшафоту: {next_player.name}")
        await start_turn(message, db, advance_turn=True)  # <- Продвигаем ход через start_turn


@router.message(Command("pass"))
async def pass_turn(message: types.Message):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда работает только в группе.")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    with session_scope() as db:
        state = db.query(SessionState).filter_by(chat_id=chat_id, started=True).first()
        if not state:
            await safe_answer(message, "Игра не запущена. Чего ты там пропускаешь?")
            return

        current_player_id = state.player_order[state.current_index]
        if current_player_id != user_id:
            await safe_answer(message, "Не твой ход, не тебе и пропускать.")
            return

        player = db.query(SessionPlayer).filter_by(tg_id=user_id).first()
        if not player:
            await safe_answer(message, "Ошибка: игрок не найден. Мистика какая-то.")
            return

        player.in_rotation = False
        db.commit()

        await safe_answer(message, "Вы пропустили ход. Вернётесь в следующем круге — если доживёте.")

        players = db.query(SessionPlayer).filter(SessionPlayer.tg_id.in_(state.player_order)).all()
        players_dict = {player.tg_id: player for player in players}

        await start_turn(message, db, advance_turn=True)  # <- Продвигаем ход через start_turn

async def start_turn(message: types.Message, db, advance_turn: bool = True):
    global current_ping_task
    chat_id = message.chat.id
    state = db.query(SessionState).filter_by(chat_id=chat_id, started=True).first()
    if not state:
        await safe_answer(message, "Веселье ещё не началось. Потерпи.")
        return

    # Сдвиг хода — только если advance_turn = True
    if advance_turn:
        state.current_index += 1
        if state.current_index >= len(state.player_order):
            # Конец круга — увеличиваем раунд и обновляем очередь
            state.round += 1

            # 🆕 Обновляем player_order: берём всех игроков из базы
            players = db.query(SessionPlayer).all()
            state.player_order = [player.tg_id for player in players]
            random.shuffle(state.player_order)
            flag_modified(state, "player_order")

            state.current_index = 0  # Сбросить на первого игрока
        db.commit()

    # Берём игроков для текущего состояния
    players = db.query(SessionPlayer).filter(SessionPlayer.tg_id.in_(state.player_order)).all()
    players_dict = {player.tg_id: player for player in players}

    current_player_id = state.player_order[state.current_index]
    current_player = players_dict.get(current_player_id)

    if not current_player:
        await safe_answer(message, "Ошибка. Даже у нас бывают сбои в матрице.")
        return

    # Новый круг или 1-й раунд — объявляем порядок
    if state.current_index == 0 or state.round == 1:
        players_list = "\n".join(
            f"{idx + 1}. {players_dict[player_id].name}" for idx, player_id in enumerate(state.player_order)
        )
        await message.answer(
            f"🌀 Раунд {state.round}!\n\n"
            f"Очередность:\n{players_list}"
        )

    # Отменить прошлую задачу пинга, если она была
    task = current_ping_task.get(chat_id)
    if task and not task.done():
        task.cancel()

    current_ping_task[chat_id] = asyncio.create_task(ping_current_player(message, state.current_index))

async def ping_current_player(message: types.Message, start_index: int):
    try:
        with session_scope() as db:
            settings = get_settings(db)
            reminder_delay = settings.reminder_delay

        await asyncio.sleep(reminder_delay)

        with session_scope() as db:
            state = db.query(SessionState).filter_by(chat_id=message.chat.id, started=True).first()
            if not state or state.current_index != start_index:
                return

            players = db.query(SessionPlayer).filter(SessionPlayer.tg_id.in_(state.player_order)).all()
            players_dict = {player.tg_id: player for player in players}

            current_player = players_dict.get(state.player_order[state.current_index])

            if current_player:
                username_part = f" (@{current_player.username})" if current_player.username else ""
                await message.answer(
                    f"{current_player.name}{username_part}, /fant сам себя не возьмет, знаешь ли."
                )
    except asyncio.CancelledError:
        pass 

@router.message(Command("reset_queue"))
async def reset_queue(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await safe_answer(message, "Сбрасывать очередь можно только в группе.")
        return

    chat_id = message.chat.id

    with session_scope() as db:
        players = db.query(SessionPlayer).all()
        if not players:
            await safe_answer(message, "Нет игроков. Кого ты собираешься тасовать?")
            return

        player_ids = [p.tg_id for p in players]
        random.shuffle(player_ids)

        state = db.query(SessionState).filter_by(chat_id=chat_id).first()
        if not state:
            state = SessionState(chat_id=chat_id)

        state.player_order = player_ids
        state.current_index = 0
        state.round = 1
        state.started = True
        flag_modified(state, "player_order")
        db.merge(state)
        db.commit()

        players_dict = {p.tg_id: p.name for p in players}
        players_list = "\n".join(
            f"{idx + 1}. {players_dict[player_id]}" for idx, player_id in enumerate(player_ids)
        )

        await message.answer(
            f"♻️ Очередь сброшена и пересоставлена!\n\n"
            f"Новый порядок:\n{players_list}"
        )

        # Автостарт с нового игрока
        from handlers.fant import start_turn  # ⚠️ Локальный импорт, если всё ещё актуально
        await start_turn(message, db, advance_turn=False)  # Важно: не сдвигать ход сразу!

