import os
import sys

sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../app')))
import asyncio  # noqa

import pytest  # noqa
import pytest_asyncio  # noqa
from httpx import ASGITransport, AsyncClient  # noqa

from app.main import app  # noqa


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def transport():
    return ASGITransport(app=app, raise_app_exceptions=True)


@pytest_asyncio.fixture
async def client(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register_user(ac, name, email, password):
    await ac.post("/register", data={"name": name, "email": email, "password": password})


async def login_user(ac, email, password):
    response = await ac.post("/login", data={"username": email, "password": password})
    return response.json()["access_token"]
