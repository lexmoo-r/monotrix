from contextlib import contextmanager
from sqlalchemy.orm import Session
from aiogram import types
from config import ADMIN_IDS
from database import SessionLocal, Settings

DEFAULT_MIN_PLAYERS = 4
DEFAULT_VOTE_TIMEOUT = 600  # 10 минут
DEFAULT_VOTE_SPECIAL_FANT_CHANCE = 50  # 50%

@contextmanager
def session_scope():
    """Контекстный менеджер для сессии базы данных."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def safe_answer(message: types.Message, text: str):
    """Безопасная отправка сообщения пользователю."""
    try:
        await message.answer(text)
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

async def safe_edit(message: types.Message, text: str):
    """Безопасное редактирование сообщения."""
    try:
        await message.edit_text(text)
    except Exception as e:
        print(f"Ошибка редактирования сообщения: {e}")

async def is_bot_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором бота."""
    return user_id in ADMIN_IDS

async def is_admin(message: types.Message) -> bool:
    """Проверка, является ли пользователь админом чата."""
    if message.chat.type not in ("group", "supergroup"):
        return False
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ("administrator", "creator")

def is_private_chat(message: types.Message) -> bool:
    """Проверка, является ли чат личным."""
    return message.chat.type == "private"

def get_settings(db: Session) -> Settings:
    """Получение или создание настроек."""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
        db.commit()
    return settings