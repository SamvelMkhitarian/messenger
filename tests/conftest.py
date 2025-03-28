import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app


@pytest.fixture(scope="session")
def event_loop():
    """
    Создаёт новый event loop для асинхронных тестов (scope: session)

    :return: объект asyncio event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def transport():
    """
    Создаёт ASGITransport для тестового клиента с поднятым приложением

    :return: объект ASGITransport
    """
    return ASGITransport(app=app, raise_app_exceptions=True)


@pytest_asyncio.fixture
async def client(transport):
    """
    Асинхронный HTTP-клиент для тестирования приложения

    :return: экземпляр httpx.AsyncClient
    """
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register_user(ac, name, email, password):
    """
    Отправляет запрос на регистрацию нового пользователя

    :param ac: httpx.AsyncClient
    :param name: имя пользователя
    :param email: email пользователя
    :param password: пароль пользователя
    """
    await ac.post("/register", data={"name": name, "email": email, "password": password})


async def login_user(ac, email, password):
    """
    Отправляет запрос на вход и возвращает access token

    :param ac: httpx.AsyncClient
    :param email: email пользователя
    :param password: пароль
    :return: access token из ответа
    """
    response = await ac.post("/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
