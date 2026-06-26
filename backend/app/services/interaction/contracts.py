"""Interaction entry result contract guard."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

INTERACTION_SEND_VIA = {"interaction_bot", "userbot_reply", "bbot_notice"}
INTERACTION_BUTTON_CHANNELS = {"interaction_bot", "bbot_notice"}

WriteLog = Callable[[str, str], Awaitable[None]]
EntryManifestResolver = Callable[[str | None, str | None], dict[str, Any] | None]


def action_send_via(action: dict[str, Any]) -> str:
    send_via = str(action.get("send_via") or "interaction_bot").strip()
    return send_via if send_via in INTERACTION_SEND_VIA else "interaction_bot"


async def guard_interaction_actions(
    *,
    rule: dict[str, Any],
    actions: list[dict[str, Any]],
    resolve_entry_manifest: EntryManifestResolver,
    write_log: Callable[..., Awaitable[None]],
    log_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Apply ``result_contract`` limits before actions reach delivery."""

    contract = _entry_result_contract(rule, resolve_entry_manifest)
    raw_actions = contract.get("actions")
    allowed_actions = (
        {str(item or "").strip() for item in raw_actions if str(item or "").strip()}
        if isinstance(raw_actions, list)
        else set()
    )
    raw_send_via = contract.get("send_via")
    allowed_send_via = (
        {str(item or "").strip() for item in raw_send_via if str(item or "").strip() in INTERACTION_SEND_VIA}
        if isinstance(raw_send_via, list)
        else set()
    ) or {"interaction_bot"}
    context = dict(log_context or {})
    guarded: list[dict[str, Any]] = []
    for raw_action in actions:
        if not isinstance(raw_action, dict):
            continue
        action = dict(raw_action)
        action_type = str(action.get("type") or "").strip()
        if allowed_actions and action_type not in allowed_actions:
            await write_log(
                "warn",
                f"interaction action blocked by result_contract.actions: {action_type}",
                action_type=action_type,
                allowed_actions=sorted(allowed_actions),
                **context,
            )
            continue
        if action_type in {"send_message", "send_photo", "send_file", "delete_message", "pin_message"}:
            send_via = action_send_via(action)
            if send_via not in allowed_send_via:
                await write_log(
                    "warn",
                    f"interaction action blocked by result_contract.send_via: {send_via}",
                    action_type=action_type,
                    send_via=send_via,
                    allowed_send_via=sorted(allowed_send_via),
                    **context,
                )
                continue
            action["send_via"] = send_via
            if send_via not in INTERACTION_BUTTON_CHANNELS and "reply_markup" in action:
                action.pop("reply_markup", None)
                await write_log(
                    "info",
                    "interaction action reply_markup stripped for non-bot channel",
                    action_type=action_type,
                    send_via=send_via,
                    **context,
                )
        guarded.append(action)
    return guarded


def _entry_result_contract(
    rule: dict[str, Any],
    resolve_entry_manifest: EntryManifestResolver,
) -> dict[str, Any]:
    module_key = str(rule.get("module_key") or "").strip() or None
    entry_key = str(rule.get("module_action") or "").strip() or None
    entry = resolve_entry_manifest(module_key, entry_key)
    contract = entry.get("result_contract") if isinstance(entry, dict) else None
    return dict(contract) if isinstance(contract, dict) else {}


__all__ = [
    "INTERACTION_BUTTON_CHANNELS",
    "INTERACTION_SEND_VIA",
    "action_send_via",
    "guard_interaction_actions",
]
