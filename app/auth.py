import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from database import get_db_session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from models import User
from schemas import TokenData
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

SECRET_KEY = os.getenv("SECRET_KEY", "SECRET_KEY_FOR_DEMO")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
oauth2_scheme = HTTPBearer()


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


async def authenticate_user(email: str, password: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta  # TODO изменить метод на актуальный
    else:
        # TODO изменить метод на актуальный
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()
    except JWTError:
        return None
