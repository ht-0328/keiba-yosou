"""展開の予想の結果（まとまり P）の、元の予測の列の名前と、特徴量の名前。"""

from __future__ import annotations

#: 元の予測の表を突き合わせる鍵（木曜は馬番が無いので、馬で突き合わせる）。
KEY: list[str] = ["race_id", "horse_id"]

#: 元の予測の列（予想「展開から着順を予想」の前半・後半の組の予測の列と同じ名前）。1頭ごとの列と、1レースごとの列
#: （同じレースの馬には同じ値を配ったもの）。
LEADER, FRONT, MIDDLE, BACK = "p_leader", "p_front", "p_middle", "p_back"
SLOW, HIGH = "p_slow", "p_high"
FIRST_LOW, FIRST_MIDDLE, FIRST_HIGH = "first_q10", "first_q50", "first_q90"
CORNER4, CLOSING = "corner4_pred", "closing_pred"
SECOND_MIDDLE = "second_q50"
#: 元の予測の表に要る列の並び（鍵を除く）。
SOURCE_COLUMNS: tuple[str, ...] = (
    LEADER, FRONT, MIDDLE, BACK, SLOW, HIGH, FIRST_LOW, FIRST_MIDDLE, FIRST_HIGH, CORNER4, CLOSING, SECOND_MIDDLE,
)

#: 特徴量の名前の頭（馬の力の材料の「先頭率」など、過去走から数えた列と取り違えないように付ける）。
_HEAD = "展開の予想_"
LEADER_P = f"{_HEAD}先頭の確率"
LEADER_RANK = f"{_HEAD}先頭の確率のレース内順位"
LEADER_GAP = f"{_HEAD}先頭の確率の1位との差"
FRONT_P = f"{_HEAD}先団の確率"
MIDDLE_P = f"{_HEAD}中団の確率"
BACK_P = f"{_HEAD}後方の確率"
FRONT_RANK = f"{_HEAD}先団の確率のレース内順位"
CORNER4_P = f"{_HEAD}4コーナーの位置"
CORNER4_RANK = f"{_HEAD}4コーナーの位置のレース内順位"
CORNER4_Z = f"{_HEAD}4コーナーの位置のレース内偏差"
CLOSING_P = f"{_HEAD}上がりの速さ"
CLOSING_RANK = f"{_HEAD}上がりの速さのレース内順位"
CLOSING_Z = f"{_HEAD}上がりの速さのレース内偏差"
COMBINED = f"{_HEAD}位置と上がりの和"
COMBINED_RANK = f"{_HEAD}位置と上がりの和のレース内順位"
HIGH_P = f"{_HEAD}ハイペースの確率"
SLOW_P = f"{_HEAD}スローペースの確率"
FIRST_DIFF = f"{_HEAD}前半タイムの基準との差"
FIRST_WIDTH = f"{_HEAD}前半タイムの予測の幅"
SECOND_DIFF = f"{_HEAD}後半タイムの基準との差"

#: まとまり P の列の並び（20個。どれも小数）。
PACE_FORECAST_NAMES: tuple[str, ...] = (
    LEADER_P, LEADER_RANK, LEADER_GAP, FRONT_P, MIDDLE_P, BACK_P, FRONT_RANK,
    CORNER4_P, CORNER4_RANK, CORNER4_Z, CLOSING_P, CLOSING_RANK, CLOSING_Z, COMBINED, COMBINED_RANK,
    HIGH_P, SLOW_P, FIRST_DIFF, FIRST_WIDTH, SECOND_DIFF,
)
