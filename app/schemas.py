from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Данные для создания пользователя."""
    name: str
    email: EmailStr
    password: str


class UserRead(BaseModel):
    """Данные пользователя, возвращаемые клиенту."""
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class ChatCreate(BaseModel):
    """Данные для создания чата (личного или группового)."""
    name: str
    type: str  # personal / group


class ChatRead(BaseModel):
    """Информация о чате."""
    id: int
    name: str
    type: str

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(BaseModel):
    """Данные для создания группы."""
    name: str


class MessageBase(BaseModel):
    """Базовая структура сообщения."""
    text: str


class MessageWithSender(BaseModel):
    """Сообщение вместе с информацией об отправителе."""
    id: int
    chat_id: int
    sender_id: int
    sender_name: str
    text: str
    timestamp: datetime
    is_read: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT-токен для авторизации."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Декодированные данные токена (ID пользователя)."""
    user_id: Optional[int] = None
