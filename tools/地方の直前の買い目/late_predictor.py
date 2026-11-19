"""1レースの材料（オッズの断面と全頭の予想の確率）から、直前の買い目を決める。"""

from __future__ import annotations

import pandas as pd

from .late_bets import LateBets
from .late_columns import FIELD_SIZE, HORSE_NO, ODDS_NOW, RACE_DATE, RACE_ID
from .late_features import LateFeatures
from .late_models import LateModels
from .late_rule import LateRule

#: 買い目を決める最少の頭数（学習用の表と同じ。これより少ないレースは学んでいない）。
MIN_HEADS = 5


class LatePredictor:
    """``snapshot`` は ``OddsSnapshotRepository.load`` の表（馬ごとのオッズの断面）、``probabilities`` は ``LateProbabilities.of`` の表。
    2つを馬番で結び、頭数は「今の断面にオッズのある馬」の数にする。断面が無い・頭数が足りないときは理由つきの「なし」。"""

    def __init__(self, models: LateModels, rule: LateRule | None = None, features: LateFeatures | None = None) -> None:
        self._models = models
        self._rule = rule or LateRule()
        self._features = features or LateFeatures()

    def bets(self, rid: str, snapshot: pd.DataFrame, probabilities: pd.DataFrame) -> LateBets:
        if snapshot.empty:
            return LateBets.none("時系列オッズの断面がまだ無い")
        material = self.material(rid, snapshot, probabilities)
        if len(material) < MIN_HEADS:
            return LateBets.none(f"オッズと予想のそろった馬が {len(material)} 頭（{MIN_HEADS} 頭未満）")
        scored = self._models.score(self._features.build(material))
        picks = tuple(self._rule.picks(scored))
        announced = str(snapshot["announced"].max())
        closeness = self._rule.closeness(scored)
        if not picks:
            return LateBets((), "2つの見込みがそろって線以上の馬がいない", announced, closeness)
        return LateBets(picks, "", announced, closeness)

    @staticmethod
    def material(rid: str, snapshot: pd.DataFrame, probabilities: pd.DataFrame) -> pd.DataFrame:
        """材料の表（``MATERIAL_COLUMNS``）。今の断面にオッズがあり、当日の予想のある馬だけ。"""
        merged = snapshot[snapshot[ODDS_NOW] > 0].merge(probabilities, on=HORSE_NO, how="inner")
        day = f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}"
        return merged.assign(**{RACE_ID: rid, RACE_DATE: day, FIELD_SIZE: len(merged)})
