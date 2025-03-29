from unittest.mock import AsyncMock

import pytest
from models import Message, User
from schemas import MessageWithSender
from ws_queries import (fetch_last_messages, mark_message_as_read,
                        save_new_message)


@pytest.mark.asyncio
async def test_fetch_last_messages():
    """
    Проверяет получение последних сообщений из чата.

    :return: список сообщений, преобразованных в MessageWithSender
    """
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.__iter__.return_value = [
        type(
            "Row",
            (),
            {
                "id": 1,
                "chat_id": 10,
                "sender_id": 2,
                "sender_name": "Alice",
                "text": "Hello",
                "timestamp": "2024-01-01T00:00:00",
                "is_read": False,
            },
        )()
    ]
    mock_db.execute.return_value = mock_result

    messages = await fetch_last_messages(chat_id=10, db=mock_db)
    assert len(messages) == 1
    assert isinstance(messages[0], MessageWithSender)
    assert messages[0].text == "Hello"


@pytest.mark.asyncio
async def test_save_new_message_skip_if_duplicate():
    """
    Проверяет поведение при попытке сохранить дубликат сообщения.

    :param client_id: уже существующий client_id
    :return: None, если сообщение уже существует
    """
    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = Message()

    user = User(id=1, name="Samvel", email="s@example.com",
                password_hash="hashed")

    result = await save_new_message(
        chat_id=5, user=user, text="Hey!", client_id="abc123", db=mock_db
    )
    assert result is None


@pytest.mark.asyncio
async def test_mark_message_as_read():
    """
    Проверяет логику отметки сообщения как прочитанного.

    :param user_id: идентификатор пользователя
    :param message_id: идентификатор сообщения
    :return: True, если запись успешно добавлена
    """
    mock_db = AsyncMock()
    result = await mark_message_as_read(user_id=1, message_id=99, db=mock_db)
    assert result is True
    mock_db.execute.assert_called()
    mock_db.commit.assert_called()
