"""買い目の決まり。確率の付いた組の表から、買う組を選ぶ。

| 名前 | 仕事 |
|---|---|
| ``HighPayoutRule`` | オッズが高配当の線以上・上限未満で、期待値（確率 × オッズ）が線以上の組を選ぶ。1レースの点数の上限も付けられる |

帯（高配当の線・上限）と期待値の線の既定は ``dataset`` の ``DEFAULT_BANDS``・``DEFAULT_VALUE_LINE``。金額の決め方は持たない
（買い目に金額を付けるのは、この予想を使う道具の側）。
"""

from .high_payout_rule import HighPayoutRule

__all__ = ["HighPayoutRule"]
