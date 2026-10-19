"""予測の流れを進める（1頭ごとの「3着以内」と「1着」の予想）。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pandas as pd

from ..dataset import (
    DatasetBuilder,
    FinishPowerFreeData,
    OddsInput,
    OddsResolver,
    PaceAttachment,
    PoolAvailability,
    PoolFreeData,
    PredictionData,
    WinTargetData,
)
from ..feature import PredictionTiming
from ..feature.group import WIN_ODDS
from ..place_value import PlaceValueColumns
from ..win_value import WinValueColumns
from .explained_prediction import ExplainedPrediction
from .prepared_prediction import PreparedPrediction
from .segmented_prediction import AVERAGE, SegmentedPrediction

#: 予測の結果の、アンサンブルの確率の列の名前（3着以内のモデルと1着のモデル）。
PROBABILITY = "3着以内に入る確率"
WIN_PROBABILITY = "1着になる確率"
#: モデルごとの単勝の期待値の列の名前（例 ``単勝の期待値（LightGBM）``）。2モデル一致（◎ の単勝の期待値が、2つのモデルのそれぞれの確率でも
#: 線以上）を見るのに使う（研究「レースの種類ごとの買い方」の docs/04 の 9）。
WIN_VALUE_MEMBER = "単勝の期待値（{member}）"
#: 1レースの展開の予想の予測（まとまり P の元の予測の表）を返す関数（レースID, 時点, 利用者が渡したオッズ）。
PaceSource = Callable[[str, PredictionTiming, OddsInput | None], pd.DataFrame]
#: 予測用データに列を足す関数（予測用データ, レースID, 時点, 利用者が渡したオッズ → 列を足した予測用データ）。
#: その時点の3着以内のモデルにだけ足す材料（展開スコア S）を、コマンドが時点で選んで渡す。
DataAttachment = Callable[[PredictionData, str, PredictionTiming, OddsInput | None], PredictionData]


class PredictionWorkflow:
    """予測の流れ（近走と適性の予想の設計書 05 の図2。中央と地方の両方の予想が使う）。

    オッズを決める → 予測用データを作る → 券種のオッズが無ければ、N を外して N を使わないモデルに切り替える →
    その時点の3着以内のモデルで2つのモデルの予測確率を出して平均する（当日の勝ち切る材料 Q は外して渡す） →
    1着のモデルでも同じ手順で予測する（Q は渡したまま。設計書 15 の 15） →
    オッズが分かる時点なら、オッズから見た3着以内率（基準）と複勝の期待値、単勝の期待値を足す（既存モデルの修正計画の 1、設計書 15 の 14）。

    ``dataset_builder`` は、予測する時点のモデルの材料の組み立て（コマンドが時点で選んで渡す）。
    ``pool_free`` は、当日に券種のオッズが無いときに使う、N を使わないモデルでの予測。
    ``pace`` は、展開の予想の結果（P）を足して学んだ時点のモデルで予測するときに渡す、そのレースの展開の予測を返す関数
    （中央の予想のコマンドが、P を採用した時点でだけ渡す。地方の予想は渡さない）。
    ``extras``・``win_extras`` は、3着以内のモデル・1着のモデルの予測用データに列を足す関数の並び（展開スコア S を採用した時点で、
    コマンドが S を足す関数を渡す。設計書 15 の 17）。
    ``win_predictor``・``win_pool_free`` は1着のモデル（置き場所は ``1着`` のフォルダ）での予測。渡さなければ、1着の確率と単勝の期待値は出さない。
    """

    def __init__(self, dataset_builder: DatasetBuilder, predictor: SegmentedPrediction,
                 odds_resolver: OddsResolver, place_value: PlaceValueColumns,
                 pool_free: SegmentedPrediction | None = None, pace: PaceSource | None = None,
                 win_predictor: SegmentedPrediction | None = None, win_pool_free: SegmentedPrediction | None = None,
                 extras: Sequence[DataAttachment] = (), win_extras: Sequence[DataAttachment] = ()) -> None:
        self._dataset_builder = dataset_builder
        self._predictor = predictor
        self._odds_resolver = odds_resolver
        self._place_value = place_value
        self._pool_free = pool_free
        self._pace = pace
        self._win_predictor = win_predictor
        self._win_pool_free = win_pool_free
        self._extras = tuple(extras)
        self._win_extras = tuple(win_extras)
        self._pools = PoolAvailability()
        self._win_target = WinTargetData()
        self._win_value = WinValueColumns()
        self._finish_free = FinishPowerFreeData()

    def run(self, race_id: str, timing: PredictionTiming,
            given: OddsInput | None = None) -> pd.DataFrame:
        """1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名 と、複勝オッズなどの材料）、単勝オッズ（前日・当日だけ）、
        ``PROBABILITY``（平均）、モデルごとの確率、前日・当日はオッズから見た3着以内率と複勝の期待値、
        ``WIN_PROBABILITY``（1着のモデルの平均。1着のモデルがあるとき）と、前日・当日は単勝の期待値。
        馬番の決まっていないレース（中央の木曜）では、馬番は空になる（馬ID・馬名で見分ける）。
        ``given`` は利用者が ``--odds`` で渡したオッズ（省略すると、元DB から決める）。
        当日に券種のオッズが無いレースは、N を使わないモデルで予測する（設計書 06 の図3）。
        """
        return self._table(self._prepared(race_id, timing, given))

    def explain(self, race_id: str, timing: PredictionTiming,
                given: OddsInput | None = None) -> ExplainedPrediction:
        """``run`` と同じ予測に、3着以内のモデルに渡した特徴量の値と、特徴量ごとの寄与（理由を見せる材料）を添える。"""
        prepared = self._prepared(race_id, timing, given)
        return ExplainedPrediction(
            table=self._table(prepared), features=prepared.top3_data.features,
            contributions=prepared.predictor.contributions(prepared.top3_data), timing=timing,
            pool_free=prepared.predictor is not self._predictor,
        )

    def _prepared(self, race_id: str, timing: PredictionTiming, given: OddsInput | None) -> PreparedPrediction:
        """予測用データと、それを予測するモデル（当日に券種のオッズが無ければ、N を使わないモデル）。"""
        odds = self._odds_resolver.resolve(race_id, given)
        data = self._dataset_builder.build_prediction_data(race_id, timing, odds=odds)
        if self._pace is not None:
            data = PaceAttachment().apply(data, self._pace(race_id, timing, given))
        if self._pool_free is not None and self._pools.missing(data):
            data, predictor, win_predictor = PoolFreeData().prediction(data), self._pool_free, self._win_pool_free
        else:
            predictor, win_predictor = self._predictor, self._win_predictor
        top3_data = self._finish_free.prediction(data)
        for attach in self._extras:
            top3_data = attach(top3_data, race_id, timing, given)
        win_data = self._win_target.prediction(data)
        for attach in self._win_extras:
            win_data = attach(win_data, race_id, timing, given)
        return PreparedPrediction(data, top3_data, win_data, predictor, win_predictor)

    def _table(self, prepared: PreparedPrediction) -> pd.DataFrame:
        """予測の結果の表。"""
        data = prepared.data
        predicted = prepared.predictor.predict(prepared.top3_data)
        probability = predicted[AVERAGE].rename(PROBABILITY)
        members = predicted.drop(columns=[AVERAGE])
        extra = self._place_value.of(probability, data)
        win = self._win_columns(prepared)
        return pd.concat([data.ids, self._shown_odds(data), probability, members, extra, win], axis=1)

    def _win_columns(self, prepared: PreparedPrediction) -> pd.DataFrame:
        """1着になる確率（1着のモデルの平均）と、前日・当日は単勝の期待値（平均の確率と、モデルごとの確率のそれぞれで出したもの）。
        1着のモデルが無ければ（前の版で学習したモデル）何も足さない。"""
        win_data = prepared.win_data
        if prepared.win_predictor is None:
            return pd.DataFrame(index=win_data.ids.index)
        try:
            predicted = prepared.win_predictor.predict(win_data)
        except FileNotFoundError:
            return pd.DataFrame(index=win_data.ids.index)
        probability = predicted[AVERAGE].rename(WIN_PROBABILITY)
        members = [self._win_value.of(predicted[name], win_data).rename(columns=lambda _, n=name: WIN_VALUE_MEMBER.format(member=n))
                   for name in predicted.columns if name != AVERAGE]
        return pd.concat([probability, self._win_value.of(probability, win_data), *members], axis=1)

    def _shown_odds(self, data: PredictionData) -> pd.DataFrame:
        """結果の表に出す単勝オッズ。オッズを使わない時点は、列を出さない（設計書 07）。"""
        if WIN_ODDS not in data.features.columns:
            return pd.DataFrame(index=data.ids.index)
        return data.features[[WIN_ODDS]]
