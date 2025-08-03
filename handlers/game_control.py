import asyncio
import random
from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from database import SessionPlayer, SessionState, Settings, Fant
from utils import session_scope, safe_answer, is_admin, get_settings

active_votes = {}

router = Router()

def is_group_chat(message: types.Message) -> bool:
    return message.chat.type in ("group", "supergroup")

@router.message(Command("start_game"))
async def start_game(message: types.Message):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда доступна только в группе.")
        return

    chat_id = message.chat.id

    with session_scope() as db:
        existing_state = db.query(SessionState).filter_by(chat_id=chat_id).first()
        if existing_state and existing_state.started:
            await safe_answer(message, "Эй, гений, игра уже идёт. Следи за событиями.")
            return

        players = db.query(SessionPlayer).all()

        if not players:
            await safe_answer(message, "Ваc буквально 0. Играть будет ветер и песок?")
            return

        settings = get_settings(db)
        min_players = settings.min_players if settings else 4

        if len(players) < min_players:
            await safe_answer(
                message,
                f"Подберите друзей, вас мало. Нужно минимум {min_players}, а сейчас только {len(players)}."
            )
            return

        player_ids = [p.tg_id for p in players]
        random.shuffle(player_ids)

        state = SessionState(
            chat_id=chat_id,
            player_order=player_ids,
            current_index=0,
            round=1,
            started=True
        )
        db.merge(state)
        db.commit()

        players_dict = {p.tg_id: p.name for p in players}
        players_list = "\n".join(f"{idx+1}. {players_dict[player_id]}" for idx, player_id in enumerate(player_ids))

        await safe_answer(message, f"ДА НАЧНЁТСЯ ЖЕ ВЕСЕЛЬЕ!")

        from handlers.fant import start_turn
        await start_turn(message, db)

@router.message(Command("reset"))
async def reset_game(message: types.Message):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда доступна только в группе.")
        return

    if not await is_admin(message):
        await safe_answer(message, "Только администратор может сбросить игру. Монократия работает.")
        return

    with session_scope() as db:
        chat_id = message.chat.id
        db.query(SessionState).filter_by(chat_id=chat_id).delete()
        db.query(SessionPlayer).delete()
        db.commit()

        to_delete = [key for key in active_votes if key[0] == chat_id]
        for key in to_delete:
            del active_votes[key]

        await safe_answer(message, "Игра сброшена. Добро пожаловать в пустоту.")

@router.message(Command("status"))
async def game_status(message: types.Message):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда доступна только в группе.")
        return

    chat_id = message.chat.id

    with session_scope() as db:
        state = db.query(SessionState).filter_by(chat_id=chat_id, started=True).first()
        if not state:
            await safe_answer(message, "Веселье ещё не началось. Статус: уныние.")
            return

        players = db.query(SessionPlayer).filter(SessionPlayer.tg_id.in_(state.player_order)).all()
        players_dict = {player.tg_id: player for player in players}

        if not players:
            await safe_answer(message, "Здесь даже друзей по переписке нет.")
            return

        current_player_id = state.player_order[state.current_index]
        current_player = players_dict.get(current_player_id)

        next_index = (state.current_index + 1) % len(state.player_order)
        next_player = players_dict.get(state.player_order[next_index])

        total_fants = db.query(Fant).filter_by(used=False).count()

        status_lines = []

        for idx, player_id in enumerate(state.player_order):
            player = players_dict.get(player_id)
            if not player:
                continue
            mark = "🟢" if player.in_rotation else "⏸️"
            pointer = "➡️" if player_id == current_player_id else ""
            status_lines.append(f"{idx+1}. {mark} {player.name} {pointer}")

        status_text = "\n".join(status_lines)

        await safe_answer(
            message,
            f"📋 Статус игры:\n\n"
            f"Раунд: {state.round}\n"
            f"Осталось фантов: {total_fants}\n\n"
            f"{status_text}\n\n"
            f"Сейчас ходит: {current_player.name}\n"
            f"Следующий: {players_dict.get(state.player_order[next_index]).name}"
        )

@router.message(Command("end_game"))
async def end_game(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await safe_answer(message, "Команда работает только в группе.")
        return

    if not await is_admin(message):
        await safe_answer(message, "Только администратор может завершить игру.")
        return

    with session_scope() as db:
        chat_id = message.chat.id
        db.query(SessionState).filter_by(chat_id=chat_id).delete()
        db.query(SessionPlayer).delete()
        db.commit()
        await safe_answer(message, "Игра завершена досрочно. Все свободны.")

@router.message(Command("kick"))
async def cmd_kick_player(message: types.Message, command: CommandObject):
    if not is_group_chat(message):
        await safe_answer(message, "Эта команда работает только в группе.")
        return

    if not await is_admin(message):
        await safe_answer(message, "Только админы могут устраивать чистки.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await safe_answer(message, "Формат команды: /kick <имя игрока>")
        return

    player_name = args[1].strip()

    with session_scope() as db:
        player = db.query(SessionPlayer).filter_by(name=player_name).first()
        if not player:
            await safe_answer(message, f"Нет такого страдальца по имени '{player_name}'.")
            return

        db.delete(player)
        db.commit()

        await safe_answer(message, f"{player_name} вылетает из игры. Надеюсь, он не сильно расстроится.")