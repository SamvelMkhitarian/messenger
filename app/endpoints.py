from typing import List

from auth import (authenticate_user, create_access_token, get_current_user,
                  get_password_hash)
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from models import Chat, Group, Message, User, group_members
from schemas import (ChatCreate, ChatRead, MessageReadSchema, Token,
                     UserCreate, UserRead)
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def register_user(user_data: UserCreate = Query(), db: AsyncSession = Depends(get_db)) -> UserRead:
    """
    Зарегистрировать нового пользователя

    :param user_data: данные пользователя
    :param db: сессия базы данных
    :return: объект созданного пользователя
    """
    # Проверка на дубликат email
    existing_user = (await db.execute(select(User).where(User.email == user_data.email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=400, detail='Email уже зарегистрирован')
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

# Логин и получение JWT


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)) -> Token:
    """
    Авторизовать пользователя и выдать JWT токен

    :param form_data: форма с email и паролем
    :param db: сессия базы данных
    :return: JWT токен и тип токена
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user.id)},
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Создание чата


@router.post("/chats", response_model=ChatRead)
async def create_chat(
    chat_data: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ChatRead:
    """
    Создать новый чат (личный или групповой)

    :param chat_data: данные чата (название, тип)
    :param db: сессия базы данных
    :param current_user: текущий авторизованный пользователь
    :return: объект созданного чата
    """
    new_chat = Chat(name=chat_data.name, type=chat_data.type)
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    # Если это групповой чат — создаём Group и добавляем создателя
    if chat_data.type == "group":
        new_group = Group(name=chat_data.name, creator_id=current_user.id)
        db.add(new_group)
        await db.commit()
        await db.refresh(new_group)
        # Добавляем создателя в участники
        await db.execute(group_members.insert().values(group_id=new_group.id, user_id=current_user.id))
        await db.commit()

    return new_chat

# Подключить пользователя к группе (добавить в group_members)


@router.post("/groups/{group_id}/join")
async def join_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Присоединить пользователя к существующей группе

    :param group_id: идентификатор группы
    :param db: сессия базы данных
    :param current_user: текущий авторизованный пользователь
    :return: результат добавления в группу
    """
    # Проверим, существует ли группа
    group_obj = (await db.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
    if not group_obj:
        raise HTTPException(status_code=404, detail="Group not found")
    # Проверим, не в группе ли уже
    res = await db.execute(
        select(group_members).where(
            and_(group_members.c.group_id == group_id,
                 group_members.c.user_id == current_user.id)
        )
    )
    if res.first():
        return {"detail": "Already in group"}

    await db.execute(group_members.insert().values(group_id=group_id, user_id=current_user.id))
    await db.commit()
    return {"detail": f"User {current_user.id} joined group {group_id}"}


# История сообщений


@router.get("/history/{chat_id}", response_model=List[MessageReadSchema])
async def get_history(
    chat_id: int = Path(..., description='ID чата'),
    limit: int = Query(
        default=50, ge=1, description='максимальное количество сообщений'),
    offset: int = Query(default=0, ge=0, description='смещение для пагинации'),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[MessageReadSchema]:
    """
    Получить историю сообщений в чате

    :param chat_id: идентификатор чата
    :param limit: максимальное количество сообщений
    :param offset: смещение для пагинации
    :param db: сессия базы данных
    :param current_user: текущий авторизованный пользователь
    :return: список сообщений
    """
    # Проверяем существование чата
    chat_obj = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
    if not chat_obj:
        raise HTTPException(status_code=404, detail="Chat not found")

    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.timestamp.asc())
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()
    return messages

# Эндпоинт для наполнения тестовыми данными (по желанию)


@router.post("/seed_data")
async def seed_data(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Создать тестовые данные (пользователи и чат)

    :param db: сессия базы данных
    :return: результат создания данных
    """
    # Создадим пару пользователей
    u1 = User(name="Alice", email="alice@example.com",
              password_hash=get_password_hash("password"))
    u2 = User(name="Bob", email="bob@example.com",
              password_hash=get_password_hash("password"))
    db.add_all([u1, u2])
    await db.commit()
    await db.refresh(u1)
    await db.refresh(u2)

    # Создадим личный чат для Alice и Bob
    chat = Chat(name="Alice&Bob", type="personal")
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    return {"detail": "Test data created"}
