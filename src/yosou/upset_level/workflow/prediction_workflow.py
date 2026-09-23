"""予測の流れを進める。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from yosou.shared.dataset import OddsInput, OddsResolver, RaceDatasetBuilder
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository

from ..dataset import BetType, UpsetLevel

#: 予測の結果の列の名前（券種、クラスごとの確率、いちばん高いクラス、中荒れ以上の確率）。
BET = "券種"
TOP_LEVEL = "いちばん高いクラス"
UPSET_OR_MORE = "中荒れ以上の確率"
PREDICTION_COLUMNS: tuple[str, ...] = (BET, *UpsetLevel.labels(), TOP_LEVEL, UPSET_OR_MORE)


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 予測用データ（1行）を作る → 券種ごとに、その時点のモデルを読み込み、2つのモデルの4つの確率を
    平均する → 券種 × 4つの確率の表にする。
    """

    def __init__(self, dataset_builder: RaceDatasetBuilder, repositories: Mapping[BetType, ModelRepository],
                 odds_resolver: OddsResolver) -> None:
        self._dataset_builder = dataset_builder
        self._repositories = dict(repositories)
        self._odds_resolver = odds_resolver

    def run(self, race_id: str, timing: PredictionTiming, given: OddsInput | None = None,
            bets: Sequence[BetType] | None = None) -> pd.DataFrame:
        """1レースの、券種ごとの荒れ具合の確率（1行 = 1券種）。

        列は ID 列（レースID・開催日・競馬場・レース番号）と ``PREDICTION_COLUMNS``。
        ``given`` は利用者が ``--odds`` で渡したオッズ（省略すると、元DB から決める）。``bets`` を渡すと、その券種だけ。
        """
        odds = self._odds_resolver.resolve(race_id, given)
        data = self._dataset_builder.build_prediction_data(race_id, timing, odds=odds)
        rows = [self._row(bet, self._probabilities(bet, timing, data)) for bet in (bets or tuple(BetType))]
        ids = data.ids.iloc[[0] * len(rows)].reset_index(drop=True)
        return pd.concat([ids, pd.DataFrame(rows)], axis=1)

    def _probabilities(self, bet: BetType, timing: PredictionTiming, data) -> np.ndarray:
        """その券種・その時点の2つのモデルの、4つの確率の平均（1レースぶん）。"""
        ensemble = EnsembleModel(self._repositories[bet].load(timing))
        return ensemble.predict_proba(data)[0]

    def _row(self, bet: BetType, probabilities: np.ndarray) -> dict[str, object]:
        by_level = {level.label: float(probability) for level, probability in zip(UpsetLevel, probabilities, strict=True)}
        top = UpsetLevel(int(probabilities.argmax()))
        return {
            BET: bet.label, **by_level, TOP_LEVEL: top.label,
            UPSET_OR_MORE: float(probabilities[UpsetLevel.MID.value:].sum()),
        }
