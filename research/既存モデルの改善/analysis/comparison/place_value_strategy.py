"""複勝を期待値で買う（見込みの倍率は学習期間で、線は検証期間で決める）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE
from yosou.shared.dataset.column_names import FIELD_SIZE, PLACE_ODDS_LOW, PLACE_PAYOUT
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE

from yosou.shared.place_value import PlaceHitProbability, PlacePriceEstimator

from ..scores import ThresholdChooser
from ..walk_forward import PART, PART_TEST, PART_VALID, PREDICTION_COLUMN
from ..windows import TestWindow

#: 足す列の名前。
PLACE_PROBABILITY = "複勝的中の確率"
EXPECTED_VALUE = "複勝の期待値"


class PlaceValueStrategy:
    """複勝を「複勝的中の確率 × 見込みの払戻の倍率」（期待値）で買う（既存モデルの修正計画の 1・2「馬を選ぶ基準」）。

    - 見込みの倍率（``PlacePriceEstimator``）: 検証期間より前（学習期間）の、当たった複勝の払戻で決める。
    - 買う線（``ThresholdChooser``）: 検証期間の回収率がいちばん高い線。
    - テスト期間は、その線以上の馬を全部買う。テスト期間の結果は、どちらを決めるのにも使わない。

    ``history`` は、見込みの倍率を決めるための全期間の表（開催日・複勝オッズ（最低）・複勝の払戻の列）。
    """

    def __init__(self, history: pd.DataFrame) -> None:
        self._history = history
        self._probability = PlaceHitProbability()
        self._chooser = ThresholdChooser()

    def run(self, joined: pd.DataFrame, window: TestWindow) -> tuple[pd.DataFrame, float]:
        """（テスト期間に買った行, 線）。``joined`` は1つの区切りの検証とテストの行（予測と評価用の列を突き合わせたもの）。

        検証期間で線が決まらなければ（どの線も点が足りない）、何も買わない（空の表, NaN）。
        """
        estimator = self._estimator(window)
        valued = self._with_value(joined, estimator)
        valid = valued[valued[PART] == PART_VALID]
        threshold = self._chooser.choose(valid[EXPECTED_VALUE], valid[PLACE_PAYOUT].fillna(0.0))
        test = valued[valued[PART] == PART_TEST]
        return test[test[EXPECTED_VALUE] >= threshold], threshold

    def _estimator(self, window: TestWindow) -> PlacePriceEstimator:
        before = self._history[self._history[RACE_DATE] < pd.Timestamp(window.valid_first_day)]
        return PlacePriceEstimator().fit(before[PLACE_ODDS_LOW], before[PLACE_PAYOUT].fillna(0.0))

    def _with_value(self, joined: pd.DataFrame, estimator: PlacePriceEstimator) -> pd.DataFrame:
        probability = self._probability.of(joined[PREDICTION_COLUMN], joined[FIELD_SIZE], joined[TOP2_RATE],
                                           joined[TOP3_RATE])
        price = estimator.estimate(joined[PLACE_ODDS_LOW])
        return joined.assign(**{PLACE_PROBABILITY: probability, EXPECTED_VALUE: probability * price})
