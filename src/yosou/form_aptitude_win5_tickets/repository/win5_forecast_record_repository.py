"""実際に予想した結果を、開催日ごとのファイルに書く・読む。"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

#: 置き場所のフォルダ名（``--models`` の下）。
FOLDER_NAME = "記録"


class Win5ForecastRecordRepository:
    """実際に予想した結果（日のまとめ・買い目・対象レースごとの確率と、使ったオッズの断面。``Win5Forecast.to_dict()`` の形の辞書）を
    ``<root>/記録/<開催日>.json`` に書く・読む（SQL は持たない）。

    確定オッズで確かめた成績と、実際に予想した成績を同じ表で比べるためにとっておく（設計書 15 の 7）。同じ開催日に予想し直したら、
    いちばん新しい予想で上書きする。
    """

    def __init__(self, root: Path) -> None:
        self._folder = Path(root) / FOLDER_NAME

    def save(self, record: dict[str, Any], race_date: date) -> Path:
        path = self._path(race_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 書きかけを読まれないように、別の名前で書いてから置き換える（道具「発走前の通知」が裏で予想している間に、
        # 道具「今週の予想」がこの記録を読むことがある）
        written = path.with_suffix(".tmp")
        written.write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        os.replace(written, path)
        return path

    def load(self, race_date: date) -> dict[str, Any]:
        """その開催日の記録。無ければ ``FileNotFoundError``。"""
        path = self._path(race_date)
        if not path.exists():
            raise FileNotFoundError(f"{race_date.isoformat()} の WIN5 の予想の記録がありません: {path}")
        return json.loads(path.read_bytes().decode("utf-8"))

    def _path(self, race_date: date) -> Path:
        return self._folder / f"{race_date.isoformat()}.json"
