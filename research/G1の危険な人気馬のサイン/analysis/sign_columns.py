"""サインの材料とサインの列の名前（学習データの特徴量の列名にもなる）。"""

from __future__ import annotations

# 1. 距離適性
BEST_PLACED_DISTANCE_GAP = "今回の距離 − 3着以内に来た最長距離"
# 2. 馬場・枠の不利
MEETING_GATE_EDGE = "開催の先の日の、自分の枠の側の有利さ"
COURSE_GATE_EDGE = "コースの過去の、自分の枠の帯の有利さ"
# 3. G1の格
G1_RUNS = "G1の出走数"
G1_PLACES = "G1の3着以内の数"
G1_BEST_FINISH = "G1の最高着順"
GRADED_WINS = "G2・G3の勝利数"
GRADED_PLACES = "重賞の3着以内の数"
# 4. 重度のリピーター
SAME_STAKES_RUNS = "同じ重賞への出走数"
SAME_STAKES_PLACES = "同じ重賞での3着以内の数"
# 5. 惜しい競馬
LAST5_NEAR_MISSES = "近5走の2〜5着の数"
LAST5_WINS = "近5走の1着の数"
RUNS_SINCE_WIN = "最後の勝ちから走った数"
# 6. そもそも強くない
WINS = "勝利数"
# 7. 普通に考えたら来るわけない
PREV_CLASS_ORDER = "前走のクラスの並び"
DISTANCE_STEP_UP = "前走からの距離の延長"
FILLY_AGAINST_COLTS = "3歳牝馬の牡馬との混合戦"
# 8. 急激にオワコン
PREV2_FINISH = "前々走の着順"
# 10. 断然人気がいる時の2・3番人気
TOP_FAVORITE_ODDS = "1番人気の単勝オッズ"

#: サイン（0 か 1）の列。番号は、研究の README に並べた10のパターンの番号。
SIGN_COLUMNS: tuple[str, ...] = (
    "サイン1 距離適性の外",
    "サイン2 馬場・枠の不利",
    "サイン3 G1の格がない",
    "サイン4 重度のリピーター",
    "サイン5 惜しい競馬を繰り返す",
    "サイン6 そもそも強くない",
    "サイン7 普通は来ない条件",
    "サイン8 急に走らなくなった",
    "サイン9 人気薄の激走のあと",
    "サイン10 断然人気の陰の2・3番人気",
)
SIGN_COUNT = "サインの数"

#: サインの材料の数値の列（サインの列と数のほかに、モデルに渡すもの）。
MATERIAL_COLUMNS: tuple[str, ...] = (
    BEST_PLACED_DISTANCE_GAP, MEETING_GATE_EDGE, COURSE_GATE_EDGE, G1_RUNS, G1_PLACES, G1_BEST_FINISH, GRADED_WINS,
    GRADED_PLACES, SAME_STAKES_RUNS, SAME_STAKES_PLACES, LAST5_NEAR_MISSES, LAST5_WINS, RUNS_SINCE_WIN, WINS,
    PREV_CLASS_ORDER, DISTANCE_STEP_UP, FILLY_AGAINST_COLTS, PREV2_FINISH, TOP_FAVORITE_ODDS,
)
