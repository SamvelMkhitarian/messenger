from typing import Any

from auth import get_current_user
from database import get_db_session
from fastapi import APIRouter, Depends, Form, Path, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from models import User
from queries import (create_chat_query, create_seed_data_query,
                     get_history_query, get_user_chats_query, join_group_query,
                     login_query, register_user_query)
from schemas import ChatCreate, MessageWithSender, Token, UserRead
from sqlalchemy.ext.asyncio import AsyncSession
from utils import validate_password

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
) -> UserRead:
    """
    Зарегистрировать нового пользователя

    :param user_data: данные пользователя
    :param db: сессия базы данных
    :return: объект созданного пользователя
    """
    validate_password(password)
    return await register_user_query(name, email, password, db)


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session)
) -> Token:
    """
    Авторизовать пользователя и выдать JWT токен

    :param form_data: форма с email и паролем
    :param db: сессия базы данных
    :return: JWT токен и тип токена
    """
    return await login_query(form_data, db)


@router.post("/create_chats", status_code=status.HTTP_200_OK)
async def create_chat(
    chat_data: ChatCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Создать новый чат (личный или групповой)

    :param chat_data: данные чата (название, тип)
    :param db: сессия базы данных
    :param current_user: текущий пользователь
    :return: данные созданного чата + group_id (если это групповой чат)
    """
    return await create_chat_query(chat_data, db, current_user)


@router.get("/get_chats", status_code=status.HTTP_200_OK)
async def get_user_chats(
    db: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_user)
) -> list[dict[str, Any]]:
    """
    Получить список чатов, в которых участвует текущий пользователь.

    :param db: сессия базы данных
    :param current_user: текущий авторизованный пользователь
    :return: список чатов
    """
    return await get_user_chats_query(db, current_user)


@router.post("/groups/{group_id}/join", status_code=status.HTTP_200_OK)
async def join_group(
    group_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Присоединить пользователя к существующей группе

    :param group_id: идентификатор группы
    :param db: сессия базы данных
    :param current_user: текущий авторизованный пользователь
    :return: результат добавления в группу
    """
    return await join_group_query(group_id, db, current_user)


@router.get(
    "/history/{chat_id}", response_model=list[MessageWithSender], status_code=status.HTTP_200_OK
)
async def get_history(
    chat_id: int = Path(..., description="ID чата"),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[MessageWithSender]:
    """
    Получить историю сообщений в заданном чате.

    :param chat_id: идентификатор чата
    :param limit: максимальное количество сообщений
    :param offset: смещение (для пагинации)
    :param db: сессия базы данных
    :return: список сообщений (MessageWithSender)
    """
    return await get_history_query(chat_id, limit, offset, db)


@router.post("/seed_data", status_code=status.HTTP_204_NO_CONTENT)
async def seed_data(db: AsyncSession = Depends(get_db_session)) -> None:
    """
    Создать тестовые данные (пользователи и чат)

    :param db: сессия базы данных
    """
    return await create_seed_data_query(db)
