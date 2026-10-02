"""券種ごとの確定オッズと払戻を、レースごとに引ける形にする。

元DB から読むのは、研究「馬券の買い方の検証」のリポジトリ（``FinalOddsRepository``・``PayoutRepository``。
1 SQL = 1クラス）をそのまま使う。ここには、読んだ表を組み合わせの馬番（整数）に直して、レースごとに引ける
帳簿にする部品を置く。

| 名前 | 仕事 |
|---|---|
| ``CombinationTable`` | 1つの券種の、レースごとの組み合わせ（馬番の並び）と確定オッズ（最低・最高） |
| ``CombinationTableReader`` | 元DB から、期間の全レースぶんの ``CombinationTable`` を読む |
"""

from .combination_table import CombinationTable, RaceCombinations
from .combination_table_reader import CombinationTableReader

__all__ = ["CombinationTable", "RaceCombinations", "CombinationTableReader"]
