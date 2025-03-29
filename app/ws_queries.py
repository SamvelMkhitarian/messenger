import json
from typing import Any

from models import Message, MessageRead, User
from schemas import MessageWithSender
from sqlalchemy import join, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_last_messages(chat_id: int, db: AsyncSession) -> list[MessageWithSender]:
    """
    Получить последние 50 сообщений в чате по его ID.

    :param chat_id: идентификатор чата
    :param db: сессия базы данных
    :return: список сообщений с данными отправителя
    """
    result = await db.execute(
        select(
            Message.id,
            Message.chat_id,
            Message.sender_id,
            User.name.label("sender_name"),
            Message.text,
            Message.timestamp,
            Message.is_read,
        )
        .select_from(join(Message, User, Message.sender_id == User.id))
        .where(Message.chat_id == chat_id)
        .order_by(Message.timestamp.asc())
        .limit(50)
    )
    return [
        MessageWithSender(
            id=row.id,
            chat_id=row.chat_id,
            sender_id=row.sender_id,
            sender_name=row.sender_name,
            text=row.text,
            timestamp=row.timestamp,
            is_read=row.is_read,
        )
        for row in result
    ]


async def save_new_message(
    chat_id: int, user: User, text: str, client_id: str, db: AsyncSession
) -> MessageWithSender | None:
    """
    Сохранить новое сообщение в базу, если оно ещё не было отправлено (по client_id).

    :param chat_id: идентификатор чата
    :param user: объект текущего пользователя
    :param text: текст сообщения
    :param client_id: уникальный идентификатор сообщения от клиента
    :param db: сессия базы данных
    :return: сообщение с данными отправителя или None, если дубликат
    """
    existing = await db.execute(select(Message).where(Message.client_id == client_id))
    if existing.scalar_one_or_none():
        return None

    new_msg = Message(
        chat_id=chat_id,
        sender_id=user.id,
        text=text,
        client_id=client_id,
    )
    db.add(new_msg)
    await db.commit()
    await db.refresh(new_msg)

    return MessageWithSender(
        id=new_msg.id,
        chat_id=new_msg.chat_id,
        sender_id=new_msg.sender_id,
        sender_name=user.name,
        text=new_msg.text,
        timestamp=new_msg.timestamp,
        is_read=new_msg.is_read,
    )


async def mark_message_as_read(user_id: int, message_id: int, db: AsyncSession) -> bool:
    """
    Отметить сообщение как прочитанное для конкретного пользователя.

    :param user_id: идентификатор пользователя
    :param message_id: идентификатор сообщения
    :param db: сессия базы данных
    :return: True при успешной записи
    """
    stmt = (
        insert(MessageRead).values(user_id=user_id, message_id=message_id).on_conflict_do_nothing()
    )
    await db.execute(stmt)
    await db.commit()
    return True
