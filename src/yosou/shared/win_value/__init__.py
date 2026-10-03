"""単勝を買う期待値と、レースの期待度（設計書「近走と適性から3着以内を予想」の 15 の 14・16 の 6）。

「勝ちやすさ」（1着になる確率）と「単勝を買う価値があるか」（期待値）は違う。ここでは、1着のモデルの確率に単勝オッズを掛けて
単勝の期待値（1 で元返し）を出し（``WinExpectedValue``）、レースごとに ◎（期待値がいちばん高い馬）の期待値を 高・低 の2段階にする
（``ExpectationLevel``。線は 1.00 で固定）。

| クラス | 仕事 |
|---|---|
| ``WinExpectedValue`` | 単勝の期待値 = 1着になる確率 × 単勝オッズ |
| ``WinValueColumns`` | 予測の結果に足す列（単勝の期待値）を作る。単勝オッズは予測用データの ``market`` から取る |
| ``ExpectationLevel`` | レースの期待度（高・低）を、◎ の単勝の期待値から決める |
"""

from .expectation_level import EXPECTATION_LEVELS, HIGH, LINE, LOW, ExpectationLevel
from .win_expected_value import WIN_VALUE, WinExpectedValue
from .win_value_columns import WinValueColumns

__all__ = ["WinExpectedValue", "WinValueColumns", "ExpectationLevel", "WIN_VALUE", "EXPECTATION_LEVELS", "HIGH", "LOW", "LINE"]
