"""10のサイン（当てはまれば 1）を、材料の列から決める。"""

from __future__ import annotations

import pandas as pd

from .sign_columns import (
    BEST_PLACED_DISTANCE_GAP,
    COURSE_GATE_EDGE,
    DISTANCE_STEP_UP,
    FILLY_AGAINST_COLTS,
    G1_PLACES,
    G1_RUNS,
    GRADED_PLACES,
    GRADED_WINS,
    LAST5_NEAR_MISSES,
    LAST5_WINS,
    MEETING_GATE_EDGE,
    PREV2_FINISH,
    PREV_CLASS_ORDER,
    SAME_STAKES_RUNS,
    SIGN_COLUMNS,
    SIGN_COUNT,
    TOP_FAVORITE_ODDS,
    WINS,
)

#: 線（結果を見る前に決めた値。docs/01-仮定と進め方.md の 2）。
DISTANCE_GAP_LINE = 400            # 3着以内に来た最長距離より 400m 以上長い
MEETING_EDGE_LINE = -0.10          # 開催の先の日に、自分の側の枠が 10ポイント以上来ていない
COURSE_EDGE_LINE = -0.05           # コースの過去に、自分の枠の帯が 5ポイント以上来ていない
REPEAT_LINE = 2                    # 同じ重賞に2回以上出ている（今回が3回目以上）
NEAR_MISS_LINE = 3                 # 近5走で 2〜5着が3回以上、1着なし
OPEN_CLASS_ORDER = 6               # クラスの並びのオープン（これより下は条件戦）
STEP_UP_LINE = 600                 # 前走から 600m 以上の延長
LONGSHOT_POPULARITY = 6            # 前走で 6番人気以下
STRONG_FAVORITE_ODDS = 2.0         # 1番人気の単勝オッズが 2.0倍以下


class DangerSigns:
    """材料の列（``HorseHistoryFeatures``・``GateBiasFeatures`` の出力と出走の列）から、10のサインと数を返す。

    ``frame`` に要る列: 材料の列（``sign_columns``）、``prev_finish``・``prev_popularity``・``popularity``。
    材料の無い行（初出走など）は、そのサインに当てはまらない（0）とする。
    """

    def compute(self, frame: pd.DataFrame) -> pd.DataFrame:
        signs = (
            frame[BEST_PLACED_DISTANCE_GAP].ge(DISTANCE_GAP_LINE),
            frame[MEETING_GATE_EDGE].le(MEETING_EDGE_LINE) | frame[COURSE_GATE_EDGE].le(COURSE_EDGE_LINE),
            frame[G1_RUNS].ge(1) & frame[G1_PLACES].eq(0) & frame[GRADED_WINS].ge(1),
            frame[SAME_STAKES_RUNS].ge(REPEAT_LINE),
            frame[LAST5_NEAR_MISSES].ge(NEAR_MISS_LINE) & frame[LAST5_WINS].eq(0),
            frame[GRADED_PLACES].eq(0) | frame[WINS].le(1),
            frame[PREV_CLASS_ORDER].lt(OPEN_CLASS_ORDER) | frame[FILLY_AGAINST_COLTS].eq(1)
            | frame[DISTANCE_STEP_UP].ge(STEP_UP_LINE),
            frame[G1_PLACES].ge(1) & frame["prev_finish"].ge(4) & frame[PREV2_FINISH].ge(4),
            frame["prev_popularity"].ge(LONGSHOT_POPULARITY) & frame["prev_finish"].le(3),
            frame[TOP_FAVORITE_ODDS].le(STRONG_FAVORITE_ODDS) & frame["popularity"].isin((2, 3)),
        )
        out = pd.DataFrame({name: sign.fillna(False).astype(int) for name, sign in zip(SIGN_COLUMNS, signs)}, index=frame.index)
        out[SIGN_COUNT] = out[list(SIGN_COLUMNS)].sum(axis=1)
        return out
