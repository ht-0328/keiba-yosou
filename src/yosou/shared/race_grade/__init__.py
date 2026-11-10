"""レースの目安の等級（S・A・B・C。設計書「買うレースと買い目を決める」の 03 の 5 と 11）。

今週の予想（中央）は、レースごとに ◎ランク（◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数。高いほど ◎ の単勝・複勝のべた買いの的中率と回収率が高い）と
配当率（配当が中荒れ以上になる確率。荒れ具合の予想の4券種の平均）を出し、どちらも S・A・B・C の等級にする。
地方の発走前の通知は、1つの目安「期待度」（◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1）の点数）だけを S・A・B・C にする。
ここには、その線と等級の決め方だけを置く（確率や点数そのものは、今週の予想・発走前の通知・印の成績が出す）。

| 名前 | 仕事 |
|---|---|
| ``GradeScale`` | 0〜1 の確率を等級にする（配当率）。``legend()`` は線の説明の文 |
| ``TopRankScale`` | ◎ の点数を ◎ランクにする（中央）。``score()`` で点数を出す |
| ``LocalExpectationScale`` | ◎ の点数を期待度にする（地方）。``score()`` で点数を出す |
| ``GRADES`` | 等級の並び（S・A・B・C） |
| ``LOWER_LINES``・``RANK_LINES``・``EXPECTATION_LINES`` | 等級ごとの下の線（確率 0.75・0.50・0.25・0、◎ランクの点数 0.35・0.15・0・−∞、期待度の点数 0.45・0.15・−0.10・−∞） |
"""

from .grade_scale import GRADES, LOWER_LINES, GradeScale
from .local_expectation_scale import EXPECTATION_LABEL, EXPECTATION_LINES, EXPECTATION_MEANING, VALUE_WEIGHT, LocalExpectationScale
from .top_rank_scale import RANK_LINES, TopRankScale

__all__ = [
    "GradeScale", "GRADES", "LOWER_LINES", "TopRankScale", "RANK_LINES",
    "LocalExpectationScale", "EXPECTATION_LABEL", "EXPECTATION_LINES", "EXPECTATION_MEANING", "VALUE_WEIGHT",
]
