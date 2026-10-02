"""学習データと予測用データを作る入口。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from ..feature import EntryColumns, FeatureBuilder, PredictionTiming
from ..feature.odds import MarketPlaces
from . import column_names as names
from .baseline_logit import BaselineLogit
from .history_records_loader import HistoryRecordsLoader
from .prediction_data import PredictionData
from .race_records_loader import RaceRecordsLoader
from .required_info_check import RequiredInfoCheck
from .sample_selector import SampleSelector
from .target_baseline import TargetBaseline
from .target_labeler import TargetLabeler
from .training_data import TrainingData
from .training_period import TrainingPeriod

#: ID 列（学習データの列名 → 出走の記録の列名）。
_ID_COLUMNS = EntryColumns({
    names.RACE_ID: "race_id", names.RACE_DATE: "race_date", names.HORSE_ID: "horse_id",
    names.HORSE_NO: "horse_no", names.HORSE_NAME: "horse_name",
})
#: 評価用の列（学習データの列名 → 出走の記録の列名）。
_EVALUATION_COLUMNS = EntryColumns({
    names.FINISH: "finish", names.WIN_ODDS: "win_odds", names.POPULARITY: "popularity",
    names.WIN_PAYOUT: "win_payout", names.PLACE_PAYOUT: "place_payout",
    names.PLACE_ODDS_LOW: "place_odds_low", names.PLACE_ODDS_HIGH: "place_odds_high",
    names.FIELD_SIZE: "field_size",
})
#: 予想ごとに足す列が無いときの、空の列の選び方。
_NO_EXTRA_COLUMNS = EntryColumns({})
#: 予測用データの ``market`` の列（複勝の期待値を見積もる材料。予測するときの複勝オッズと頭数。
#: 単勝オッズは、展開の予想が単勝の期待値（印の☆）を出すのに使う）。
_PREDICTION_INFO_COLUMNS = EntryColumns({
    names.PLACE_ODDS_LOW: "place_odds_low", names.PLACE_ODDS_HIGH: "place_odds_high", names.FIELD_SIZE: "field_size",
    names.WIN_ODDS: "win_odds",
})


class DatasetBuilder:
    """学習データと予測用データを作る。

    どちらも同じ手順（記録を集める → 行を選ぶ → 特徴量を作る → 残す行を決める）を通し、学習と予測で
    特徴量の中身がずれないようにする（設計書 11 の 4）。予想ごとに違うところ（入れる行・目的変数・特徴量の一覧）は、
    作られるときに受け取る ``selector``・``target_builder``・``feature_builder`` の中にある。

    ``extra_columns`` は、出走の行から、学習データの評価用の列と予測の結果に足す列（予想ごと。例: 穴馬の区分。
    行を選ぶクラスが出走の行に足した列を、そのまま残すのに使う）。無ければ何も足さない。

    ``baseline`` は目的変数の基準（ロジット）の作り方（既存モデルの修正計画の 1・2）。渡すと、学習データと
    予測用データに基準が付き、モデルはそれを出発点にして上げ下げだけを学ぶ。渡さなければ基準なしで学ぶ。
    基準はオッズを使うので、行を絞る前（同じレースの全頭がそろった形）で作ってから、残す行を選ぶ。
    """

    def __init__(self, history_loader: HistoryRecordsLoader, race_loader: RaceRecordsLoader,
                 selector: SampleSelector, target_builder: TargetLabeler,
                 feature_builder: FeatureBuilder, extra_columns: EntryColumns | None = None,
                 baseline: TargetBaseline | None = None) -> None:
        self._history_loader = history_loader
        self._race_loader = race_loader
        self._selector = selector
        self._target_builder = target_builder
        self._feature_builder = feature_builder
        self._extra_columns = extra_columns or _NO_EXTRA_COLUMNS
        self._baseline = baseline
        self._required_info = RequiredInfoCheck()
        self._market_places = MarketPlaces()

    def build_training_data(self, period: TrainingPeriod) -> TrainingData:
        """``period`` の学習データの始まりからの出走で、学習データを作る。特徴量は当日の時点の全部。

        ウォームアップの始まりからの出走を読み、学習データの始まりより前の行は過去走の計算にだけ使う。
        """
        records = self._history_loader.load(period.warmup_first_day)
        samples = self._selector.training_samples(records.entries, period.train_first_day)
        sample_records = records.with_entries(samples)
        features = self._feature_builder.build(sample_records, PredictionTiming.RACE_DAY)
        kept = self._selector.keep_samples(samples)
        return TrainingData(
            ids=_ID_COLUMNS.select(kept),
            features=features.loc[kept.index],
            targets=self._target_builder.build(kept),
            evaluation=self._with_market_places(
                self._with_extra_columns(_EVALUATION_COLUMNS.select(kept), kept), samples, kept.index),
            catalog=self._feature_builder.catalog,
            label_name=self._target_builder.label_name,
            baseline=self._baseline_of(samples, kept.index),
        )

    def build_prediction_data(self, race_id: str, timing: PredictionTiming,
                              popularity: Mapping[int | str, int] | None = None,
                              odds: Mapping[int, float] | None = None) -> PredictionData:
        """1レースの出走馬の予測用データを作る。特徴量は ``timing`` の時点で使うものだけ。

        ``popularity`` は 馬番（木曜は馬名）→ 単勝人気、``odds`` は 馬番 → 単勝オッズ。まだ DB に無い値を、
        利用者が手で渡すか、締め切り前の値から作って渡すときに使う。
        障害レースと、その時点で要る情報（馬番・馬場状態・馬体重・オッズ）がまだ DB に無いときは ``ValueError``。
        """
        records = self._race_loader.load(race_id, popularity, odds)
        runners = self._selector.prediction_runners(records.entries, race_id)
        features = self._feature_builder.build(records.with_entries(runners), timing)
        kept = self._selector.keep_samples(runners)
        kept_features = features.loc[kept.index]
        self._required_info.check(kept_features)
        baseline = self._baseline_of(runners, kept.index)
        return PredictionData(
            ids=self._with_extra_columns(_ID_COLUMNS.select(kept), kept), features=kept_features,
            timing=timing, catalog=self._feature_builder.catalog,
            baseline=baseline.for_timing(timing) if baseline is not None else None,
            market=self._with_market_places(_PREDICTION_INFO_COLUMNS.select(kept), runners, kept.index),
        )

    def _baseline_of(self, rows: pd.DataFrame, kept: pd.Index) -> BaselineLogit | None:
        """``rows``（同じレースの全頭）で基準を作り、``kept`` の行だけにする。基準の作り方が無ければ None。"""
        if self._baseline is None:
            return None
        values = self._baseline.build(rows).loc[kept]
        return BaselineLogit(values, self._baseline.known_from)

    def _with_market_places(self, table: pd.DataFrame, rows: pd.DataFrame, kept: pd.Index) -> pd.DataFrame:
        """``table`` の右に、オッズから見た勝率・2着以内率・3着以内率を付ける。

        ``rows``（同じレースの全頭）で出してから ``kept`` の行だけにする。オッズの無い時点（木曜）は欠損値。
        """
        places = self._market_places.of(rows).loc[kept]
        return pd.concat([table, places], axis=1)

    def _with_extra_columns(self, table: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
        """``table`` の右に、予想ごとに足す列（``rows`` から選ぶ）を付ける。"""
        return pd.concat([table, self._extra_columns.select(rows)], axis=1)
