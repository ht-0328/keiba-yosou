"""通知の設定（Discord のウェブフック URL・発走の何分前か）。"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from 発走前の通知.folders import DEFAULT_FOLDER

#: 設定ファイルの名前（置き場所は reports/発走前の通知。Git 対象外）。
SETTINGS_FILE = "設定.json"
#: ウェブフック URL を入れる環境変数（設定ファイルより優先）。
WEBHOOK_ENV = "KEIBA_DISCORD_WEBHOOK"
#: 発走の何分前に取り込みと予想を始めるか（既定）。10分前のオッズ ≒ 確定オッズ を前提にしているので前倒ししない。
DEFAULT_MINUTES_BEFORE = 10


@dataclass(frozen=True)
class NotifySettings:
    """ウェブフック URL と、発走の何分前に始めるか。

    設定ファイル ``reports/発走前の通知/設定.json``（``{"webhook_url": "https://discord.com/api/webhooks/…", "minutes_before": 10}``）
    から読む。URL は環境変数 ``KEIBA_DISCORD_WEBHOOK`` があればそちら。無ければ空（投稿するときに ``require_webhook`` で止める）。
    """

    webhook_url: str = ""
    minutes_before: int = DEFAULT_MINUTES_BEFORE

    @classmethod
    def load(cls, folder: Path = DEFAULT_FOLDER, environ: Mapping[str, str] | None = None) -> NotifySettings:
        environ = os.environ if environ is None else environ
        path = folder / SETTINGS_FILE
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        url = environ.get(WEBHOOK_ENV) or str(data.get("webhook_url") or "")
        return cls(url, int(data.get("minutes_before") or DEFAULT_MINUTES_BEFORE))

    def require_webhook(self, folder: Path = DEFAULT_FOLDER) -> str:
        """ウェブフック URL。無ければ、どこに書けばよいかを添えて ``FileNotFoundError``。"""
        if self.webhook_url:
            return self.webhook_url
        raise FileNotFoundError(f"Discord のウェブフック URL がありません。{folder / SETTINGS_FILE} に"
                                f' {{"webhook_url": "https://discord.com/api/webhooks/…"}} と書くか、環境変数 {WEBHOOK_ENV} に入れてください')
