"""重賞の二段の予想（2案目。今の予想の確率を出発点にして、重賞の行だけで市場とのずれを直す）の部品。

| 名前 | 仕事 |
|---|---|
| ``StackTableBuilder`` | 重賞の行ごとに、1段目の確率（その年より前だけで学んだ予測）・確定オッズから見た確率・W・K・結果を並べる |
| ``StackFeatures`` | 2段目の材料の行列（1段目と市場の差・W・縮めた K・頭数）。出発点は1段目のロジット |
| ``OffsetLogit`` | 3着以内の2段目。出発点からのずらしだけを学ぶロジスティック回帰（L2 の罰） |
| ``ConditionalLogit`` | 1着の2段目。レースの全頭で合計 1 にする条件付きロジット（出発点つき・L2 の罰） |
| ``YearlyStackRunner`` | テストの年ごとに、その年より前の重賞だけで2段目を学んで予測する（罰の強さは前の年で選ぶ） |
"""

from .conditional_logit import ConditionalLogit
from .offset_logit import OffsetLogit
from .stack_features import StackFeatures
from .stack_table_builder import StackTableBuilder
from .yearly_stack_runner import PENALTIES, YearlyStackRunner

__all__ = ["ConditionalLogit", "OffsetLogit", "StackFeatures", "StackTableBuilder", "PENALTIES", "YearlyStackRunner"]
