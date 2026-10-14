"""展開スコアのデータの読み書き。元DB を読む SQL はこのフォルダだけに書き、1つの SQL につき 1つのリポジトリにする。

| リポジトリ | 読む・書くもの |
|---|---|
| ``DevelopmentRunRepository`` | 表 G の元になる、中央・平地の全出走（最初のコーナーの順位・前3ハロン・単勝オッズ・着順） |
| ``RaceCourseRepository`` | これから走る1レースの競馬場コードと芝ダ |
| ``EntryNameRepository`` | 1レースの出走馬の馬番と馬名（結果を人が見るため。``HORSE_NO``・``HORSE_NAME`` は列の名前） |
| ``AdvantageTableRepository`` | 表 G の pickle のファイルと、元DB の印（``stamp.json``）。SQL ではなくファイルに読み書きする |
"""

from .advantage_table_repository import AdvantageTableRepository
from .development_run_repository import DevelopmentRunRepository
from .entry_name_repository import HORSE_NAME, HORSE_NO, EntryNameRepository
from .race_course_repository import RaceCourseRepository

__all__ = ["DevelopmentRunRepository", "RaceCourseRepository", "EntryNameRepository", "HORSE_NAME", "HORSE_NO", "AdvantageTableRepository"]
