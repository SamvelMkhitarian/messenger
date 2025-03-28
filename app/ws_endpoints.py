import json
from typing import Dict

from auth import get_current_user_ws
from database import get_db_session
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models import Message, MessageRead, User
from schemas import MessageWithSender
from sqlalchemy import join, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

ws_router = APIRouter()
active_connections: Dict[int, set[WebSocket]] = {}


@ws_router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, token: str) -> None:
    db_gen = get_db_session()
    db: AsyncSession = await anext(db_gen)
    try:
        user = await get_current_user_ws(token, db)
        if user is None:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        active_connections.setdefault(chat_id, set()).add(websocket)

        result = await db.execute(
            select(
                Message.id,
                Message.chat_id,
                Message.sender_id,
                User.name.label("sender_name"),
                Message.text,
                Message.timestamp,
                Message.is_read,
            )
            .select_from(join(Message, User, Message.sender_id == User.id))
            .where(Message.chat_id == chat_id)
            .order_by(Message.timestamp.asc())
            .limit(50)
        )
        messages = [
            MessageWithSender(
                id=row.id,
                chat_id=row.chat_id,
                sender_id=row.sender_id,
                sender_name=row.sender_name,
                text=row.text,
                timestamp=row.timestamp,
                is_read=row.is_read,
            )
            for row in result
        ]
        await websocket.send_text(json.dumps([msg.model_dump() for msg in messages], default=str))

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "message_read":
                message_id = data.get("message_id")
                if message_id:
                    stmt = (
                        insert(MessageRead)
                        .values(user_id=user.id, message_id=message_id)
                        .on_conflict_do_nothing()
                    )
                    await db.execute(stmt)
                    await db.commit()

                    for conn in active_connections.get(chat_id, set()):
                        await conn.send_text(
                            json.dumps({
                                "type": "message_read",
                                "message_id": message_id,
                                "reader_id": user.id,
                            })
                        )

            elif event_type == "new_message":
                text = data.get("text")
                client_id = data.get("client_id")
                if not text or not client_id:
                    continue

                existing = await db.execute(select(Message).where(Message.client_id == client_id))
                if existing.scalar_one_or_none():
                    continue

                new_msg = Message(
                    chat_id=chat_id,
                    sender_id=user.id,
                    text=text,
                    client_id=client_id,
                )
                db.add(new_msg)
                await db.commit()
                await db.refresh(new_msg)

                response_data = {
                    "type": "new_message",
                    "message": MessageWithSender(
                        id=new_msg.id,
                        chat_id=new_msg.chat_id,
                        sender_id=new_msg.sender_id,
                        sender_name=user.name,
                        text=new_msg.text,
                        timestamp=new_msg.timestamp,
                        is_read=new_msg.is_read,
                    ).model_dump(),
                }

                for conn in active_connections.get(chat_id, set()):
                    await conn.send_text(json.dumps(response_data, default=str))

    except WebSocketDisconnect:
        active_connections.get(chat_id, set()).discard(websocket)
    finally:
        await db_gen.aclose()
