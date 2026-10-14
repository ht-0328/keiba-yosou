"""トラックバイアスのデータの読み書き。元DB を読む SQL はこのフォルダだけに書き、1つの SQL につき 1つのリポジトリにする。

| リポジトリ | 読む・書くもの |
|---|---|
| ``BiasRunRepository`` | 傾きの元になる、中央・平地の全出走（馬番・頭数・4コーナーの順位・単勝オッズ・着順） |
| ``RaceEntryRepository`` | これから走る1レースの鍵と条件と出走馬（馬番・頭数） |
| ``PriorSlopeTableRepository`` | レースごとの傾きと過去の傾きの表の pickle のファイルと、元DB の印（``stamp.json``）。SQL ではなくファイルに読み書きする |
"""

from .bias_run_repository import BiasRunRepository
from .prior_slope_table_repository import PriorSlopeTableRepository
from .race_entry_repository import RaceEntryRepository

__all__ = ["BiasRunRepository", "RaceEntryRepository", "PriorSlopeTableRepository"]
