"""単勝を買う期待値と、◎ の単勝の期待値の帯（設計書「近走と適性から3着以内を予想」の 15 の 14・16 の 6）。

「勝ちやすさ」（1着になる確率）と「単勝を買う価値があるか」（期待値）は違う。ここでは、1着のモデルの確率に単勝オッズを掛けて
単勝の期待値（1 で元返し）を出し（``WinExpectedValue``）、レースごとに ◎（期待値がいちばん高い馬）の期待値が線（1.00。固定）以上か未満かを決める
（``WinValueBand``。買い方の決まりで「◎の期待値 1.00 以上のレース」と書く条件）。

| クラス | 仕事 |
|---|---|
| ``WinExpectedValue`` | 単勝の期待値 = 1着になる確率 × 単勝オッズ |
| ``WinValueColumns`` | 予測の結果に足す列（単勝の期待値）を作る。単勝オッズは予測用データの ``market`` から取る |
| ``WinValueBand`` | ◎ の単勝の期待値が線（1.00）以上か未満かを決める |
"""

from .win_expected_value import WIN_VALUE, WinExpectedValue
from .win_value_band import HIGH, LINE, LOW, WIN_VALUE_BANDS, WinValueBand
from .win_value_columns import WinValueColumns

__all__ = ["WinExpectedValue", "WinValueColumns", "WinValueBand", "WIN_VALUE", "WIN_VALUE_BANDS", "HIGH", "LOW", "LINE"]
