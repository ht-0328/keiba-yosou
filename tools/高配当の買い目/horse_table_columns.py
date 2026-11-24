"""馬ごとの表（予想「高配当の組が当たるかを予想」が学習に使う、1頭1行の表）の列の名前（定数だけ）。"""

from __future__ import annotations

from 今週の予想.forecast_columns import (
    DANGER_SCORE,
    HORSE_NO,
    IS_DANGER,
    MARK,
    MARKET_TOP3,
    MARKET_WIN,
    PLACE_ODDS_HIGH,
    PLACE_ODDS_LOW,
    PLACE_VALUE,
    POPULARITY,
    PROBABILITY,
    RANK,
    UPDOWN,
    WIN_ODDS,
    WIN_PROBABILITY,
    WIN_VALUE,
    WIN_VALUE_BAND,
)
from 今週の予想.filter_columns import POOL_SUPPORT

RACE_ID = "race_id"
RACE_DATE = "race_date"
#: 行の鍵（1頭1行）。
KEY_COLUMNS: tuple[str, ...] = (RACE_ID, HORSE_NO)
#: 予想の材料になる列（予想のパッケージとの約束の列。今週の予想の、印を付けた1レースの表 ``MarkRule.assign`` の戻り値にある列）。
MATERIAL_COLUMNS: tuple[str, ...] = (
    PROBABILITY, WIN_PROBABILITY, MARKET_WIN, MARKET_TOP3, WIN_ODDS, PLACE_ODDS_LOW, PLACE_ODDS_HIGH, POPULARITY, RANK,
    IS_DANGER, DANGER_SCORE, MARK, UPDOWN, WIN_VALUE, PLACE_VALUE,
)
#: 必ず要る列（無ければ誤りにする）。
REQUIRED_COLUMNS: tuple[str, ...] = (RACE_ID, RACE_DATE, HORSE_NO, *MATERIAL_COLUMNS)
#: あれば残す列（予想の材料ではない。確かめや調べものに使う。馬ID・区切り・着順・◎ の期待値の帯・3連単の支持）。
EXTRA_COLUMNS: tuple[str, ...] = ("horse_id", "fold", "finish", WIN_VALUE_BAND, POOL_SUPPORT)
