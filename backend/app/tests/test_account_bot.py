"""账号绑定 Bot 联动系统的关键安全单测。"""

from __future__ import annotations

from app.crypto import encrypt_str
from app.db.models.account_bot import AccountBot
from app.schemas.account_bot import AccountBotConfigUpdate
from app.services import account_bot_runtime, account_bot_service


def test_account_bot_config_response_hides_plain_token() -> None:
    """配置出参只暴露 has_token，不返回明文 token 或加密串。"""

    row = AccountBot(account_id=1, bot_token_enc=encrypt_str("123456:secret-token"))
    out = account_bot_service.config_to_response(row)

    assert out.has_token is True
    assert "token" not in out.model_dump()


def test_account_bot_role_matrix() -> None:
    """viewer/operator/admin 权限必须逐级包含。"""

    assert account_bot_service.role_allows("viewer", "viewer") is True
    assert account_bot_service.role_allows("viewer", "operator") is False
    assert account_bot_service.role_allows("operator", "viewer") is True
    assert account_bot_service.role_allows("operator", "admin") is False
    assert account_bot_service.role_allows("admin", "operator") is True


def test_account_bot_callback_data_parser() -> None:
    """callback data 必须绑定 aid/action/resource/nonce。"""

    assert account_bot_runtime._parse_callback("ab:12:feature_toggle:game24") == (
        12,
        "feature_toggle",
        "game24",
        None,
    )
    assert account_bot_runtime._parse_callback("ab:12:confirm:restart:n1") == (
        12,
        "confirm",
        "restart",
        "n1",
    )
    assert account_bot_runtime._parse_callback("bad:12:confirm:restart") is None


def test_account_bot_error_sanitizer_masks_token() -> None:
    token = "123456:secret-token"
    text = account_bot_service.sanitize_bot_error(
        f"https://api.telegram.org/bot{token}/sendMessage failed at /Users/me/project/file.py",
        token=token,
    )
    assert token not in text
    assert "api.telegram.org" not in text
    assert "/Users/me" not in text


def test_account_bot_token_payload_trims_whitespace() -> None:
    payload = AccountBotConfigUpdate(bot_token="  123456:secret-token  ")
    assert payload.bot_token == "123456:secret-token"
