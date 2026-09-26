"""この予想の目的変数と評価用の列の名前（設計書 10）。"""

from __future__ import annotations

#: ① 先頭（1/0）。
LEADER = "先頭"
#: ② 序盤の位置の区分（先団 0・中団 1・後方 2）。
EARLY_ZONE = "序盤の位置の区分"
#: ④ 4コーナーの位置（0〜1）。
CORNER4_POSITION = "4コーナーの位置"
#: ⑤ 上がりの速さ（0〜1）。
CLOSING_SPEED = "上がりの速さ"
#: ⑦ 1着（1/0）。
WINNER = "1着"
#: ③ ペースの区分（スロー 0・平均 1・ハイ 2）。
PACE_CLASS = "ペースの区分"
#: ③ 前半タイムの基準との差（秒）。
FIRST_HALF_DIFF = "前半タイムの基準との差"
#: ⑥ 後半タイムの基準との差（秒）。
SECOND_HALF_DIFF = "後半タイムの基準との差"

#: 評価用の列。
EARLY_POSITION = "序盤の位置"
FINISH = "確定着順"
FIRST_HALF_TIME = "前半タイム"
SECOND_HALF_TIME = "後半タイム"

#: 3区分のクラスの並び（②③）。
THREE_CLASSES: tuple[int, ...] = (0, 1, 2)
#: 3区分の名前。クラスの番号の順。
EARLY_ZONE_NAMES: tuple[str, ...] = ("先団", "中団", "後方")
PACE_CLASS_NAMES: tuple[str, ...] = ("スロー", "平均", "ハイ")
