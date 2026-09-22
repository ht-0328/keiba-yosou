"""データの読み書き。SQL はこのフォルダだけに書き、1つの SQL につき 1つのリポジトリにする。

元DB（jvdata-store の DuckDB）は読むだけ。

| リポジトリ | 読む・書くもの |
|---|---|
| ``FactTableRepository`` | 事実表（一時表）を用意する |
| ``RaceEntryTableRepository`` | 予測する1レースの出走馬の一時表を作る |
| ``EntryRepository`` | 出走の行（事実表の列） |
| ``CareerCountRepository`` | 出走別着度数（その出走の時点の、通算の着回数） |
| ``PastRunRepository`` | 過去走 |
| ``WorkoutRepository`` | 調教（坂路・ウッド） |
| ``WorkoutCoverageRepository`` | 調教の記録が DB にある期間（コースごとの最初の調教日） |
| ``PeopleDayRepository`` | 騎手か調教師の、日ごとの成績 |
| ``PedigreeDayRepository`` | 父か母父の産駒の、日ごと・芝ダごとの成績 |
| ``AnnouncedGoingRepository`` | 速報の馬場状態 |
| ``AnnouncedWeightRepository`` | 速報の馬体重 |
| ``AnnouncedOddsRepository`` | 締め切り前の単勝オッズ（時系列オッズのいちばん新しい断面） |
| ``ScratchRepository`` | 速報の出走取消・競走除外 |
| ``ModelRepository`` | 学習済みモデルのファイル（SQL ではなくファイルに読み書きする） |

``TargetScope`` は「どの出走について読むか」を表す値、``CareerCountSql`` は ``CareerCountRepository`` の SQL の式を作る部品。
"""

from .announced_going_repository import AnnouncedGoingRepository
from .announced_odds_repository import AnnouncedOddsRepository
from .announced_weight_repository import AnnouncedWeightRepository
from .career_count_repository import CareerCountRepository
from .entry_repository import EntryRepository
from .fact_table_repository import FactTableRepository
from .model_repository import ModelRepository
from .past_run_repository import PastRunRepository
from .pedigree_day_repository import PedigreeDayRepository
from .people_day_repository import PeopleDayRepository
from .race_entry_table_repository import RaceEntryTableRepository
from .scratch_repository import ScratchRepository
from .target_scope import TargetScope
from .workout_coverage_repository import WorkoutCoverageRepository
from .workout_repository import WorkoutRepository

__all__ = [
    "TargetScope", "FactTableRepository", "RaceEntryTableRepository", "EntryRepository",
    "CareerCountRepository", "PastRunRepository", "WorkoutRepository", "WorkoutCoverageRepository",
    "PeopleDayRepository", "PedigreeDayRepository",
    "AnnouncedGoingRepository", "AnnouncedWeightRepository", "AnnouncedOddsRepository",
    "ScratchRepository", "ModelRepository",
]
