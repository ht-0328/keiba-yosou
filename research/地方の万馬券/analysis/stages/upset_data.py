"""④荒れ具合の、1行 = 1レースの学習データの組み立て。本番の予想 ``yosou.local_upset_level`` に移した。ここからは同じ名前で使える。

- ``local_race_dataset_builder(con, slopes_by_race, rule=None)``: 地方の元DB への接続とレースごとの使う傾きの表から、学習データ・予測用データを作るクラス。
- ``LocalRaceTrainingDataCache``（本番の ``TrainingDataCache``）: 学習データを作って pickle にとっておく。ファイルの名前は
  ``学習データ-<ウォームアップの始まり>-<学習データの始まり>.pkl``。
"""

from __future__ import annotations

from yosou.local_upset_level.dataset import TrainingDataCache as LocalRaceTrainingDataCache, local_race_dataset_builder
from yosou.local_upset_level.feature import CATALOG, HORSE_CATALOG

__all__ = ["local_race_dataset_builder", "LocalRaceTrainingDataCache", "CATALOG", "HORSE_CATALOG"]
