from typing import List, Any

from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from database import get_db_session
from fastapi import APIRouter, Depends, Form, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from models import Chat, Group, Message, User, group_members
from schemas import ChatCreate, MessageWithSender, Token, UserRead
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


async def register_user_query(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
) -> UserRead:
    """
    Регистрирует нового пользователя и возвращает модель UserRead.
    """
    existing_user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    new_user = User(name=name, email=email, password_hash=get_password_hash(password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def login_query(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session)
) -> Token:
    """
    Авторизует пользователя и возвращает модель Token.
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user.id)},
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def create_chat_query(
    chat_data: ChatCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Создаёт чат (личный или групповой) и возвращает словарь с chat_id и при необходимости group_id.
    """
    new_chat = Chat(name=chat_data.name, type=chat_data.type)
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)

    response = {
        "chat_id": new_chat.id,
        "name": new_chat.name,
        "type": new_chat.type,
    }

    if chat_data.type == "group":
        new_group = Group(name=chat_data.name, creator_id=current_user.id)
        db.add(new_group)
        await db.commit()
        await db.refresh(new_group)
        await db.execute(
            group_members.insert().values(group_id=new_group.id, user_id=current_user.id)
        )
        await db.commit()
        response["group_id"] = new_group.id

    return response


async def get_user_chats_query(
    db: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_user)
) -> list[dict[str, Any]]:
    """
    Возвращает список чатов, в которых участвует текущий пользователь.
    """
    stmt = (
        select(Chat)
        .select_from(Chat)
        .join(group_members, group_members.c.group_id == Chat.id, isouter=True)
        .where((Chat.type == "private") | (group_members.c.user_id == current_user.id))
    )

    result = await db.execute(stmt)
    chats = result.scalars().all()

    return [{"id": chat.id, "name": chat.name, "type": chat.type} for chat in chats]


async def join_group_query(
    group_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Добавляет текущего пользователя в указанную группу и возвращает информацию о результате.
    """
    # Проверим, существует ли группа
    group_obj = (await db.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
    if not group_obj:
        raise HTTPException(status_code=404, detail="Группа не найдена.")
    # Проверим, не в группе ли уже
    res = await db.execute(
        select(group_members).where(
            and_(group_members.c.group_id == group_id, group_members.c.user_id == current_user.id)
        )
    )
    if res.first():
        return {"detail": "Пользователь уже находится в группе."}

    await db.execute(group_members.insert().values(group_id=group_id, user_id=current_user.id))
    await db.commit()
    return {"detail": f"Пользователь {current_user.id} присоединился к группе {group_id}"}


async def get_history_query(
    chat_id: int = Path(..., description="ID чата"),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> List[MessageWithSender]:
    """
    Возвращает сообщения из чата с учётом limit/offset либо поднимает 404, если чата нет.
    """
    # Проверяем существование чата
    chat_obj = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
    if not chat_obj:
        raise HTTPException(status_code=404, detail="Чат не найден")

    result = await db.execute(
        select(Message, User.name)
        .join(User, User.id == Message.sender_id)
        .where(Message.chat_id == chat_id)
        .order_by(Message.timestamp.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()

    return [
        MessageWithSender(
            id=msg.id,
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            sender_name=user_name,
            text=msg.text,
            timestamp=msg.timestamp,
            is_read=msg.is_read,
        )
        for msg, user_name in rows
    ]


async def create_seed_data_query(db: AsyncSession) -> None:
    """
    Создаёт тестовых пользователей и чат, не возвращая данные.
    """
    u1 = User(name="Alice", email="alice@example.com", password_hash=get_password_hash("password"))
    u2 = User(name="Bob", email="bob@example.com", password_hash=get_password_hash("password"))
    db.add_all([u1, u2])
    await db.commit()
    await db.refresh(u1)
    await db.refresh(u2)

    chat = Chat(name="Alice&Bob", type="personal")
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
