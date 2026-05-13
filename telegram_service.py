import asyncio
import random
from dataclasses import dataclass
from typing import List, Optional

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.messages import SendReactionRequest, SetTypingRequest
from telethon.tl.types import SendMessageTypingAction, ReactionEmoji

from config import APP_API_HASH, APP_API_ID


class TelegramServiceError(Exception):
    pass


@dataclass
class DialogSummary:
    peer_id: int
    title: str
    username: Optional[str]


@dataclass
class MessageSummary:
    msg_id: int
    sender_id: Optional[int]
    text: str
    date_iso: str


class TelegramService:
    """
    Thin API wrapper with reusable methods for future apps (e.g. userbot).
    """

    def __init__(self, session_name: str = "hotbot_session") -> None:
        self.client = TelegramClient(session_name, APP_API_ID, APP_API_HASH)

    async def connect(self) -> None:
        await self.client.start()

    async def disconnect(self) -> None:
        await self.client.disconnect()

    async def list_dialogs(self, limit: int = 20) -> List[DialogSummary]:
        dialogs = []
        async for dialog in self.client.iter_dialogs(limit=limit):
            entity = dialog.entity
            username = getattr(entity, "username", None)
            dialogs.append(
                DialogSummary(
                    peer_id=entity.id,
                    title=dialog.name,
                    username=username,
                )
            )
        return dialogs

    async def resolve_entity(self, target: str):
        try:
            return await self.client.get_entity(target)
        except Exception as exc:  # noqa: BLE001
            raise TelegramServiceError(f"Could not resolve target: {target}") from exc

    async def send_message(self, target: str, text: str) -> None:
        entity = await self.resolve_entity(target)
        await self._human_pause()
        try:
            await self.client.send_message(entity, text)
        except FloodWaitError as exc:
            raise TelegramServiceError(f"Flood wait. Try again in {exc.seconds}s") from exc
        except RPCError as exc:
            raise TelegramServiceError(f"Telegram RPC error: {exc}") from exc

    async def get_recent_messages(self, target: str, limit: int = 20) -> List[MessageSummary]:
        entity = await self.resolve_entity(target)
        messages = await self.client.get_messages(entity, limit=limit)
        output: List[MessageSummary] = []
        for message in reversed(messages):
            text = (message.message or "").strip()
            output.append(
                MessageSummary(
                    msg_id=message.id,
                    sender_id=message.sender_id,
                    text=text,
                    date_iso=message.date.isoformat(),
                )
            )
        return output

    async def set_typing(self, target: str, seconds: int = 3) -> None:
        entity = await self.resolve_entity(target)
        seconds = max(1, min(seconds, 8))
        try:
            await self.client(SetTypingRequest(peer=entity, action=SendMessageTypingAction()))
            await asyncio.sleep(seconds)
        except RPCError as exc:
            raise TelegramServiceError(f"Could not set typing status: {exc}") from exc

    async def react_to_message(self, target: str, msg_id: int, emoji: str) -> None:
        entity = await self.resolve_entity(target)
        try:
            await self.client(
                SendReactionRequest(
                    peer=entity,
                    msg_id=msg_id,
                    reaction=[ReactionEmoji(emoticon=emoji)],
                    add_to_recent=True,
                )
            )
        except RPCError as exc:
            raise TelegramServiceError(f"Could not react to message: {exc}") from exc

    async def _human_pause(self) -> None:
        """
        Small random delay to avoid suspicious machine-like cadence.
        """
        await asyncio.sleep(random.uniform(0.8, 2.2))
