"""馬体重の表のデータの読み書き。元DB を読む SQL はこのフォルダだけに書き、1つの SQL につき 1つのリポジトリにする。

| リポジトリ | 読む・書くもの |
|---|---|
| ``WeightRunRepository`` | 表の元になる、中央・平地の全出走（増減・前走からの日数・馬齢・単勝オッズ・着順） |
| ``WeightTableRepository`` | 表 W の pickle のファイルと、元DB の印（``stamp.json``）。SQL ではなくファイルに読み書きする |
"""

from .weight_run_repository import WeightRunRepository
from .weight_table_repository import WeightTableRepository

__all__ = ["WeightRunRepository", "WeightTableRepository"]
