"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder, OddsInput, OddsResolver, PopularityApplier, PopularityInput
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.group import POPULARITY_RANK
from yosou.shared.workflow import AVERAGE, SegmentedPrediction

from ..danger import DangerJudge
from ..dataset import FAVORITE_BAND
from .prediction_timings import TIMING_CHOICES, TIMINGS

#: 予測の結果の、アンサンブルの確率の列の名前。
PROBABILITY = "4着以下になる確率"


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 人気を決める（渡されなければオッズの順）→ 予測用データを作る → 人気帯ごとのその時点のモデルで、
    2つのモデルの予測確率を平均する → オッズから見た4着以下の確率（基準）と、危険度（予想 − 基準）と、危険か
    （危険度が人気帯の線以上）を足す（既存モデルの修正計画の 1）。

    ``judges`` は時点 → ``DangerJudge``（学習のときに検証期間で決めた人気帯ごとの線）。無い時点は危険と判定しない。
    """

    def __init__(self, dataset_builder: DatasetBuilder, predictor: SegmentedPrediction,
                 popularity_applier: PopularityApplier, odds_resolver: OddsResolver,
                 judges: dict[PredictionTiming, DangerJudge]) -> None:
        self._dataset_builder = dataset_builder
        self._predictor = predictor
        self._popularity_applier = popularity_applier
        self._odds_resolver = odds_resolver
        self._judges = dict(judges)

    def run(self, race_id: str, timing: PredictionTiming, given: PopularityInput | None = None,
            given_odds: OddsInput | None = None) -> pd.DataFrame:
        """1レースの人気馬ごとの「4着以下になる確率」と危険度。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名）、人気帯、人気順位、``PROBABILITY``（平均）、モデルごとの確率、
        オッズから見た4着以下の確率・危険度・危険。``given`` は利用者が ``--pops`` で渡した人気、``given_odds`` は
        ``--odds`` で渡した単勝オッズ（人気が渡されなければ、オッズの小さい順を人気にする）。
        """
        self._check_timing(timing)
        odds = self._odds_resolver.resolve(race_id, given_odds)
        popularity = self._popularity_applier.resolve(race_id, given, odds)
        data = self._dataset_builder.build_prediction_data(race_id, timing, popularity, odds)
        predicted = self._predictor.predict(data)
        probability = predicted[AVERAGE].rename(PROBABILITY)
        members = predicted.drop(columns=[AVERAGE])
        judged = self._judge(timing).judge(probability, data.baseline.probabilities(), data.ids[FAVORITE_BAND])
        ranks = data.features[[POPULARITY_RANK]]
        return pd.concat([data.ids, ranks, probability, members, judged], axis=1)

    def _judge(self, timing: PredictionTiming) -> DangerJudge:
        return self._judges.get(timing, DangerJudge({}))

    def _check_timing(self, timing: PredictionTiming) -> None:
        """この予想は、人気の見当が付く前日・当日だけ予測を出す（設計書 07）。"""
        if timing not in TIMINGS:
            raise ValueError(
                f"この予想は前日・当日だけです（{timing.label}では、馬番も人気も決まっていません）。"
                f"--timing は {TIMING_CHOICES} のどちらかです"
            )
