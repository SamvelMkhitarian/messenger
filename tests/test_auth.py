from uuid import uuid4

import pytest
from conftest import login_user, register_user
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_access_without_token(client: AsyncClient):
    """
    Проверяет доступ к защищённому эндпоинту без токена:
    - Отправляет GET-запрос на /get_chats без заголовков
    - Проверяет, что вернётся 403 и сообщение об ошибке
    """
    response = await client.get("/get_chats")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_access_with_invalid_token(client: AsyncClient):
    """
    Проверяет доступ с невалидным токеном:
    - Отправляет GET-запрос на /get_chats с поддельным токеном
    - Ожидает статус 401 и сообщение о невалидных данных
    """
    headers = {"Authorization": "Bearer invalid.token.value"}
    response = await client.get("/get_chats", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.asyncio
async def test_access_with_valid_token(client: AsyncClient):
    """
    Проверяет доступ с валидным токеном:
    - Регистрирует пользователя и получает токен
    - Отправляет GET-запрос на /get_chats с токеном
    - Ожидает статус 200 и список чатов в ответе
    """
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "User", email, password)
    token = await login_user(client, email, password)

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/get_chats", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_access_with_tampered_token(client: AsyncClient):
    """
    Проверяет отклонение подделанного токена:
    - Получает токен, вручную изменяет последний символ
    - Отправляет запрос с поддельным токеном
    - Ожидает статус 401 и сообщение о невалидных данных
    """
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "Password1"
    await register_user(client, "User", email, password)
    token = await login_user(client, email, password)

    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = await client.get("/get_chats", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
