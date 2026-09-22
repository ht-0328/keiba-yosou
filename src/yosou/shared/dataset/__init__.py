"""学習データ・予測用データを作る（設計書 06 の図1・08・10）。

| クラス | 仕事 |
|---|---|
| ``DatasetBuilder`` | 入口。学習データか予測用データを作る。下のクラスを順に呼ぶだけ |
| ``TrainingData``・``PredictionData`` | 学習データ・予測用データの表（1行 = 1頭） |
| ``HistoryRecordsLoader`` | 学習用に、ある日以降の全部の出走の記録を集める |
| ``RaceRecordsLoader`` | 予測用に、1レースの出走馬の記録を集める（速報を反映し、渡された人気を当てる） |
| ``EntryRecordsLoader`` | リポジトリを順に呼んで、対象の出走の記録を集める |
| ``AnnouncedWeightApplier`` | 速報の馬体重を、出走の行に反映する |
| ``ScratchApplier`` | 速報の出走取消・競走除外を、出走の行に反映する |
| ``FlatRunnerFilter`` | 障害レースと、出走しなかった馬の行を除く（どの予想でも同じ決まり） |
| ``SampleSelector`` | 入れる行の選び方の決まり（インターフェース）。守るクラスは予想ごとに作る |
| ``TargetLabeler`` | 目的変数の付け方の決まり（インターフェース）。守るクラスは予想ごとに作る |
| ``Top3TargetBuilder`` | 目的変数「3着以内なら 1」（「1着」の列も付ける）。近走と適性の予想と穴馬の予想が使う |
| ``PopularityInput`` | 利用者が ``--pops`` で渡した「馬番（木曜は馬名）→ 人気」を表す値 |
| ``PopularityApplier`` | 予測に使う人気を決める（渡された人気 → 締め切り前のオッズ → 元DB の人気）。人気を使う予想が使う |
| ``RequiredInfoCheck`` | 予測に要る情報（馬番・馬場状態・馬体重）が DB にあるかを確かめる |
| ``TrainingPeriod`` | 学習データの期間（ウォームアップ・学習・検証・テストの始まりの日） |
| ``PeriodSplitter``・``SplitData`` | 学習データを時期で、学習・検証・テストに分ける |

列の名前（レースID・確定着順 など）は ``column_names.py``。予想ごとに違う目的変数の列の名前は、ここには無い
（3着以内・1着だけは ``Top3TargetBuilder`` と一緒に ``top3_target_builder.py`` にある）。
多頭数とみなす出走頭数（``LARGE_FIELD_FROM``）は ``field_size_rule.py``。
"""

from .column_names import HORSE_ID, HORSE_NAME, HORSE_NO, RACE_DATE, RACE_ID
from .dataset_builder import DatasetBuilder
from .field_size_rule import LARGE_FIELD_FROM
from .flat_runner_filter import JUMP, FlatRunnerFilter
from .history_records_loader import HistoryRecordsLoader
from .period_splitter import PeriodSplitter
from .popularity_applier import PopularityApplier
from .popularity_input import PopularityInput
from .prediction_data import PredictionData
from .race_records_loader import RaceRecordsLoader
from .sample_selector import SampleSelector
from .split_data import SplitData
from .target_labeler import TargetLabeler
from .top3_target_builder import TOP3, WIN, Top3TargetBuilder
from .training_data import TrainingData
from .training_period import (
    DEFAULT_TEST_FIRST_DAY,
    DEFAULT_TRAIN_FIRST_DAY,
    DEFAULT_VALID_FIRST_DAY,
    TrainingPeriod,
)

__all__ = [
    "DatasetBuilder", "TrainingData", "PredictionData", "TrainingPeriod", "PeriodSplitter", "SplitData",
    "HistoryRecordsLoader", "RaceRecordsLoader", "SampleSelector", "TargetLabeler",
    "Top3TargetBuilder", "TOP3", "WIN", "PopularityInput", "PopularityApplier",
    "FlatRunnerFilter", "JUMP", "LARGE_FIELD_FROM",
    "DEFAULT_TRAIN_FIRST_DAY", "DEFAULT_VALID_FIRST_DAY", "DEFAULT_TEST_FIRST_DAY",
    "RACE_ID", "RACE_DATE", "HORSE_ID", "HORSE_NO", "HORSE_NAME",
]
