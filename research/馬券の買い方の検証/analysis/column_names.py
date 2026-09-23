"""列名の対応。予測ファイルの列（日本語。予想モデルの出力のまま）と、材料表・精算表の列（英語。事実表と同じ流儀）。

予測ファイルの日本語の列名は、予想モデルの定数をそのまま使う（ここで書き写さない）。
"""

from __future__ import annotations

from yosou.favorites_out_of_top3.workflow import PROBABILITY as DANGER_PROBABILITY_JA
from yosou.form_aptitude_top3.workflow import PROBABILITY as FORM_PROBABILITY_JA
from yosou.longshots_in_top3.dataset.column_names import LONGSHOT_ZONE as LONGSHOT_ZONE_JA
from yosou.longshots_in_top3.workflow import PROBABILITY as LONGSHOT_PROBABILITY_JA
from yosou.shared.dataset import column_names as ja
from yosou.upset_level.dataset import BetType
from yosou.upset_level.workflow import BET as BET_JA
from yosou.upset_level.workflow import UPSET_OR_MORE as UPSET_OR_MORE_JA

#: 1頭ごとの表（runners）の列。
RACE_ID = "race_id"
RACE_DATE = "race_date"
HORSE_NO = "horse_no"
FINISH = "finish"
WIN_ODDS = "win_odds"
POPULARITY = "popularity"
WIN_PAYOUT = "win_payout"
PLACE_PAYOUT = "place_payout"
FORM_PROB = "form_prob"          # 近走と適性モデルの「3着以内に入る確率」
DANGER_PROB = "danger_prob"      # 危険な人気馬モデルの「4着以下になる確率」（人気馬だけ。ほかは欠損）
LONGSHOT_PROB = "longshot_prob"  # 穴馬モデルの「3着以内に入る確率」（穴馬だけ。ほかは欠損）
LONGSHOT_ZONE = "longshot_zone"  # 穴馬の区分（中穴・大穴。穴馬だけ）
PLACE_ODDS = "place_odds"        # 複勝の確定オッズの下限（倍。無ければ欠損）

#: 1レースごとの表（races）の列（runners と同じ名前の列は同じ意味）。
VENUE_CODE = "venue_code"
RACE_NO = "race_no"
SURFACE = "surface"
DISTANCE_M = "distance_m"
CLASS_ORDER = "class_order"
GRADE_CODE = "grade_code"
FIELD_SIZE = "field_size"
IS_GRADED = "is_graded"          # 重賞か（グレードコード A〜D）
WEEK = "week"                    # 開催週の鍵（その週の土曜日）
FAVORITE_NO = "favorite_no"      # 本命（近走と適性モデルの確率が最大の馬。同点は人気上位）の馬番
FAVORITE_PROB = "favorite_prob"  # 本命の「3着以内に入る確率」
FAVORITE_DANGER = "favorite_danger"  # 本命の「4着以下になる確率」（本命が人気馬でなければ欠損）


def upset_column(bet: BetType) -> str:
    """その券種の「中荒れ以上の確率」の列の名前（例 ``upset_trio``）。"""
    return f"upset_{bet.key}"


#: 予測ファイルの列 → runners の列（近走と適性モデルの CSV から取る、全頭にある列）。
RUNNER_BASE_COLUMNS: dict[str, str] = {
    ja.RACE_ID: RACE_ID, ja.RACE_DATE: RACE_DATE, ja.HORSE_NO: HORSE_NO, ja.FINISH: FINISH,
    ja.WIN_ODDS: WIN_ODDS, ja.POPULARITY: POPULARITY, ja.WIN_PAYOUT: WIN_PAYOUT, ja.PLACE_PAYOUT: PLACE_PAYOUT,
}
#: 予測ファイルの確率などの列（日本語）。
FORM_PROBABILITY_JA = FORM_PROBABILITY_JA
DANGER_PROBABILITY_JA = DANGER_PROBABILITY_JA
LONGSHOT_PROBABILITY_JA = LONGSHOT_PROBABILITY_JA
LONGSHOT_ZONE_JA = LONGSHOT_ZONE_JA
BET_JA = BET_JA
UPSET_OR_MORE_JA = UPSET_OR_MORE_JA
RACE_ID_JA = ja.RACE_ID
HORSE_NO_JA = ja.HORSE_NO
