"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder, OddsInput, OddsResolver, PopularityApplier, PopularityInput
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.group import POPULARITY_RANK
from yosou.shared.place_value import PlaceValueColumns
from yosou.shared.workflow import AVERAGE, SegmentedPrediction

from ..dataset import LongshotZone, LongshotZoneFilter

#: 予測の結果の、アンサンブルの確率の列の名前。
PROBABILITY = "3着以内に入る確率"


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 人気を決める（渡されなければオッズの順）→ 予測用データを作る → 区分（中穴・大穴）ごとの
    その時点のモデルで、2つのモデルの予測確率を平均する → オッズが分かる時点なら、オッズから見た3着以内率と
    複勝を買う期待値を足す（既存モデルの修正計画の 1）→ 区分が指定されていれば、その行だけにする。
    """

    def __init__(self, dataset_builder: DatasetBuilder, predictor: SegmentedPrediction,
                 popularity_applier: PopularityApplier, odds_resolver: OddsResolver,
                 zone_filter: LongshotZoneFilter, place_value: PlaceValueColumns) -> None:
        self._dataset_builder = dataset_builder
        self._predictor = predictor
        self._popularity_applier = popularity_applier
        self._odds_resolver = odds_resolver
        self._zone_filter = zone_filter
        self._place_value = place_value

    def run(self, race_id: str, timing: PredictionTiming, given: PopularityInput | None = None,
            zone: LongshotZone | None = None, given_odds: OddsInput | None = None) -> pd.DataFrame:
        """1レースの穴馬ごとの「3着以内に入る確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名）、穴馬の区分、人気順位、``PROBABILITY``（平均）、モデルごとの確率、
        前日・当日はオッズから見た3着以内率と複勝の期待値。木曜は馬番が決まっていないので、馬番は空になる。
        ``given`` は利用者が ``--pops`` で渡した全頭の人気、``given_odds`` は ``--odds`` で渡した全頭の単勝オッズ
        （人気が渡されなければ、オッズの小さい順を人気にする）。``zone`` を渡すと、その区分の穴馬の行だけにする。
        """
        odds = self._odds_resolver.resolve(race_id, given_odds)
        popularity = self._popularity_applier.resolve(race_id, given, odds)
        data = self._dataset_builder.build_prediction_data(race_id, timing, popularity, odds)
        predicted = self._predictor.predict(data)
        probability = predicted[AVERAGE].rename(PROBABILITY)
        members = predicted.drop(columns=[AVERAGE])
        ranks = data.features[[POPULARITY_RANK]]
        extra = self._place_value.of(probability, data)
        prediction = pd.concat([data.ids, ranks, probability, members, extra], axis=1)
        return self._zone_filter.apply(prediction, zone)
