"""架空のシーズンの日付・レース・確定前のレースの定数。"""

from __future__ import annotations

from datetime import date

from .race_plan import DIRT_TRACK, JUMP_TRACK, TURF_TRACK, RacePlan

#: 乱数の種。同じ種なら、いつも同じシーズンができる。
SEED = 20260921
FIRST_RACE_DAY = date(2023, 10, 7)
LAST_RACE_DAY = date(2024, 12, 28)
#: 検証データ・テストデータの最初の日（このシーズンに合わせた区切り）。
VALID_FIRST_DAY = date(2024, 7, 1)
TEST_FIRST_DAY = date(2024, 10, 1)

#: 競馬場は東京だけ。
VENUE_CODE, VENUE_NAME = "05", "東京"
HORSE_COUNT = 80
#: 1レースの頭数。
FIELD_SIZE = 10
#: 毎週の平地のレース。
FLAT_RACES: tuple[RacePlan, ...] = (
    RacePlan("01", TURF_TRACK, 1600, 1340), RacePlan("02", DIRT_TRACK, 1400, 1250),
    RacePlan("03", TURF_TRACK, 2000, 2010), RacePlan("04", DIRT_TRACK, 1600, 1380),
)
#: 月の最初の土曜だけ行う障害のレース。
JUMP_RACE = RacePlan("05", JUMP_TRACK, 3000, 3200)

#: 確定前のレースの開催日と rid。
FUTURE_DAY = date(2025, 1, 11)
CARD_RACE_ID = "2025011105010101"        # 1R 出馬表（馬番が決まっている）
ENTRY_LIST_RACE_ID = "2025011105010102"  # 2R 出走馬名表（馬番が未定）
JUMP_CARD_RACE_ID = "2025011105010103"   # 3R 障害の出馬表
#: 確定前のレースの頭数。
FUTURE_FIELD_SIZE = 8
#: 確定前の 1R で、速報で出走取消になる馬番。
SCRATCHED_HORSE_NO = 8
#: 確定前の 1R で、最後に発表される芝の馬場状態コード（3 = 重）。
ANNOUNCED_TURF_GOING = "3"
