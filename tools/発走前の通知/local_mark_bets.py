"""地方の印の買い目（道具「地方の推奨買目」の ``MarkRecommender``）を、発走前の通知から1レースぶん出す。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from 共通 import db

from 地方の推奨買目.coefficient_store import CoefficientStore
from 地方の推奨買目.mark_bets import MarkBets
from 地方の推奨買目.mark_recommender import MarkRecommender


class LocalMarkBets:
    """係数は作るときに読む（無ければその場で分かる）。DB は読むたびに開いてすぐ閉じる。
    オッズがまだ無い・予想の結果に列が足りない、のときは失敗にせず、理由つきの「なし」を返す。"""

    def __init__(self, db_path: str | Path | None = None, store: CoefficientStore | None = None) -> None:
        self._db_path = db_path
        self._coefficients = (store or CoefficientStore()).load()

    def marks(self, rid: str, forecast: dict[str, Any], marked: pd.DataFrame) -> MarkBets:
        """印の買い目（``marked`` は印を付けた全頭の表）。"""
        try:
            with db.open_db(self._db_path, default=db.LOCAL) as con:
                return MarkRecommender(con, self._coefficients).recommend(rid, forecast, marked)
        except (LookupError, ValueError) as error:
            return MarkBets.none(f"印の買い目を出せない: {error}")
