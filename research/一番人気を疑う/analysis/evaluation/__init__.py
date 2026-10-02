"""◎と1番人気を比べる部品。

| 名前 | 仕事 |
|---|---|
| ``TopPickTable`` | 予測の表から、レースごとに◎（確率がいちばん高い馬）と1番人気を横に並べた表を作る |
| ``TopPickSummary`` | ◎と1番人気の3着以内率、疑ったレースでの成績、区切りごとの勝ち負けをまとめる |
| ``DoubtBreakdown`` | 疑ったレースを条件ごとに分けて、どちらがよく来たかを出す |
| ``ConfidenceBands`` | ◎の確率の高さごとに、◎と同じレースの1番人気の3着以内率を出す |
"""

from .confidence_bands import ConfidenceBands
from .doubt_breakdown import DoubtBreakdown
from .top_pick_summary import TopPickSummary
from .top_pick_table import TopPickTable

__all__ = ["ConfidenceBands", "DoubtBreakdown", "TopPickSummary", "TopPickTable"]
