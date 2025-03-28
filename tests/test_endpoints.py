from uuid import uuid4

import pytest
from conftest import login_user, register_user
from database import get_db_session
from httpx import AsyncClient
from models import Message, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """
    Проверяет успешную регистрацию пользователя:
    - Отправляет POST-запрос на /register
    - Проверяет статус 200 и наличие email и id в ответе
    """
    email = f"test_{uuid4().hex[:8]}@example.com"
    response = await client.post("/register", data={"name": "Тест", "email": email, "password": "Password1"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """
    Проверяет, что повторная регистрация с тем же email вызывает ошибку:
    - Первый запрос проходит успешно
    - Второй возвращает 400 и сообщение об ошибке
    """
    email = f"test_{uuid4().hex[:8]}@example.com"
    await register_user(client, "Тест", email, "Password1")
    response = await client.post("/register", data={"name": "Тест 2", "email": email, "password": "Password1"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Email уже зарегистрирован"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """
    Проверяет успешную авторизацию:
    - Регистрирует пользователя
    - Выполняет вход
    - Проверяет наличие токена и типа bearer
    """
    email = f"test_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "Test User", email, password)
    response = await client.post("/login", data={"username": email, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_create_chat_success(client: AsyncClient):
    """
    Проверяет создание приватного чата:
    - Регистрирует и авторизует пользователя
    - Отправляет POST-запрос на /create_chats
    - Проверяет успешный статус и содержимое ответа
    """
    email = f"test_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "User", email, password)
    token = await login_user(client, email, password)

    response = await client.post(
        "/create_chats",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Chat", "type": "private"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Chat"
    assert data["type"] == "private"
    assert "chat_id" in data


@pytest.mark.asyncio
async def test_get_user_chats_success(client: AsyncClient):
    """
    Проверяет получение списка чатов пользователя:
    - Создаёт чат
    - Запрашивает список через /get_chats
    - Проверяет, что нужный чат присутствует в списке
    """
    email = f"test_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "Chat Tester", email, password)
    token = await login_user(client, email, password)
    # Создаём чат
    await client.post(
        "/create_chats",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Chat 1", "type": "private"}
    )
    # Получаем список
    response = await client.get("/get_chats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    chats_list = response.json()
    assert isinstance(chats_list, list)
    assert any(chat["name"] == "Chat 1" for chat in chats_list)


@pytest.mark.asyncio
async def test_create_group_chat_success(client: AsyncClient):
    """
    Проверяет создание группового чата:
    - Регистрирует пользователя
    - Создаёт групповой чат
    - Проверяет поля name, type, chat_id и group_id в ответе
    """
    email = f"test_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "Group User", email, password)
    token = await login_user(client, email, password)

    response = await client.post(
        "/create_chats",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "My Group", "type": "group"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Group"
    assert data["type"] == "group"
    assert "chat_id" in data
    assert "group_id" in data


@pytest.mark.asyncio
async def test_join_group_success(client: AsyncClient):
    """
    Проверяет успешное присоединение к группе:
    - Один пользователь создаёт группу
    - Второй пользователь присоединяется
    - Проверяется успешный ответ и сообщение о вступлении
    """
    creator_email = f"creator_{uuid4().hex[:8]}@example.com"
    joiner_email = f"joiner_{uuid4().hex[:8]}@example.com"
    password = "Password1"

    # Создатель группы
    await register_user(client, "Creator", creator_email, password)
    creator_token = await login_user(client, creator_email, password)
    group_response = await client.post(
        "/create_chats",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"name": "Group Chat", "type": "group"}
    )
    assert group_response.status_code == 200
    group_id = group_response.json()["group_id"]

    # Присоединяющийся участник
    await register_user(client, "Joiner", joiner_email, password)
    joiner_token = await login_user(client, joiner_email, password)
    join_response = await client.post(f"/groups/{group_id}/join", headers={"Authorization": f"Bearer {joiner_token}"})
    assert join_response.status_code == 200
    assert f"присоединился к группе {group_id}" in join_response.json()[
        "detail"]


@pytest.mark.asyncio
async def test_join_group_already_member(client: AsyncClient):
    """
    Проверяет повторное присоединение к одной и той же группе:
    - Пользователь создаёт и присоединяется к группе
    - Повторное присоединение возвращает сообщение "Already in group"
    """
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "User", email, password)
    token = await login_user(client, email, password)

    group_resp = await client.post(
        "/create_chats",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Group", "type": "group"}
    )
    assert group_resp.status_code == 200
    group_id = group_resp.json()["group_id"]

    # Первый раз присоединяемся
    first_join = await client.post(f"/groups/{group_id}/join", headers={"Authorization": f"Bearer {token}"})
    assert first_join.status_code == 200

    # Второй раз — Already in group
    second_join = await client.post(f"/groups/{group_id}/join", headers={"Authorization": f"Bearer {token}"})
    assert second_join.status_code == 200
    assert second_join.json(
    )["detail"] == "Пользователь уже находится в группе."


@pytest.mark.asyncio
async def test_join_nonexistent_group(client: AsyncClient):
    """
    Проверяет попытку вступить в несуществующую группу:
    - Отправляется запрос на /groups/999999/join
    - Проверяется статус 404 и сообщение об ошибке
    """
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "User", email, password)
    token = await login_user(client, email, password)
    response = await client.post("/groups/999999/join", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Группа не найдена."


@pytest.mark.asyncio
async def test_chat_history_success(client: AsyncClient):
    """
    Проверяет получение истории сообщений:
    - Создаёт чат и вручную добавляет 3 сообщения в базу
    - Отправляет GET-запрос на /history/{chat_id}
    - Проверяет, что возвращаются все сообщения и указано имя отправителя
    """
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    user_name = "Историк"
    await register_user(client, user_name, email, password)
    token = await login_user(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём чат
    chat_resp = await client.post("/create_chats", headers=headers, json={"name": "История", "type": "private"})
    assert chat_resp.status_code == 200
    chat_id = chat_resp.json()["chat_id"]

    # Наполним сообщениями прямо в БД
    async for session in get_db_session():
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        for i in range(3):
            session.add(Message(chat_id=chat_id, sender_id=user.id,
                        text=f"Сообщение {i+1}", is_read=False))
        await session.commit()
        break

    # Проверка истории
    response = await client.get(f"/history/{chat_id}", headers=headers)
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 3
    assert all("sender_name" in msg for msg in messages)
    assert all(msg["sender_name"] == user_name for msg in messages)
