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
| ``RaceEarlyRecordRepository`` | レースごとの序盤と後半の記録（最初のコーナー・先頭の馬番・前3ハロン・後3ハロン）。1行 = 1レース。展開から着順を予想する予想が使う |
| ``RacePayoutRepository`` | レースごとの4券種（単勝・馬連・3連複・3連単）の払戻と、成立したか。レース単位の予想が使う |
| ``FinalOddsRepository`` | 1つの券種の確定オッズを、期間の全レースぶん 1組番1行で読む（o1〜o6。親の確定の断面と発表月日時分で結ぶ） |
| ``PayoutRepository`` | 1つの券種の払戻の明細を、期間の全レースぶん 1組番1行で読む（hr__<券種>払戻。複勝・ワイド・同着の複数行はそのまま） |
| ``PayoutFlagRepository`` | 払戻の親（hr）から、7券種の不成立・特払と、返還の有無を、期間の全レースぶん 1レース1行で読む |
| ``AnnouncedGoingRepository`` | 速報の馬場状態 |
| ``AnnouncedWeightRepository`` | 速報の馬体重 |
| ``AnnouncedOddsRepository`` | 締め切り前の単勝オッズ（時系列オッズのいちばん新しい断面）。人気かオッズを使う予想が使う |
| ``PlaceOddsRepository`` | 複勝オッズ（最低・最高）。終わったレースは確定、これから走るレースは締め切り前のいちばん新しい断面 |
| ``ScratchRepository`` | 速報の出走取消・競走除外 |
| ``ModelRepository`` | 学習済みモデルのファイル（SQL ではなくファイルに読み書きする） |
| ``PlacePriceRepository`` | 複勝の見込みの倍率（帯ごとの倍率）のファイル。モデルと一緒に置く |

``TargetScope`` は「どの出走について読むか」を表す値、``RaceDayRange`` は「どの開催日の範囲を読むか」を表す値
（``FinalOddsRepository``・``PayoutRepository``・``PayoutFlagRepository`` が使う）、``CareerCountSql`` は ``CareerCountRepository`` の SQL の式を作る部品。
``PAYOUT_TABLES`` は、``RacePayoutRepository`` の券種の鍵（列の名前の頭）と払戻の表の対応。
``void_column(券種)`` は ``PayoutFlagRepository`` の「その券種が不成立か特払なら True」の列の名前、``REFUNDED`` は返還の有無の列の名前。
"""

from .announced_going_repository import AnnouncedGoingRepository
from .announced_odds_repository import AnnouncedOddsRepository
from .announced_weight_repository import AnnouncedWeightRepository
from .career_count_repository import CareerCountRepository
from .entry_repository import EntryRepository
from .fact_table_repository import FactTableRepository
from .final_odds_repository import FinalOddsRepository
from .model_repository import ModelRepository
from .past_run_repository import PastRunRepository
from .payout_flag_repository import REFUNDED, PayoutFlagRepository, void_column
from .payout_repository import PayoutRepository
from .pedigree_day_repository import PedigreeDayRepository
from .people_day_repository import PeopleDayRepository
from .place_odds_repository import PlaceOddsRepository
from .place_price_repository import PlacePriceRepository
from .race_day_range import RaceDayRange
from .race_early_record_repository import RaceEarlyRecordRepository
from .race_entry_table_repository import RaceEntryTableRepository
from .race_payout_repository import PAYOUT_TABLES, RacePayoutRepository
from .scratch_repository import ScratchRepository
from .target_scope import TargetScope
from .workout_coverage_repository import WorkoutCoverageRepository
from .workout_repository import WorkoutRepository

__all__ = [
    "TargetScope", "FactTableRepository", "RaceEntryTableRepository", "EntryRepository",
    "CareerCountRepository", "PastRunRepository", "WorkoutRepository", "WorkoutCoverageRepository",
    "PeopleDayRepository", "PedigreeDayRepository", "RacePayoutRepository", "PAYOUT_TABLES", "RaceEarlyRecordRepository",
    "AnnouncedGoingRepository", "AnnouncedWeightRepository", "AnnouncedOddsRepository", "PlaceOddsRepository",
    "ScratchRepository", "ModelRepository", "PlacePriceRepository",
    "RaceDayRange", "FinalOddsRepository", "PayoutRepository", "PayoutFlagRepository", "void_column", "REFUNDED",
]
