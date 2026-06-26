"""Message operation facade exposed to plugins.

The facade does not expose Telegram clients or bot tokens. In interaction
entry calls it buffers platform-standard actions; the main process later
executes those actions through the existing controlled delivery path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MessageChannel = Literal["interaction_bot", "userbot_reply", "bbot_notice"]


@dataclass
class BufferedMessageOps:
    actions: list[dict[str, Any]] = field(default_factory=list)

    async def send(
        self,
        *,
        channel: MessageChannel = "interaction_bot",
        chat_id: int | None = None,
        text: str,
        reply_to_message_id: int | None = None,
        reply_markup: dict[str, Any] | None = None,
        save_message_id_key: str | None = None,
        pin: bool = False,
    ) -> dict[str, Any]:
        action: dict[str, Any] = {
            "type": "send_message",
            "send_via": channel,
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to_message_id,
        }
        if reply_markup is not None:
            action["reply_markup"] = dict(reply_markup)
        if save_message_id_key:
            action["save_message_id_key"] = save_message_id_key
        if pin:
            action["pin"] = True
        self.actions.append(action)
        return action

    async def edit(
        self,
        *,
        channel: MessageChannel = "interaction_bot",
        chat_id: int | None = None,
        message_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        action: dict[str, Any] = {
            "type": "send_message",
            "send_via": channel,
            "chat_id": chat_id,
            "edit_message_id": message_id,
            "text": text,
        }
        if reply_markup is not None:
            action["reply_markup"] = dict(reply_markup)
        self.actions.append(action)
        return action

    async def delete(
        self,
        *,
        channel: MessageChannel = "interaction_bot",
        chat_id: int | None = None,
        message_id: int,
    ) -> dict[str, Any]:
        action = {
            "type": "delete_message",
            "send_via": channel,
            "chat_id": chat_id,
            "message_id": message_id,
        }
        self.actions.append(action)
        return action

    async def pin(
        self,
        *,
        channel: MessageChannel = "interaction_bot",
        chat_id: int | None = None,
        message_id: int,
    ) -> dict[str, Any]:
        action = {
            "type": "pin_message",
            "send_via": channel,
            "chat_id": chat_id,
            "message_id": message_id,
        }
        self.actions.append(action)
        return action

    async def answer_callback(
        self,
        *,
        callback_query_id: str | None,
        text: str = "",
        show_alert: bool = False,
    ) -> dict[str, Any]:
        action = {
            "type": "answer_callback",
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        }
        self.actions.append(action)
        return action


__all__ = ["BufferedMessageOps", "MessageChannel"]
