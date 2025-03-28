import re
import uuid

from fastapi import HTTPException


def generate_unique_message_id() -> str:
    """
    Генерирует уникальный идентификатор сообщения (UUID v4)

    :return: строка с уникальным UUID
    """
    return str(uuid.uuid4())


def validate_password(password: str) -> None:
    if len(password) < 6:
        raise HTTPException(
            status_code=422, detail="Пароль должен содержать минимум 6 символов")
    if len(password) > 64:
        raise HTTPException(status_code=422, detail="Пароль слишком длинный")
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=422, detail="Пароль должен содержать хотя бы одну заглавную букву")
    if not re.search(r'\d', password):
        raise HTTPException(
            status_code=422, detail="Пароль должен содержать хотя бы одну цифру")
