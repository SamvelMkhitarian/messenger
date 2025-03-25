from typing import Dict, List

from database import get_db
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from models import Chat, Group, Message, MessageRead, group_members
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

ws_router = APIRouter()

# Храним активные WebSocket-соединения.
# Ключ: chat_id, значение: список активных соединений (для всех юзеров).
active_connections: Dict[int, List[WebSocket]] = {}


@ws_router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, db: AsyncSession = Depends(get_db)):
    await websocket.accept()

    if chat_id not in active_connections:
        active_connections[chat_id] = []
    active_connections[chat_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            sender_id = data.get("sender_id")
            text = data.get("text", "")
            # клиентский UUID для исключения дубликатов
            message_id = data.get("message_id")
            if action == "send_message":
                # Сохраняем сообщение в БД (проверка дубликатов)
                # Если message_id не пуст, можно добавить unique_constraint и проверять
                msg = Message(chat_id=chat_id, sender_id=sender_id, text=text)
                db.add(msg)
                await db.commit()
                await db.refresh(msg)

                # Рассылаем сообщение всем подключённым сокетам в данном чате
                for conn in active_connections[chat_id]:
                    await conn.send_json({
                        "type": "new_message",
                        "message": {
                            "id": msg.id,
                            "chat_id": chat_id,
                            "sender_id": sender_id,
                            "text": text,
                            "timestamp": str(msg.timestamp),
                            "is_read": msg.is_read
                        }
                    })
            elif action == "read_message":
                # Пользователь прочитал сообщение
                msg_id = data.get("msg_id")
                # Обновляем статус чтения (если это личный чат — сразу True, если групповой — нужно проверить всех участников)
                message_obj = (await db.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
                if message_obj:
                    # Логика сохранения в таблицу MessageRead
                    read_record = MessageRead(
                        message_id=message_obj.id, user_id=sender_id)
                    db.add(read_record)
                    await db.commit()

                    # Проверим, это чат групповой или личный
                    chat_obj = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
                    if chat_obj.type == "personal":
                        # Сразу ставим is_read = True
                        message_obj.is_read = True
                        await db.commit()
                        # Отправляем уведомление о прочтении всем
                        for conn in active_connections[chat_id]:
                            await conn.send_json({
                                "type": "read_receipt",
                                "message_id": msg_id,
                                "by_user": sender_id,
                                "all_read": True
                            })
                    else:
                        # Если групповой: проверяем, все ли участники прочитали
                        group_obj = (await db.execute(select(Group).where(Group.name == chat_obj.name))).scalar_one_or_none()
                        if group_obj:
                            # Найдём всех участников группы
                            res = await db.execute(select(group_members.c.user_id).where(group_members.c.group_id == group_obj.id))
                            all_user_ids = [row[0] for row in res.fetchall()]
                            # Проверяем, сколько человек прочитали
                            res2 = await db.execute(select(MessageRead).where(MessageRead.message_id == msg_id))
                            read_rows = res2.scalars().all()
                            read_user_ids = [r.user_id for r in read_rows]

                            # Если все участники есть в read_user_ids
                            if all(uid in read_user_ids for uid in all_user_ids):
                                # Помечаем сообщение как прочитанное
                                message_obj.is_read = True
                                await db.commit()
                                for conn in active_connections[chat_id]:
                                    await conn.send_json({
                                        "type": "read_receipt",
                                        "message_id": msg_id,
                                        "by_user": sender_id,
                                        "all_read": True
                                    })
                            else:
                                # Частично прочитано
                                for conn in active_connections[chat_id]:
                                    await conn.send_json({
                                        "type": "read_receipt",
                                        "message_id": msg_id,
                                        "by_user": sender_id,
                                        "all_read": False
                                    })
    except WebSocketDisconnect:
        active_connections[chat_id].remove(websocket)
