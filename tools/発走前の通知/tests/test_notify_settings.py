"""NotifySettings（ウェブフック URL と何分前か）のテスト。URL は架空。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from 発走前の通知.notify_settings import SETTINGS_FILE, WEBHOOK_ENV, NotifySettings


def test_設定ファイルから読む(tmp_path: Path) -> None:
    (tmp_path / SETTINGS_FILE).write_text(json.dumps({"webhook_url": "https://example.invalid/hook", "minutes_before": 12}), encoding="utf-8")
    settings = NotifySettings.load(tmp_path, environ={})
    assert settings.require_webhook(tmp_path) == "https://example.invalid/hook"
    assert settings.minutes_before == 12


def test_環境変数が設定ファイルより優先(tmp_path: Path) -> None:
    (tmp_path / SETTINGS_FILE).write_text(json.dumps({"webhook_url": "https://example.invalid/file"}), encoding="utf-8")
    settings = NotifySettings.load(tmp_path, environ={WEBHOOK_ENV: "https://example.invalid/env"})
    assert settings.webhook_url == "https://example.invalid/env"
    assert settings.minutes_before == 10


def test_URLが無ければ書く場所を添えて止まる(tmp_path: Path) -> None:
    settings = NotifySettings.load(tmp_path, environ={})
    assert settings.webhook_url == ""
    with pytest.raises(FileNotFoundError, match=SETTINGS_FILE):
        settings.require_webhook(tmp_path)
