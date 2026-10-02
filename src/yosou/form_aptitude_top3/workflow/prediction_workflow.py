"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder, PredictionData
from yosou.shared.feature import PredictionTiming
from yosou.shared.place_value import PlaceValueColumns
from yosou.shared.workflow import AVERAGE, SegmentedPrediction

from ..dataset import OddsInput, OddsResolver, PoolAvailability, PoolFreeData
from ..feature import WIN_ODDS

#: 予測の結果の、アンサンブルの確率の列の名前。
PROBABILITY = "3着以内に入る確率"


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 予測用データを作る → 券種のオッズが無ければ、N を外して N を使わないモデルに切り替える →
    その時点のモデルで2つのモデルの予測確率を出して平均する → オッズが分かる時点なら、オッズから見た3着以内率（基準）と、
    複勝を買う期待値を足す（既存モデルの修正計画の 1）。

    ``dataset_builder`` は、予測する時点のモデルの材料の組み立て（木曜・前日は馬の力の材料、当日は今の材料。
    コマンドが時点で選ぶ）。``pool_free`` は、当日に券種のオッズが無いときに使う、N を使わないモデルでの予測。
    """

    def __init__(self, dataset_builder: DatasetBuilder, predictor: SegmentedPrediction,
                 odds_resolver: OddsResolver, place_value: PlaceValueColumns,
                 pool_free: SegmentedPrediction | None = None) -> None:
        self._dataset_builder = dataset_builder
        self._predictor = predictor
        self._odds_resolver = odds_resolver
        self._place_value = place_value
        self._pool_free = pool_free
        self._pools = PoolAvailability()

    def run(self, race_id: str, timing: PredictionTiming,
            given: OddsInput | None = None) -> pd.DataFrame:
        """1レースの出走馬ごとの「3着以内に入る確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名 と、複勝オッズなどの材料）、単勝オッズ（前日・当日だけ）、
        ``PROBABILITY``（平均）、モデルごとの確率、前日・当日はオッズから見た3着以内率と複勝の期待値。
        木曜は馬番が決まっていないので、馬番は空になる（馬ID・馬名で見分ける）。
        ``given`` は利用者が ``--odds`` で渡したオッズ（省略すると、元DB から決める）。
        当日に券種のオッズが無いレースは、N を使わないモデルで予測する（設計書 06 の図3）。
        """
        odds = self._odds_resolver.resolve(race_id, given)
        data = self._dataset_builder.build_prediction_data(race_id, timing, odds=odds)
        predictor = self._predictor
        if self._pool_free is not None and self._pools.missing(data):
            data, predictor = PoolFreeData().prediction(data), self._pool_free
        predicted = predictor.predict(data)
        probability = predicted[AVERAGE].rename(PROBABILITY)
        members = predicted.drop(columns=[AVERAGE])
        extra = self._place_value.of(probability, data)
        return pd.concat([data.ids, self._shown_odds(data), probability, members, extra], axis=1)

    def _shown_odds(self, data: PredictionData) -> pd.DataFrame:
        """結果の表に出す単勝オッズ。木曜はオッズを使わないので、列を出さない（設計書 07）。"""
        if WIN_ODDS not in data.features.columns:
            return pd.DataFrame(index=data.ids.index)
        return data.features[[WIN_ODDS]]
