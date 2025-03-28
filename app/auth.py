from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from database import get_db_session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from models import User
from schemas import TokenData
from settings import ALGORITHM, SECRET_KEY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

ACCESS_TOKEN_EXPIRE_MINUTES = 120
oauth2_scheme = HTTPBearer()


def get_password_hash(password: str) -> str:
    """
    Хеширует пароль с использованием bcrypt

    :param password: исходный пароль в виде строки
    :return: захешированный пароль в виде строки
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие введённого пароля и хеша

    :param plain_password: введённый пароль
    :param hashed_password: сохранённый хеш пароля
    :return: True, если пароль совпадает, иначе False
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


async def authenticate_user(email: str, password: str, db: AsyncSession):
    """
    Проверяет существование пользователя и валидность пароля

    :param email: email пользователя
    :param password: введённый пароль
    :param db: сессия базы данных
    :return: объект пользователя при успешной аутентификации, иначе None
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создаёт JWT access токен с указанием срока действия

    :param data: данные, которые нужно зашифровать в токен (например, user_id)
    :param expires_delta: опциональный параметр для настройки времени истечения
    :return: закодированный JWT токен
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получить текущего авторизованного пользователя по JWT токену

    :param credentials: заголовок Authorization с Bearer токеном
    :param db: сессия базы данных
    :return: объект пользователя
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = str(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=int(user_id))
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_ws(token: str, db: AsyncSession) -> Optional[User]:
    """
    Получает текущего пользователя по JWT токену из WebSocket-соединения

    :param token: JWT токен
    :param db: сессия базы данных
    :return: объект пользователя или None, если токен недействителен
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()
    except JWTError:
        return None
