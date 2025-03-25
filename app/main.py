from contextlib import asynccontextmanager

import uvicorn
from database import Base, engine
from endpoints import router
from fastapi import FastAPI
from ws_endpoints import ws_router


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(ws_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
