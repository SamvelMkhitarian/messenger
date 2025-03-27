from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Table, Text)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # Для удобства запросов
    sent_messages = relationship("Message", back_populates="sender")


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # personal / group


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)


# Промежуточная таблица для хранения участников групп
group_members = Table(
    "group_members",
    Base.metadata,
    Column("group_id", ForeignKey("groups.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    extend_existing=True
)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True),
                       server_default=func.now(), nullable=False)
    is_read = Column(Boolean, default=False)
    client_id = Column(String, unique=True, nullable=True)

    chat = relationship("Chat")
    sender = relationship("User", back_populates="sent_messages")
