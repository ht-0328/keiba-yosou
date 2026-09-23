"""過去の記録から数える部品。「開催日より前のものだけを使う」決まり（設計書 11 の 2）を、ここで守る。

| クラス | 仕事 |
|---|---|
| ``DatedRecords`` | 鍵と日付を持つ、過去の記録の表 |
| ``AsOfLookup`` | 出走の行ごとに、「開催日の N 日前まで」でいちばん新しい記録の行を引く |
| ``RecentRunSummary`` | 過去走を、馬ごとの「その走までの近5走のまとめ」にする |
| ``PopularityRunSummary`` | 過去走を、馬ごとの「その走までの近5走の人気のまとめ」にする（まとまり J の材料） |
| ``Top3Rate`` | 騎手・調教師・血統の、近1年の3着以内の割合 |
| ``PedigreeTop3Rate`` | 父・母父の産駒の、近1年の3着以内の割合（芝ダを問わない分と、同じ芝ダだけの分） |
| ``ConditionUpsetRate`` | 同じ条件のレースの、近1年の中荒れ以上の割合（荒れ具合の予想のまとまり E） |
| ``WorkoutLookup`` | 開催日の前 14日以内の調教（直近の1本と、本数） |
| ``WorkoutCoverage`` | 調教の記録が DB にある期間（コースごとの最初の日）。「記録が無い」と「調教していない」を区別する |
"""

from .as_of_lookup import AsOfLookup
from .condition_upset_rate import RACES, UPSETS, ConditionUpsetRate
from .dated_records import DatedRecords
from .pedigree_top3_rate import PedigreeTop3Rate
from .popularity_run_summary import (
    AVERAGE_POPULARITY,
    WORSE_THAN_POPULARITY,
    PopularityRunSummary,
)
from .recent_run_summary import RecentRunSummary
from .top3_rate import Top3Rate
from .workout_coverage import COURSES, HILL, WOOD, WorkoutCoverage
from .workout_lookup import WorkoutLookup

__all__ = [
    "DatedRecords", "AsOfLookup", "RecentRunSummary", "PopularityRunSummary", "Top3Rate", "PedigreeTop3Rate",
    "ConditionUpsetRate", "RACES", "UPSETS",
    "WorkoutLookup", "WorkoutCoverage", "COURSES", "HILL", "WOOD",
    "WORSE_THAN_POPULARITY", "AVERAGE_POPULARITY",
]
