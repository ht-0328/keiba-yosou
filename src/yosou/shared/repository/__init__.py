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
| ``AbilityRunRepository`` | 過去の全出走と対象の出走（馬主・生産者・母を付けて）。馬の力の材料（まとまり M）の元 |
| ``SpeedFigureRepository`` | 過去の全部の走のスピード指数（SQL と計算は道具「能力指数」の ``FigureCache``）。まとまり M の元 |
| ``WorkoutSummaryRepository`` | 対象の出走ごとの、レースの前の 14日・30日の調教のまとめ。まとまり M の元 |
| ``SalePriceRepository`` | セリの取引価格（hs）。まとまり M の元 |
| ``FirstHorsePoolRepository``・``AllHorsesPoolRepository`` | 券種オッズ（確定、無ければ最新の断面）から、馬ごとの確率（1着の馬だけを見る馬単・3連単と、組の全部の馬に配る馬連・ワイド・3連複・複勝）。券種ごとのオッズから見た支持（まとまり N）と custom_binary の元。SQL の共通の前半は ``PoolOddsRowsSql``、券種ごとの決まりは ``PoolSpec``・``POOLS`` |
| ``MarketRunRepository`` | 過去の平地の全出走の単勝オッズと着順（騎手・調教師・血統の市場に対する成績の材料）。全頭の3着以内・穴馬・人気馬の予想が使う |
| ``HeadToHeadRunRepository`` | 過去の平地の全出走と対象の出走の着順（レースID・開催日・馬ID・着順だけ）。対戦レーティング（まとまり O）の元 |
| ``RaceEarlyRecordRepository`` | レースごとの序盤と後半の記録（最初のコーナー・先頭の馬番・前3ハロン・後3ハロン）。1行 = 1レース。展開から着順を予想する予想が使う |
| ``StakesTendencyRepository`` | 重賞のレースごとの傾向（それより前の開催の数え上げと基準。``tools/共通/stakes.py`` の SQL）。1行 = 1レース。重賞の傾向と近走から3着以内を予想する予想が使う |
| ``RacePayoutRepository`` | レースごとの4券種（単勝・馬連・3連複・3連単）の払戻と、成立したか。レース単位の予想が使う |
| ``FinalOddsRepository`` | 1つの券種の確定オッズを、期間の全レースぶん 1組番1行で読む（o1〜o6。親の確定の断面と発表月日時分で結ぶ） |
| ``TicketOddsRepository`` | 1つの券種の、指定した買い目（レースID と組番）だけの確定オッズを読む（道具「印の成績」のトリガミの確かめ） |
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

from .ability_run_repository import RUN_COLUMNS, AbilityRunRepository
from .all_horses_pool_repository import AllHorsesPoolRepository
from .announced_going_repository import AnnouncedGoingRepository
from .announced_odds_repository import AnnouncedOddsRepository
from .announced_weight_repository import AnnouncedWeightRepository
from .career_count_repository import CareerCountRepository
from .entry_repository import EntryRepository
from .fact_table_repository import FactTableRepository
from .final_odds_repository import FinalOddsRepository
from .ticket_odds_repository import TicketOddsRepository
from .first_horse_pool_repository import FirstHorsePoolRepository
from .head_to_head_run_repository import HeadToHeadRunRepository
from .market_run_repository import MarketRunRepository
from .model_repository import ModelRepository
from .past_run_repository import PastRunRepository
from .payout_flag_repository import REFUNDED, PayoutFlagRepository, void_column
from .payout_repository import PayoutRepository
from .pedigree_day_repository import PedigreeDayRepository
from .people_day_repository import PeopleDayRepository
from .place_odds_repository import PlaceOddsRepository
from .place_price_repository import PlacePriceRepository
from .pool_spec import POOLS, PoolSpec
from .race_day_range import RaceDayRange
from .race_early_record_repository import RaceEarlyRecordRepository
from .race_entry_table_repository import RaceEntryTableRepository
from .race_payout_repository import PAYOUT_TABLES, RacePayoutRepository
from .sale_price_repository import SalePriceRepository
from .scratch_repository import ScratchRepository
from .speed_figure_repository import SpeedFigureRepository
from .stakes_tendency_repository import StakesTendencyRepository
from .target_scope import TargetScope
from .workout_coverage_repository import WorkoutCoverageRepository
from .workout_repository import WorkoutRepository
from .workout_summary_repository import WorkoutSummaryRepository

__all__ = [
    "TargetScope", "FactTableRepository", "RaceEntryTableRepository", "EntryRepository",
    "CareerCountRepository", "PastRunRepository", "WorkoutRepository", "WorkoutCoverageRepository",
    "PeopleDayRepository", "PedigreeDayRepository", "MarketRunRepository", "RacePayoutRepository", "PAYOUT_TABLES", "RaceEarlyRecordRepository",
    "AnnouncedGoingRepository", "AnnouncedWeightRepository", "AnnouncedOddsRepository", "PlaceOddsRepository",
    "ScratchRepository", "StakesTendencyRepository", "ModelRepository", "PlacePriceRepository",
    "RaceDayRange", "FinalOddsRepository", "TicketOddsRepository", "PayoutRepository", "PayoutFlagRepository", "void_column", "REFUNDED",
    "AbilityRunRepository", "RUN_COLUMNS", "SpeedFigureRepository", "WorkoutSummaryRepository", "SalePriceRepository",
    "FirstHorsePoolRepository", "AllHorsesPoolRepository", "POOLS", "PoolSpec", "HeadToHeadRunRepository",
]
