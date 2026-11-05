"""1レースの通知（投稿する文と添付ファイル）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RaceNotice:
    #: 投稿する文（印・買い目・◎ の理由と近走）。
    text: str
    #: 添付するファイル（中央は全頭の予想根拠の Markdown、地方は全頭の表の画像）。無ければ None。
    attachment: Path | None = None
