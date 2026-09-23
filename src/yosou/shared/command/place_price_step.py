"""学習のあとに、複勝の見込みの倍率を決めて保存する。"""

from __future__ import annotations

from pathlib import Path

from 共通.render import Table

from ..dataset import TrainingData
from ..dataset.column_names import PLACE_ODDS_LOW, PLACE_PAYOUT
from ..place_value import PlacePriceEstimator
from ..repository import PlacePriceRepository


class PlacePriceStep:
    """学習データの期間（学習に使った行）の複勝の払戻から、見込みの倍率（``PlacePriceEstimator``）を決め、
    モデルの置き場所に保存する。予測のときに、複勝を買う期待値を出すのに使う（既存モデルの修正計画の 1・2）。

    検証データ・テストデータの払戻は使わない。保存した倍率の表を返す。
    """

    def run(self, train: TrainingData, models_root: Path) -> Table:
        estimator = PlacePriceEstimator().fit(train.evaluation[PLACE_ODDS_LOW], train.evaluation[PLACE_PAYOUT])
        path = PlacePriceRepository(models_root).save(estimator.state())
        rows = [[band, factor] for band, factor in estimator.multipliers().items()]
        return Table(["複勝の最低オッズの帯", "払戻 ÷ 最低オッズ の平均"], rows,
                     title="複勝の見込みの倍率（学習データの期間の、当たった複勝から決めた値）",
                     note=f"保存した場所: {path}。複勝の期待値 = 複勝的中の確率 × 最低オッズ × この倍率。")
