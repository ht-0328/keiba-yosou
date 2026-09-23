"""実験の材料を、全頭の学習データに足す。"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import chain

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming

from . import past_market_excess_features as past
from . import people_market_excess_features as people
from . import pool_support_features as pool
from . import speed_figure_features as speed
from . import track_bias_features as bias
from .condition_columns import ConditionColumns
from .past_market_excess_features import PastMarketExcessFeatures
from .people_market_excess_features import PeopleMarketExcessFeatures
from .pool_support_features import PoolSupportFeatures
from .speed_figure_features import SpeedFigureFeatures
from .track_bias_features import TrackBiasFeatures

#: 実験のまとまり → （表に出す名前, 特徴量の名前, 分かる最初の時点）。券種のオッズと当日の傾向は当日だけ。
EXPERIMENT_GROUPS: dict[str, tuple[str, tuple[str, ...], PredictionTiming]] = {
    "pool": ("券種ごとのオッズから見た支持", pool.NAMES, PredictionTiming.RACE_DAY),
    "bias": ("当日の馬場傾向", bias.NAMES, PredictionTiming.RACE_DAY),
    "speed": ("能力指数（標準タイムと比べた速さ）", speed.NAMES, PredictionTiming.THURSDAY),
    "past": ("相手関係を考えた近走（市場に対する成績）", past.NAMES, PredictionTiming.THURSDAY),
    "people": ("騎手・調教師・血統の市場に対する成績", people.NAMES, PredictionTiming.THURSDAY),
}


def experiment_features() -> tuple[Feature, ...]:
    """実験で足す特徴量の一覧（どれも数値。まとまりの記号は L）。"""
    groups = (_features_of(names, timing) for _, names, timing in EXPERIMENT_GROUPS.values())
    return tuple(chain.from_iterable(groups))


def _features_of(names: tuple[str, ...], timing: PredictionTiming) -> tuple[Feature, ...]:
    return tuple(Feature(name, "L", FeatureKind.NUMERIC, timing) for name in names)


class ExperimentTableBuilder:
    """全頭の学習データ（``form``）に、実験の材料の列と、条件で分ける実験の区分の列（評価用の列）を足す。

    材料は ``history``（2016年からの全出走）から作り、（レースID, 馬ID）で並べる。特徴量の一覧も広げる。
    ``supports`` は券種ごとの支持の表（``ComboPoolSupportRepository`` などで読んだもの）。
    """

    def build(self, form: TrainingData, history: pd.DataFrame, supports: Sequence[pd.DataFrame]) -> TrainingData:
        parts = [
            PoolSupportFeatures().build(history[["race_id", "horse_id", "horse_no", "win_odds"]], supports),
            TrackBiasFeatures().build(history), SpeedFigureFeatures().build(history),
            PastMarketExcessFeatures().build(history), PeopleMarketExcessFeatures().build(history),
        ]
        extra = parts[0]
        for part in parts[1:]:
            extra = extra.merge(part, on=["race_id", "horse_id"], how="outer")
        keys = pd.DataFrame({"race_id": form.ids[RACE_ID].to_numpy(), "horse_id": form.ids[HORSE_ID].to_numpy()})
        aligned = keys.merge(extra, on=["race_id", "horse_id"], how="left")
        new_names = [feature.name for feature in experiment_features()]
        added = aligned[new_names].set_axis(form.features.index)
        features = pd.concat([form.features, added.astype("float64")], axis=1)
        evaluation = pd.concat([form.evaluation, ConditionColumns().build(form.features)], axis=1)
        catalog = FeatureCatalog(form.catalog.features + experiment_features())
        return TrainingData(form.ids, features, form.targets, evaluation, catalog, form.label_name,
                            form.class_labels, form.baseline)
