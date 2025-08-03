from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Text, JSON, TIMESTAMP, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Fant(Base):
    __tablename__ = 'fant'

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    used = Column(Boolean, default=False)
    author_id = Column(BigInteger, nullable=True)
    author_tag = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class SessionPlayer(Base):
    __tablename__ = 'session_player'

    tg_id = Column(BigInteger, primary_key=True)
    name = Column(String(50), nullable=False)
    username = Column(String(100), nullable=True)  
    in_rotation = Column(Boolean, default=True)
    joined_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class SessionState(Base):
    __tablename__ = 'session_state'

    chat_id = Column(BigInteger, primary_key=True)
    current_index = Column(Integer, default=0)
    player_order = Column(JSON, nullable=False)
    round = Column(Integer, default=1)
    started = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    min_players = Column(Integer, default=4)
    reminder_delay = Column(Integer, default=120)  # в секундах
    add_mode = Column(String(20), default='admin_only')  # 'all' или 'admin_only'

# Настройка базы данных
DATABASE_URL = 'sqlite:///monotrix.db'  # SQLite для примера
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
