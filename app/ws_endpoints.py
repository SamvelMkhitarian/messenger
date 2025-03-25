from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from typing import Dict, List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Chat, Group, Message, MessageRead, group_members
from settings import SECRET_KEY, ALGORITHM

ws_router = APIRouter()

active_connections: Dict[int, List[WebSocket]] = {}


@ws_router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, token: Optional[str] = None):
    """
    Подключение к чату по WebSocket с авторизацией через JWT (token в query).
    Обрабатывает отправку и чтение сообщений в реальном времени.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    if chat_id not in active_connections:
        active_connections[chat_id] = []
    active_connections[chat_id].append(websocket)

    async with get_db() as db:
        try:
            while True:
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "send_message":
                    text = data.get("text", "")
                    client_id = data.get("client_id")

                    # Проверка дубликата по client_id
                    if client_id:
                        existing = await db.execute(
                            select(Message).where(
                                Message.client_id == client_id)
                        )
                        if existing.scalar_one_or_none():
                            continue  # сообщение уже есть — не сохраняем

                    msg = Message(
                        chat_id=chat_id,
                        sender_id=user_id,
                        text=text,
                        client_id=client_id
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)

                    for conn in active_connections[chat_id]:
                        await conn.send_json({
                            "type": "new_message",
                            "message": {
                                "id": msg.id,
                                "chat_id": chat_id,
                                "sender_id": user_id,
                                "text": msg.text,
                                "timestamp": str(msg.timestamp),
                                "is_read": msg.is_read
                            }
                        })

                elif action == "read_message":
                    msg_id = data.get("msg_id")
                    result = await db.execute(select(Message).where(Message.id == msg_id))
                    message_obj = result.scalar_one_or_none()
                    if not message_obj:
                        continue

                    db.add(MessageRead(message_id=message_obj.id, user_id=user_id))
                    await db.commit()

                    result = await db.execute(select(Chat).where(Chat.id == chat_id))
                    chat_obj = result.scalar_one_or_none()

                    if chat_obj.type == "personal":
                        message_obj.is_read = True
                        await db.commit()
                        for conn in active_connections[chat_id]:
                            await conn.send_json({
                                "type": "read_receipt",
                                "message_id": msg_id,
                                "by_user": user_id,
                                "all_read": True
                            })
                    else:
                        group_result = await db.execute(
                            select(Group).where(Group.name == chat_obj.name)
                        )
                        group_obj = group_result.scalar_one_or_none()
                        members_result = await db.execute(
                            select(group_members.c.user_id).where(
                                group_members.c.group_id == group_obj.id)
                        )
                        all_user_ids = [row[0]
                                        for row in members_result.fetchall()]
                        reads_result = await db.execute(
                            select(MessageRead).where(
                                MessageRead.message_id == msg_id)
                        )
                        read_user_ids = [
                            r.user_id for r in reads_result.scalars().all()]
                        all_read = all(
                            uid in read_user_ids for uid in all_user_ids)

                        if all_read:
                            message_obj.is_read = True
                            await db.commit()

                        for conn in active_connections[chat_id]:
                            await conn.send_json({
                                "type": "read_receipt",
                                "message_id": msg_id,
                                "by_user": user_id,
                                "all_read": all_read
                            })

        except WebSocketDisconnect:
            active_connections[chat_id].remove(websocket)
