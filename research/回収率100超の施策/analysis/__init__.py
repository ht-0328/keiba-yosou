"""研究「回収率100超の施策」の部品（入口は ``pool_baseline_check.py``・``finish_check.py``）。

施策 1-B（1着のモデルの出発点を3連単から見た勝率に替える）と施策3（勝ち切る材料を1着のモデルに足す）の部品。
学習データの表・7つの区切り・区切りごとの学習・比べ方は研究「既存モデルの改善」のものをそのまま使う。

| 名前 | 仕事 |
|---|---|
| ``FINISH_NAMES``・``FINISH_FEATURES`` | 勝ち切る材料の列の名前と特徴量の一覧（まとまり Q。予想のパッケージの ``FINISH_POWER_NAMES`` と同じ） |
| ``FinishTableBuilder`` | 元の表に勝ち切る材料を足す（材料は予想のパッケージの ``FinishRecordsLoader`` で読む。採用して移したので、研究に SQL は持たない） |
| ``FinishTable``・``FINISH_TABLES`` | 勝ち切る材料を足す元の表と、足した表の名前（前日・当日） |
| ``FinishVariantSpec``・``FINISH_VARIANTS`` | 時点ごとの1着のモデルの作り方と、比べる相手（今の1着のモデル） |
| ``TrifectaWinBaseline`` | 1着のモデルの出発点を「3連単から見た勝率」のロジットに替える |
| ``POOL_VARIANT``・``POOL_CURRENT`` | 施策 1-B の作り方と、比べる相手 |
"""

from .finish_columns import FINISH_FEATURES, FINISH_NAMES
from .finish_table_builder import FinishTableBuilder
from .finish_tables import FINISH_TABLES, FinishTable, finish_table_named
from .finish_variants import FINISH_VARIANTS, FinishVariantSpec, spec_keyed
from .trifecta_win_baseline import POOL_CURRENT, POOL_TABLE, POOL_VARIANT, TrifectaWinBaseline

__all__ = [
    "FINISH_NAMES", "FINISH_FEATURES", "FinishTableBuilder",
    "FinishTable", "FINISH_TABLES", "finish_table_named", "FinishVariantSpec", "FINISH_VARIANTS", "spec_keyed",
    "TrifectaWinBaseline", "POOL_VARIANT", "POOL_CURRENT", "POOL_TABLE",
]
