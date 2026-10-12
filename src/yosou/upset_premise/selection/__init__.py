"""第1段 レース選び: 1レースの「荒れる」点数を作る（設計書 04 の 2・15 の 1・8）。

| 名前 | 仕事 |
|---|---|
| ``BigPayoutChance`` | 予想が見た 1,000倍以上になる確率。今の予想の1着の確率から Harville の式で全部の3連単の組の確率を出し、オッズが 1,000倍以上の組の確率を合計する |
| ``RaceSelectionScore`` | レースを選ぶ点数。荒れ具合の予想の3連単が 1,000倍以上になる確率（大荒れ＋超荒れ）と、予想が見た確率の平均 |

どちらもモデルを持たない（荒れ具合の予想と今の予想の出力から計算するだけ）。道具「帯狙い」が、開催日のレースごとに点数を出し、線以上のレースを選ぶ。
"""

from .big_payout_chance import BigPayoutChance
from .race_selection_score import RaceSelectionScore

__all__ = ["BigPayoutChance", "RaceSelectionScore"]
