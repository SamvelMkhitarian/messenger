from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей
    """

    pass


class User(Base):
    """
    Модель пользователя

    :id: первичный ключ
    :name: имя пользователя
    :email: уникальный email
    :password_hash: хеш пароля
    :sent_messages: связь с отправленными сообщениями
    """

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    sent_messages = relationship("Message", back_populates="sender")


class Chat(Base):
    """
    Модель чата

    :id: первичный ключ
    :name: имя чата
    :type: тип чата (personal / group)
    """

    __tablename__ = "chats"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # personal / group


class Group(Base):
    """
    Модель группы

    :id: первичный ключ
    :name: название группы
    :creator_id: id пользователя-создателя
    """

    __tablename__ = "groups"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)


# Промежуточная таблица для хранения участников групп
group_members = Table(
    "group_members",
    Base.metadata,
    Column("group_id", ForeignKey("groups.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    extend_existing=True,
)


class Message(Base):
    """
    Модель сообщения

    :id: первичный ключ
    :chat_id: внешний ключ на чат
    :sender_id: внешний ключ на пользователя
    :text: текст сообщения
    :timestamp: дата и время отправки
    :is_read: статус прочтения
    :client_id: уникальный ID сообщения от клиента
    :chat: связь с чатом
    :sender: связь с отправителем
    """

    __tablename__ = "messages"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_read = Column(Boolean, default=False)
    client_id = Column(String, unique=True, nullable=True)

    chat = relationship("Chat")
    sender = relationship("User", back_populates="sent_messages")
