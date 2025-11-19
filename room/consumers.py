# room/consumers.py
import json
from collections import defaultdict

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import ChatMessage

# set(usernames)
ROOM_USERS = defaultdict(set)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = None
        self.rooms = set()  
        await self.accept()

    async def disconnect(self, close_code):
        # list update when leave
        for room in list(self.rooms):
            await self._leave_room(room)

    async def receive(self, text_data):
        data = json.loads(text_data)
        etype = data.get("type", "message")

        #  JOIN any specific room
        if etype == "join":
            room = data["room"]
            self.username = data.get("username") or self.username or "Anonymous"
            await self._join_room(room)

        # LEAVE specific room
        elif etype == "leave_room":
            room = data["room"]
            await self._leave_room(room)

        #  MESSAGE specific room
        elif etype == "message":
            room = data["room"]
            message = data.get("message", "")
            username = data.get("username", self.username or "Anonymous")

            # DB save
            await self.save_message(room, username, message)

            await self.channel_layer.group_send(
                self._group_name(room),
                {
                    "type": "chat_message",
                    "room": room,
                    "message": message,
                    "username": username,
                },
            )

        # TYPING specific room
        elif etype == "typing":
            room = data["room"]
            is_typing = data.get("is_typing", False)
            username = data.get("username", self.username or "Anonymous")

            await self.channel_layer.group_send(
                self._group_name(room),
                {
                    "type": "typing",
                    "room": room,
                    "username": username,
                    "is_typing": is_typing,
                },
            )

    def _group_name(self, room: str) -> str:
        return f"chat_{room}"

    async def _join_room(self, room: str):
        if room in self.rooms:
            return  # already in room

        self.rooms.add(room)
        await self.channel_layer.group_add(self._group_name(room), self.channel_name)

        # send history to client only
        history = await self.get_last_messages(room, limit=30)
        for msg in history:
            await self.send(text_data=json.dumps({
                "type": "message",
                "room": room,
                "username": msg.username,
                "message": msg.message,
                "history": True,
            }))

        # online users update
        ROOM_USERS[room].add(self.username)

        await self.channel_layer.group_send(
            self._group_name(room),
            {
                "type": "users_update",
                "room": room,
                "users": sorted(ROOM_USERS[room]),
            },
        )

        # system join message
        await self.channel_layer.group_send(
            self._group_name(room),
            {
                "type": "system_message",
                "room": room,
                "message": f"{self.username} joined {room}.",
            },
        )

    async def _leave_room(self, room: str):
        if room not in self.rooms:
            return

        self.rooms.remove(room)
        await self.channel_layer.group_discard(self._group_name(room), self.channel_name)

        users = ROOM_USERS.get(room, set())
        if self.username in users:
            users.remove(self.username)
        if users:
            ROOM_USERS[room] = users
        else:
            ROOM_USERS.pop(room, None)

        # online list update
        await self.channel_layer.group_send(
            self._group_name(room),
            {
                "type": "users_update",
                "room": room,
                "users": sorted(users),
            },
        )

        # system message
        await self.channel_layer.group_send(
            self._group_name(room),
            {
                "type": "system_message",
                "room": room,
                "message": f"{self.username} left {room}.",
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "message",
            "room": event["room"],
            "username": event["username"],
            "message": event["message"],
        }))

    async def users_update(self, event):
        users = event["users"]
        await self.send(text_data=json.dumps({
            "type": "users_update",
            "room": event["room"],
            "users": users,
            "count": len(users),
        }))

    async def system_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "message",
            "room": event["room"],
            "username": "System",
            "message": event["message"],
        }))

    async def typing(self, event):
        await self.send(text_data=json.dumps({
            "type": "typing",
            "room": event["room"],
            "username": event["username"],
            "is_typing": event["is_typing"],
        }))

    @database_sync_to_async
    def save_message(self, room, username, message):
        return ChatMessage.objects.create(
            room_name=room,
            username=username,
            message=message,
        )

    @database_sync_to_async
    def get_last_messages(self, room, limit=30):
        qs = ChatMessage.objects.filter(room_name=room).order_by("-created_at")[:limit]
        return list(qs[::-1])  # old -> new
