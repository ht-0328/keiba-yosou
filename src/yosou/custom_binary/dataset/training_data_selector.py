"""全頭の特徴量の表から、人気範囲と条件に当てはまる馬の学習データを作る。"""

import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import FeatureCatalog

from ..setting import ModelSettings
from .binary_target_labeler import BinaryTargetLabeler
from .dataset_columns import EVALUATION, IDS
from .odds_baseline import OddsBaseline
from .popularity_filter import PopularityFilter


class TrainingDataSelector:
    """全頭で作った特徴量の表から、人気範囲と条件に当てはまる馬の学習データを作る。

    探索では全特徴量の表を1回だけ作り、設定ごとにここで絞る。``frame`` は選んだ特徴量と条件の列を含む表。
    オッズの基準は、絞る前の全頭（同じレースの全馬のオッズ）で作る。
    """

    def select(self, rows: pd.DataFrame, frame: pd.DataFrame, settings: ModelSettings,
               catalog: FeatureCatalog) -> TrainingData:
        kept = rows[PopularityFilter().mask(rows, settings.popularity) & settings.conditions.mask(frame)]
        baseline = OddsBaseline(settings.target).build(rows).at(kept.index) if settings.odds_baseline else None
        return TrainingData(
            IDS.select(kept), frame.loc[kept.index, list(settings.selected)],
            BinaryTargetLabeler().labels(kept, settings.target),
            EVALUATION.select(kept), catalog, settings.target, baseline=baseline,
        )
