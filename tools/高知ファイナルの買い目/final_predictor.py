"""高知の出走の表とオッズの断面から、1レースの印と買い目を決める。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .final_bets import FinalBets
from .final_columns import HORSE_NO, PLACE_LOW, RACE_ID
from .final_features import FinalFeatures
from .final_models import FinalModels
from .final_rule import FinalRule

#: オッズの断面（道具「地方の直前の買い目」の ``OddsSnapshotRepository.load`` の表）の列。
ODDS_NOW = "odds_now"
ANNOUNCED = "announced"


class FinalPredictor:
    """``runs`` は ``KochiRunRepository.read`` の表（予想するレースの出走馬の行を含む）、``snapshot`` は発走前のオッズの断面。
    予想するレースの行の単勝オッズを断面の値に置きかえてから材料を作る（断面にオッズの無い馬は取消として外れる）。
    学んだ条件（距離・頭数）に合わないレース、断面の無いレースは、理由つきの「なし」。"""

    def __init__(self, models: FinalModels, popularity_rates: Mapping[float, float], rule: FinalRule | None = None,
                 features: FinalFeatures | None = None) -> None:
        self._models = models
        self._rates = dict(popularity_rates)
        self._rule = rule or FinalRule()
        self._features = features or FinalFeatures()

    def bets(self, rid: str, runs: pd.DataFrame, snapshot: pd.DataFrame) -> FinalBets:
        if snapshot.empty:
            return FinalBets.none("時系列オッズの断面がまだ無い")
        table = self._features.build(self._with_odds(rid, runs, snapshot), self._rates, focus=rid)
        table = table.merge(snapshot[[HORSE_NO, PLACE_LOW]], on=HORSE_NO, how="left")
        if self._models.scope(table).empty:
            return FinalBets.none("学んだ条件（1300〜1600m・9頭以上）に合わない")
        return self._rule.decide(self._models.score(table), str(snapshot[ANNOUNCED].max()))

    @staticmethod
    def _with_odds(rid: str, runs: pd.DataFrame, snapshot: pd.DataFrame) -> pd.DataFrame:
        """予想するレースの行の ``win_odds`` を、断面の今のオッズにする（断面に無い馬は欠損値）。"""
        odds = snapshot[snapshot[ODDS_NOW] > 0].set_index(HORSE_NO)[ODDS_NOW]
        runs = runs.copy()
        target = runs[RACE_ID].astype(str) == rid
        runs["win_odds"] = runs["win_odds"].astype(float)
        runs.loc[target, "win_odds"] = pd.to_numeric(runs.loc[target, HORSE_NO], errors="coerce").map(odds).to_numpy()
        return runs
