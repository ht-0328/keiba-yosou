"""テスト用の架空の1シーズン（合成DB に入れる行の束）。値はすべて乱数で作った架空のもの。

- 2023-10-07 から 2024-12-28 までの毎週土曜に、東京で平地4レース。月の最初の土曜は障害も1レース。
- 80頭の馬に「能力」を1つずつ持たせ、能力が高いほど上位に来やすく、調教のタイムも速い（モデルが学べる手がかり）。
- 各レースで1割の確率で1頭が出走取消、3%の確率で1頭が競走中止。
- 出走別着度数は、各レースの前の時点の通算の着回数。調教は開催日の3日前と10日前（坂路かウッド）。
- 最後に、確定前の3レース（2025-01-11 東京）を足す。1R は出馬表（速報の馬場状態・馬体重・取消つき）、
  2R は出走馬名表、3R は障害の出馬表。

| クラス | 仕事 |
|---|---|
| ``SeasonBuilder`` | 入口。シーズンの行の束を作る |
| ``SyntheticHorse`` | 架空の馬1頭 |
| ``RacePlan`` | レース1つの条件（レース番号・コース・距離） |
| ``RaceOutcome`` | 1レースの結果（着順・人気・取消・中止）を決める |
| ``CareerCounter`` | 馬ごとの通算の着回数を数える |
| ``WorkoutLog`` | 調教の行を作る |
| ``FinishedRaceRows`` | 終わった1レースの行を足す |
| ``FutureRaceRows`` | 確定前の3レースと速報の行を足す |

日付やレースID などの定数は ``season_plan.py``。
"""

from .season_builder import SeasonBuilder
from .season_plan import (
    ANNOUNCED_TURF_GOING,
    CARD_RACE_ID,
    ENTRY_LIST_RACE_ID,
    FIRST_RACE_DAY,
    JUMP_CARD_RACE_ID,
    SCRATCHED_HORSE_NO,
    TEST_FIRST_DAY,
    TRAIN_FIRST_DAY,
    VALID_FIRST_DAY,
)

__all__ = [
    "SeasonBuilder", "CARD_RACE_ID", "ENTRY_LIST_RACE_ID", "JUMP_CARD_RACE_ID",
    "SCRATCHED_HORSE_NO", "ANNOUNCED_TURF_GOING",
    "FIRST_RACE_DAY", "TRAIN_FIRST_DAY", "VALID_FIRST_DAY", "TEST_FIRST_DAY",
]
