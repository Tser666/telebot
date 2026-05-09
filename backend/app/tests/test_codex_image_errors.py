from __future__ import annotations

import json

from app.worker.plugins.builtin.codex_image.plugin import (
    _edit_html,
    _humanize_codex_error,
    _image_ext_from_bytes,
    _parse_generation_args,
    _safe_error_text,
)


def test_codex_usage_limit_error_is_human_readable() -> None:
    detail = json.dumps(
        {
            "error": {
                "type": "usage_limit_reached",
                "message": "The usage limit has been reached",
                "plan_type": "free",
                "resets_in_seconds": 600077,
            }
        }
    )
    msg = _humanize_codex_error(429, detail)
    assert "额度已用完" in msg
    assert "free" in msg
    assert "6天" in msg
    assert "usage_limit_reached" not in msg


def test_codex_error_redacts_sensitive_values_and_paths() -> None:
    msg = _safe_error_text(
        "Bearer abcdefghijklmn failed with access_token=abcdefghijklmnopqrstuvwxyz at /Users/me/.codex/auth.json"
    )
    assert "abcdefghijklmn" not in msg
    assert "abcdefghijklmnopqrstuvwxyz" not in msg
    assert "/Users/me" not in msg
    assert "<path>" in msg


def test_codex_image_command_options_are_extracted() -> None:
    class Ctx:
        config = {
            "image_size": "1024x1024",
            "aspect_ratio": "1:1",
            "image_format": "png",
        }

    prompt, opts = _parse_generation_args(
        ["--比例", "4:3", "--size=1536x1024", "--format", "jpeg", "云海", "城市"],
        Ctx(),  # type: ignore[arg-type]
    )
    assert prompt == "云海 城市"
    assert opts == {
        "image_size": "1536x1024",
        "aspect_ratio": "4:3",
        "image_format": "jpeg",
    }


def test_codex_image_ext_detects_image_magic_bytes() -> None:
    assert _image_ext_from_bytes(b"\x89PNG\r\n\x1a\nxxxx", "jpeg") == ".png"
    assert _image_ext_from_bytes(b"\xff\xd8\xffxxxx", "png") == ".jpg"
    assert _image_ext_from_bytes(b"RIFFxxxxWEBPxxxx", "png") == ".webp"


async def test_codex_status_edit_uses_html_parse_mode() -> None:
    class Event:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        async def edit(self, text: str, **kwargs: str) -> None:
            self.calls.append((text, kwargs))

    event = Event()
    await _edit_html(event, "<b>状态:</b> 正在生成")
    assert event.calls == [("<b>状态:</b> 正在生成", {"parse_mode": "html"})]


async def test_codex_status_edit_fallback_strips_html_tags() -> None:
    class Event:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        async def edit(self, text: str, **kwargs: str) -> None:
            self.calls.append((text, kwargs))
            if kwargs.get("parse_mode") == "html":
                raise RuntimeError("bad html")

    event = Event()
    await _edit_html(event, "<b>状态:</b> 正在生成")
    assert event.calls[-1] == ("状态: 正在生成", {})
