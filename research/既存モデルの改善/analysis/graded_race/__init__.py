"""重賞に特化して3着以内と1着を予想する（設計書「重賞に特化して3着以内と1着を予想」）の、7つの区切りでの確かめの部品。

| 名前 | 仕事 |
|---|---|
| ``GradedMaterialReader`` | まとまり W（重賞の格と実績。14個）を、元DB の事実表から1本の SQL で読む |
| ``W_FEATURES``・``W_NAMES``・``IS_GRADED`` | W の一覧と、重賞かどうかの列の名前 |
| ``DayBiasReader`` | まとまり D（その日の馬場の傾向。5つ）を、元DB の事実表から1本の SQL で読む |
| ``D_FEATURES``・``D_NAMES`` | D の一覧 |
| ``GradedTableBuilder`` | 手本の学習データに W と K（その重賞の傾向）を足す |
| ``GradedVariant`` | 重賞の行に重みを付けて学ぶ作り方1つ（目的変数も持つ） |
| ``GRADED_VARIANTS`` | 並べる作り方（この予想・手本・重み 1/10・K を外す・W を外す・オッズだけ・その日の馬場を足す） |
| ``DAY_BEFORE_VARIANTS`` | 今の本番の前日の作り（2015〜2019年の区切りまで延ばして、買い目の形をまだ見ていない年で確かめる） |
"""

from .day_bias_features import D_FEATURES, D_NAMES
from .day_bias_reader import DayBiasReader
from .graded_features import IS_GRADED, W_FEATURES, W_NAMES
from .graded_material_reader import GradedMaterialReader
from .graded_table_builder import K_NAMES, GradedTableBuilder
from .graded_variant import GradedVariant
from .graded_variants import DAY_BEFORE_VARIANTS, GRADED_VARIANTS, PREDICTION_TABLE, TOP3_TABLE, WIN_TABLE, graded_variant_keyed

__all__ = ["IS_GRADED", "W_FEATURES", "W_NAMES", "K_NAMES", "D_FEATURES", "D_NAMES", "GradedMaterialReader", "DayBiasReader",
           "GradedTableBuilder", "GradedVariant", "GRADED_VARIANTS", "DAY_BEFORE_VARIANTS", "PREDICTION_TABLE", "TOP3_TABLE", "WIN_TABLE",
           "graded_variant_keyed"]
