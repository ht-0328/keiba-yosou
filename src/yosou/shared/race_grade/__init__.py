"""レースの目安の等級（S・A・B・C。設計書「買うレースと買い目を決める」の 03 の 5 と 11）。

今週の予想（中央）は、レースごとに期待度（◎ の単勝の期待値 0.90 未満は見送り、それ以外は ◎ の1着の確率 ＋ 1.25 ×（単勝の期待値 − 1）の点数の S・A・B・C）と
配当率（配当が中荒れ以上になる確率。荒れ具合の予想の4券種の平均。人には見せない）を出す。
地方の発走前の通知は、1つの目安「期待度」（そのレースの推奨買目の（期待値 − 1）の合計）だけを S・A・B・C にする。
道具「印の成績」の表13 の地方の分け方は ◎ の点数（◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1））。
ここには、その線と等級の決め方だけを置く（確率や点数そのものは、今週の予想・発走前の通知・印の成績が出す）。

| 名前 | 仕事 |
|---|---|
| ``GradeScale`` | 0〜1 の確率を等級にする（配当率）。``legend()`` は線の説明の文 |
| ``TopRankScale`` | ◎ の確率と期待値を中央の期待度（S・A・B・C か見送り）にする。``score()`` で点数、``grade()`` で等級を出す |
| ``LocalExpectationScale`` | 推奨買目の期待値の並びを期待度にする（地方）。``score()`` で点数、``grade()`` で等級を出す |
| ``LocalTopScoreScale`` | ◎ の点数を等級にする（地方。印の成績の表13）。``score()`` で点数、``grade()`` で等級を出す |
| ``GRADES`` | 等級の並び（S・A・B・C） |
| ``LOWER_LINES``・``RANK_LINES``・``EXPECTATION_LINES``・``TOP_SCORE_LINES`` | 等級ごとの下の線（確率 0.75・0.50・0.25・0、中央の期待度の点数 0.28・0.14・0.02・−∞、地方の期待度の点数 3.2・1.4・0.5・−∞、地方の ◎ の点数 0.45・0.15・−0.10・−∞） |
"""

from .grade_scale import GRADES, LOWER_LINES, GradeScale
from .local_expectation_scale import EXPECTATION_LABEL, EXPECTATION_LINES, EXPECTATION_MEANING, LocalExpectationScale
from .local_top_score_scale import TOP_SCORE_LABEL, TOP_SCORE_LINES, TOP_SCORE_MEANING, TOP_SCORE_WEIGHT, LocalTopScoreScale
from .top_rank_scale import RANK_LINES, RANK_VALUE_WEIGHT, SKIP_GRADE, SKIP_VALUE, TopRankScale

__all__ = [
    "GradeScale", "GRADES", "LOWER_LINES", "TopRankScale", "RANK_LINES", "RANK_VALUE_WEIGHT", "SKIP_GRADE", "SKIP_VALUE",
    "LocalExpectationScale", "EXPECTATION_LABEL", "EXPECTATION_LINES", "EXPECTATION_MEANING",
    "LocalTopScoreScale", "TOP_SCORE_LABEL", "TOP_SCORE_LINES", "TOP_SCORE_MEANING", "TOP_SCORE_WEIGHT",
]
