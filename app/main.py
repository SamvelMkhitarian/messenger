from contextlib import asynccontextmanager

import uvicorn
from database import engine
from endpoints import router
from fastapi import FastAPI
from models import Base
from ws_endpoints import ws_router


async def create_tables():
    """
    Создаёт все таблицы в базе данных на основе моделей.
    Используется при старте приложения для инициализации схемы
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекст жизненного цикла приложения.
    При старте вызывает создание таблиц, затем запускает приложение
    """
    await create_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(ws_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
