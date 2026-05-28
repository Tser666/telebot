"""交互 Bot 服务 façade：统一复用 account_bot_service 实现。"""

from __future__ import annotations

from .account_bot_service import (
    TRANSFER_NOTICE_SETTING_PREFIX,
    VALID_AMOUNT_MATCH_MODES,
    VALID_CONCURRENCY,
    VALID_TRIGGER_MODES,
    default_transfer_notice_config,
    get_interaction_bot_config,
    get_interaction_bot_token,
    get_transfer_bot_token,
    get_transfer_notice_config,
    normalize_interaction_rules,
    normalize_transfer_notice_config,
    transfer_notice_setting_key,
    update_interaction_bot_config,
    update_transfer_notice_config,
)

__all__ = [
    "TRANSFER_NOTICE_SETTING_PREFIX",
    "VALID_TRIGGER_MODES",
    "VALID_AMOUNT_MATCH_MODES",
    "VALID_CONCURRENCY",
    "transfer_notice_setting_key",
    "default_transfer_notice_config",
    "normalize_transfer_notice_config",
    "normalize_interaction_rules",
    "get_transfer_notice_config",
    "get_interaction_bot_config",
    "update_transfer_notice_config",
    "update_interaction_bot_config",
    "get_interaction_bot_token",
    "get_transfer_bot_token",
]
