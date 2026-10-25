"""レースの目安の等級（S・A・B・C。設計書「買うレースと買い目を決める」の 03 の 5）。

今週の予想は、レースごとに ◎ランク（◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数。高いほど ◎ の単勝・複勝のべた買いの的中率と回収率が高い）と
配当率（配当が中荒れ以上になる確率。荒れ具合の予想の4券種の平均）を出し、どちらも S・A・B・C の等級にする。
ここには、その線と等級の決め方だけを置く（確率や点数そのものは、今週の予想と印の成績が出す）。

| 名前 | 仕事 |
|---|---|
| ``GradeScale`` | 0〜1 の確率を等級にする（配当率）。``legend()`` は線の説明の文 |
| ``TopRankScale`` | ◎ の点数を ◎ランクにする。``score()`` で点数を出す |
| ``GRADES`` | 等級の並び（S・A・B・C） |
| ``LOWER_LINES``・``RANK_LINES`` | 等級ごとの下の線（確率 0.75・0.50・0.25・0 と、点数 0.35・0.15・0・−∞） |
"""

from .grade_scale import GRADES, LOWER_LINES, GradeScale
from .top_rank_scale import RANK_LINES, TopRankScale

__all__ = ["GradeScale", "GRADES", "LOWER_LINES", "TopRankScale", "RANK_LINES"]
