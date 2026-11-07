"""地方の推奨買目（道具「地方の推奨買目」）を、発走前の通知から1レースぶん出す。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from 共通 import db

from 地方の推奨買目.coefficient_store import CoefficientStore
from 地方の推奨買目.recommendation_set import RecommendationSet
from 地方の推奨買目.recommender import Recommender, UpsetSource

from 発走前の通知.saved_upset_probabilities import SavedUpsetProbabilities


class LocalRecommendations:
    """係数は作るときに読む（無ければその場で分かる）。DB は読むたびに開いてすぐ閉じる。
    3連複の荒れ具合の条件は、発走前の予想が予想と同じ接続で出して書いておいた券種ごとの中荒れ以上の確率（``upsets``。
    省略すると既定の置き場所の ``<rid>.荒れ具合.json``）を読むだけで、ここでは計算しない（計算すると、接続を開くたびに
    地方の全成績の事実表を作り直して数分かかる）。ファイルが無い・確率が出せなかった、なら 3連複だけが対象外になる。
    オッズがまだ無い・予想の結果に列が足りない、のときは失敗にせず、点の無いまとまり（理由つき）を返す。"""

    def __init__(self, db_path: str | Path | None = None, store: CoefficientStore | None = None,
                 upsets: UpsetSource | None = None) -> None:
        self._db_path = db_path
        self._coefficients = (store or CoefficientStore()).load()
        self._upsets = upsets or SavedUpsetProbabilities()

    def recommend(self, rid: str, forecast: dict[str, Any]) -> RecommendationSet:
        try:
            with db.open_db(self._db_path, default=db.LOCAL) as con:
                return Recommender(con, self._coefficients, upsets=self._upsets).recommend(rid, forecast)
        except (LookupError, ValueError) as error:
            return RecommendationSet((), f"推奨買目を出せない: {error}")
