import json
from typing import Dict

from auth import get_current_user_ws
from database import get_db_session
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from ws_queries import (fetch_last_messages, mark_message_as_read,
                        save_new_message)

ws_router = APIRouter()
active_connections: Dict[int, set[WebSocket]] = {}


@ws_router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, token: str) -> None:
    """
    Обработчик WebSocket-соединения для чата.
    Осуществляет:
    - аутентификацию пользователя;
    - отправку последних сообщений;
    - приём новых сообщений и их рассылку;
    - отметку сообщений как прочитанных.

    :param websocket: объект WebSocket-соединения
    :param chat_id: идентификатор чата
    :param token: JWT токен пользователя
    :return: None
    """
    db_gen = get_db_session()
    db: AsyncSession = await anext(db_gen)
    try:
        user = await get_current_user_ws(token, db)
        if user is None:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        active_connections.setdefault(chat_id, set()).add(websocket)

        messages = await fetch_last_messages(chat_id, db)
        await websocket.send_text(json.dumps([msg.model_dump() for msg in messages], default=str))

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "message_read":
                message_id = data.get("message_id")
                if message_id:
                    await mark_message_as_read(user.id, message_id, db)
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

                message = await save_new_message(chat_id, user, text, client_id, db)
                if message:
                    response_data = {
                        "type": "new_message",
                        "message": message.model_dump(),
                    }
                    for conn in active_connections.get(chat_id, set()):
                        await conn.send_text(json.dumps(response_data, default=str))

    except WebSocketDisconnect:
        active_connections.get(chat_id, set()).discard(websocket)
    finally:
        await db_gen.aclose()
