"""架空の地方のシーズンの日付・レース・確定前のレースの定数。"""

from __future__ import annotations

from datetime import date

from .local_race_plan import LOCAL_DIRT_TRACK, LocalRacePlan

#: 乱数の種。同じ種なら、いつも同じシーズンができる。
SEED = 20261006
FIRST_RACE_DAY = date(2023, 10, 7)
LAST_RACE_DAY = date(2024, 12, 28)
#: 学習データ・検証データ・テストデータの最初の日（中央の架空のシーズンと同じ区切り）。
TRAIN_FIRST_DAY = date(2024, 1, 1)
VALID_FIRST_DAY = date(2024, 7, 1)
TEST_FIRST_DAY = date(2024, 10, 1)

#: 競馬場は大井だけ。
VENUE_CODE, VENUE_NAME = "44", "大井"
HORSE_COUNT = 80
#: 1レースの頭数。
FIELD_SIZE = 10
#: 毎週の平地のレース（全部ダート）。クラスは競走条件名称で表す（Ｃ２・Ｂ２・Ｃ１ と、格の無い3歳の条件戦）。
FLAT_RACES: tuple[LocalRacePlan, ...] = (
    LocalRacePlan("01", LOCAL_DIRT_TRACK, 1200, 1130, condition_name="Ｃ２　一"),
    LocalRacePlan("02", LOCAL_DIRT_TRACK, 1600, 1400, condition_name="Ｂ２　二"),
    LocalRacePlan("03", LOCAL_DIRT_TRACK, 1800, 1550, condition_name="Ｃ１　三"),
    LocalRacePlan("04", LOCAL_DIRT_TRACK, 1400, 1280, condition_name="３歳　一　二"),
)
#: 月の最初の土曜だけ行う重賞（主催者の格付け I。グレードコード P）。
STAKES_RACE = LocalRacePlan("05", LOCAL_DIRT_TRACK, 2000, 2050, grade="P", stakes_no="9101", name="テスト大賞典",
                            condition_name="３歳上　オープン")

#: 確定前のレースの開催日と rid（大井 1回1日目）。地方には出走馬名表の段階が無く、どちらも馬番の決まった出馬表。
FUTURE_DAY = date(2025, 1, 11)
CARD_RACE_ID = "2025011144010101"        # 1R 出馬表（速報の馬場状態・馬体重・取消・複勝オッズつき）
PLAIN_CARD_RACE_ID = "2025011144010102"  # 2R 出馬表（速報なし）
#: 確定前のレースの頭数。
FUTURE_FIELD_SIZE = 8
#: 確定前の 1R で、速報で出走取消になる馬番。
SCRATCHED_HORSE_NO = 8
#: 確定前の 1R で、最後に発表されるダートの馬場状態コード（3 = 重）。
ANNOUNCED_DIRT_GOING = "3"
