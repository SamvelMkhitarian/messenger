from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserRead(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        orm_mode = True


class ChatCreate(BaseModel):
    name: str
    type: str  # personal / group


class ChatRead(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        orm_mode = True


class GroupCreate(BaseModel):
    name: str


class MessageBase(BaseModel):
    text: str


class MessageReadSchema(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    timestamp: datetime
    is_read: bool

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
