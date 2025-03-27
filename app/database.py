from contextlib import asynccontextmanager

from settings import DATABASE_URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
