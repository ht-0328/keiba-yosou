"""発走前の通知が保存した予想（``<rid>.json``）から、通知のときと同じ決まりで推奨買目を作り直す。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import pandas as pd

from 地方の推奨買目.position_model import EV
from 地方の推奨買目.recommendation_set import RecommendationSet

#: 当日の時点の予想の見出しに入る言葉（推奨買目は当日の時点だけ）。
_RACE_DAY = "当日"
BET_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "ticket", "numbers", "odds", EV)


class Recommends(Protocol):
    """1レースの推奨買目を返す部品（本番は道具「地方の推奨買目」の ``Recommender``）。"""

    def recommend(self, rid: str, forecast: dict) -> RecommendationSet: ...


class NotifiedBets:
    """``folder`` は通知の保存先（``reports/発走前の通知/地方``。下に ``<開催日>/<rid>.json``）。

    通知が発走前に取り込んだ途中のオッズは元DB に残る（確定の断面は発表月日時分が 0 なので、「最新の発表」は途中の断面のまま）。
    保存した予想とそのオッズで推奨買目を作り直すと、通知が出した買い目と同じものになる。``skip`` は数えないレース
    （締め切り後に取り込んだ断面があって、通知のときのオッズが再現できないレース）。推奨買目を出せなかったレースも数えない。
    """

    def __init__(self, recommender: Recommends, folder: Path, skip: frozenset[str] = frozenset()) -> None:
        self._recommender = recommender
        self._folder = Path(folder)
        self._skip = skip

    def build(self, day_from: str) -> pd.DataFrame:
        """``day_from``（YYYY-MM-DD）以降の、1行 = 1点の表（``BET_COLUMNS``）。"""
        rows: list[tuple] = []
        for path in sorted(self._folder.glob("*/*.json")):
            rid = path.name.split(".")[0]
            if path.name != f"{rid}.json" or path.parent.name < day_from or rid in self._skip:
                continue
            forecast = json.loads(path.read_text(encoding="utf-8"))
            if _RACE_DAY not in str(forecast.get("title", "")):
                continue
            rows += [(rid, path.parent.name, row.ticket, row.numbers, row.odds, row.value) for row in self._chosen(rid, forecast).rows]
        return pd.DataFrame(rows, columns=list(BET_COLUMNS))

    def _chosen(self, rid: str, forecast: dict) -> RecommendationSet:
        try:
            return self._recommender.recommend(rid, forecast)
        except (LookupError, ValueError) as error:
            return RecommendationSet((), str(error))
