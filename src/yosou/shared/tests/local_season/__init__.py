"""テスト用の架空の地方の1シーズン（地方の合成DB に入れる行の束）。値はすべて乱数で作った架空のもの。

中央の架空のシーズン（``yosou.shared.tests.synthetic_season``）と同じ骨組みで、地方の表の形だけが違う。

- 2023-10-07 から 2024-12-28 までの毎週土曜に、大井でダートの平地4レース。月の最初の土曜は重賞（グレード P）も1レース。
- 80頭の馬に「能力」を1つずつ持たせ、能力が高いほど上位に来やすい。所属は地方（東西所属コード 3）。
- クラスは競走条件名称（Ｃ２　一・Ｂ２　二 など）で表す（競走条件コードは 000）。
- 出走別着度数地方（``nd``）は、各レースの前の時点の通算の着回数（総合・地方合計・ダートの距離帯・馬場状態・大井ダ）。
- 競走馬マスタ地方（``nu``）と、その3代血統情報。調教・セリ・マイニングは無い（地方競馬DATA に無い）。
- 最後に、確定前の出馬表2レース（2025-01-11 大井）を足す。1R は速報（馬場状態・馬体重・取消・締め切り前の複勝オッズ）つき、
  2R は速報なし。地方には出走馬名表の段階が無いので、どちらも馬番が決まっている。

| クラス | 仕事 |
|---|---|
| ``LocalSeasonBuilder`` | 入口。シーズンの行の束を作る |
| ``LocalRacePlan`` | レース1つの条件（中央の ``RacePlan`` に競走条件名称を足したもの） |
| ``LocalCareerCounter`` | 馬ごとの出走別着度数地方の着回数を数える |
| ``LocalFinishedRaceRows`` | 終わった1レースの行を足す |
| ``LocalFutureRaceRows`` | 確定前の2レースと速報の行を足す |

馬（``SyntheticHorse``）・結果（``RaceOutcome``）・払戻（``PayoutRows``）は中央のシーズンと同じ部品を使う。
日付やレースID などの定数は ``local_season_plan.py``。
"""

from .local_season_builder import LocalSeasonBuilder
from .local_season_plan import (
    ANNOUNCED_DIRT_GOING,
    CARD_RACE_ID,
    FIRST_RACE_DAY,
    PLAIN_CARD_RACE_ID,
    SCRATCHED_HORSE_NO,
    TEST_FIRST_DAY,
    TRAIN_FIRST_DAY,
    VALID_FIRST_DAY,
    VENUE_CODE,
    VENUE_NAME,
)

__all__ = [
    "LocalSeasonBuilder", "CARD_RACE_ID", "PLAIN_CARD_RACE_ID", "SCRATCHED_HORSE_NO", "ANNOUNCED_DIRT_GOING",
    "FIRST_RACE_DAY", "TRAIN_FIRST_DAY", "VALID_FIRST_DAY", "TEST_FIRST_DAY", "VENUE_CODE", "VENUE_NAME",
]
