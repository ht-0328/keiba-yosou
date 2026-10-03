"""予測の流れを進める。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from yosou.shared.dataset import DatasetBuilder, PredictionData
from yosou.shared.feature import PredictionTiming
from yosou.shared.place_value import PlaceValueColumns
from yosou.shared.win_value import WinValueColumns
from yosou.shared.workflow import AVERAGE, SegmentedPrediction

from ..dataset import OddsInput, OddsResolver, PaceAttachment, PoolAvailability, PoolFreeData, WinTargetData
from ..feature import WIN_ODDS
from .explained_prediction import ExplainedPrediction

#: 予測の結果の、アンサンブルの確率の列の名前（3着以内のモデルと1着のモデル）。
PROBABILITY = "3着以内に入る確率"
WIN_PROBABILITY = "1着になる確率"
#: 1レースの展開の予想の予測（まとまり P の元の予測の表）を返す関数（レースID, 時点, 利用者が渡したオッズ）。
PaceSource = Callable[[str, PredictionTiming, OddsInput | None], pd.DataFrame]


@dataclass(frozen=True)
class _Prepared:
    """予測用データと、それを予測するモデル（3着以内と1着）。当日に券種のオッズが無ければ、N を使わないモデル。"""

    data: PredictionData
    predictor: SegmentedPrediction
    win_predictor: SegmentedPrediction | None


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 予測用データを作る → 券種のオッズが無ければ、N を外して N を使わないモデルに切り替える →
    その時点の3着以内のモデルで2つのモデルの予測確率を出して平均する → 1着のモデルでも同じ手順で予測する →
    オッズが分かる時点なら、オッズから見た3着以内率（基準）と複勝の期待値、単勝の期待値を足す（既存モデルの修正計画の 1、設計書 15 の 14）。

    ``dataset_builder`` は、予測する時点のモデルの材料の組み立て（木曜・前日は馬の力の材料、当日は今の材料。
    コマンドが時点で選ぶ）。``pool_free`` は、当日に券種のオッズが無いときに使う、N を使わないモデルでの予測。
    ``pace`` は、展開の予想の結果（P）を足して学んだ時点のモデルで予測するときに渡す、そのレースの展開の予測を返す関数
    （コマンドが、P を採用した時点でだけ渡す。設計書 15 の 13）。
    ``win_predictor``・``win_pool_free`` は1着のモデル（置き場所は ``WIN_FOLDER``）での予測。渡さなければ、1着の確率と単勝の期待値は出さない。
    """

    def __init__(self, dataset_builder: DatasetBuilder, predictor: SegmentedPrediction,
                 odds_resolver: OddsResolver, place_value: PlaceValueColumns,
                 pool_free: SegmentedPrediction | None = None, pace: PaceSource | None = None,
                 win_predictor: SegmentedPrediction | None = None, win_pool_free: SegmentedPrediction | None = None) -> None:
        self._dataset_builder = dataset_builder
        self._predictor = predictor
        self._odds_resolver = odds_resolver
        self._place_value = place_value
        self._pool_free = pool_free
        self._pace = pace
        self._win_predictor = win_predictor
        self._win_pool_free = win_pool_free
        self._pools = PoolAvailability()
        self._win_target = WinTargetData()
        self._win_value = WinValueColumns()

    def run(self, race_id: str, timing: PredictionTiming,
            given: OddsInput | None = None) -> pd.DataFrame:
        """1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名 と、複勝オッズなどの材料）、単勝オッズ（前日・当日だけ）、
        ``PROBABILITY``（平均）、モデルごとの確率、前日・当日はオッズから見た3着以内率と複勝の期待値、
        ``WIN_PROBABILITY``（1着のモデルの平均。1着のモデルがあるとき）と、前日・当日は単勝の期待値。
        木曜は馬番が決まっていないので、馬番は空になる（馬ID・馬名で見分ける）。
        ``given`` は利用者が ``--odds`` で渡したオッズ（省略すると、元DB から決める）。
        当日に券種のオッズが無いレースは、N を使わないモデルで予測する（設計書 06 の図3）。
        """
        return self._table(self._prepared(race_id, timing, given))

    def explain(self, race_id: str, timing: PredictionTiming,
                given: OddsInput | None = None) -> ExplainedPrediction:
        """``run`` と同じ予測に、3着以内のモデルに渡した特徴量の値と、特徴量ごとの寄与（理由を見せる材料）を添える。"""
        prepared = self._prepared(race_id, timing, given)
        return ExplainedPrediction(
            table=self._table(prepared), features=prepared.data.features,
            contributions=prepared.predictor.contributions(prepared.data), timing=timing,
            pool_free=prepared.predictor is not self._predictor,
        )

    def _prepared(self, race_id: str, timing: PredictionTiming, given: OddsInput | None) -> _Prepared:
        """予測用データと、それを予測するモデル（当日に券種のオッズが無ければ、N を使わないモデル）。"""
        odds = self._odds_resolver.resolve(race_id, given)
        data = self._dataset_builder.build_prediction_data(race_id, timing, odds=odds)
        if self._pace is not None:
            data = PaceAttachment().apply(data, self._pace(race_id, timing, given))
        if self._pool_free is not None and self._pools.missing(data):
            return _Prepared(PoolFreeData().prediction(data), self._pool_free, self._win_pool_free)
        return _Prepared(data, self._predictor, self._win_predictor)

    def _table(self, prepared: _Prepared) -> pd.DataFrame:
        """予測の結果の表。"""
        data = prepared.data
        predicted = prepared.predictor.predict(data)
        probability = predicted[AVERAGE].rename(PROBABILITY)
        members = predicted.drop(columns=[AVERAGE])
        extra = self._place_value.of(probability, data)
        win = self._win_columns(data, prepared.win_predictor)
        return pd.concat([data.ids, self._shown_odds(data), probability, members, extra, win], axis=1)

    def _win_columns(self, data: PredictionData, win_predictor: SegmentedPrediction | None) -> pd.DataFrame:
        """1着になる確率（1着のモデルの平均）と、前日・当日は単勝の期待値。1着のモデルが無ければ（前の版で学習したモデル）何も足さない。"""
        if win_predictor is None:
            return pd.DataFrame(index=data.ids.index)
        win_data = self._win_target.prediction(data)
        try:
            predicted = win_predictor.predict(win_data)
        except FileNotFoundError:
            return pd.DataFrame(index=data.ids.index)
        probability = predicted[AVERAGE].rename(WIN_PROBABILITY)
        return pd.concat([probability, self._win_value.of(probability, win_data)], axis=1)

    def _shown_odds(self, data: PredictionData) -> pd.DataFrame:
        """結果の表に出す単勝オッズ。木曜はオッズを使わないので、列を出さない（設計書 07）。"""
        if WIN_ODDS not in data.features.columns:
            return pd.DataFrame(index=data.ids.index)
        return data.features[[WIN_ODDS]]
