from database import Base
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Table, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # Для удобства запросов
    sent_messages = relationship("Message", back_populates="sender")


class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # personal / group


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Допустим, участников будем хранить через связку group_members (many-to-many)


# Промежуточная таблица для хранения участников групп
group_members = Table(
    "group_members",
    Base.metadata,
    Column("group_id", ForeignKey("groups.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True),
                       server_default=func.now(), nullable=False)
    is_read = Column(Boolean, default=False)

    chat = relationship("Chat")
    sender = relationship("User", back_populates="sent_messages")


class MessageRead(Base):
    __tablename__ = "message_reads"
    '''
    Для более точного трекинга «кто прочитал», отдельная таблица:
    Но по заданию поле "прочитано" в messages – ставим True, когда все прочитали (или 1v1).
    Если нужно сделать частичные прочтения для групп, можно хранить в message_reads.
    '''
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    read_at = Column(DateTime(timezone=True),
                     server_default=func.now(), nullable=False)
