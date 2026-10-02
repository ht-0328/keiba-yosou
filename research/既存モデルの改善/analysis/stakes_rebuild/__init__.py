"""重賞の予想を手本の新しい材料で作り直したあとの確かめ（重賞の設計書 15 の 9）。

作り直した専用モデル（重賞だけで学ぶ）を、オッズだけと「手本を重賞だけに使ったとき」（全レースで学び、重賞の行だけで測る）と、
1年ずつの7つの区切りで時点ごとに比べる。学習データは予想のパッケージの組み立て関数で作り、区切り・区切りごとの学習は
この研究のもの（``windows/``・``walk_forward/``）。

| 名前 | 仕事 |
|---|---|
| ``REBUILD_TABLES``・``rebuild_table_named`` | 4つの学習データの表（重賞だけ × 2、全レース × 2。どれも 2012年から） |
| ``REBUILD_VARIANTS``・``REBUILD_COMPARISONS`` | 比べる作り方と、時点ごとの比べ方 |
| ``StakesRowFilter`` | 全レースで学んだ手本の予測から、重賞の行だけを取り出す |
| ``AdoptionRule`` | 採用の基準（7つのうち 5つ以上の区切りで小さく、全期間でも小さい）を、2つの比べ先に当てる |
| ``StakesRebuildComparison`` | 時点ごとの比べ方の表（区切りごとのログ損失・採否・合わせた当たり具合・◎と1番人気） |
"""

from .adoption_rule import MIN_BETTER_WINDOWS, AdoptionRule, Verdict
from .rebuild_comparison import StakesRebuildComparison
from .rebuild_tables import (
    FORM_ABILITY,
    FORM_RACE_DAY,
    REBUILD_TABLES,
    STAKES_ABILITY,
    STAKES_RACE_DAY,
    rebuild_table_named,
)
from .rebuild_variants import REBUILD_COMPARISONS, REBUILD_VARIANTS, RebuildComparisonSpec, rebuild_variant_keyed
from .stakes_row_filter import StakesRowFilter

__all__ = [
    "REBUILD_TABLES", "rebuild_table_named", "STAKES_ABILITY", "STAKES_RACE_DAY", "FORM_ABILITY", "FORM_RACE_DAY",
    "REBUILD_VARIANTS", "REBUILD_COMPARISONS", "RebuildComparisonSpec", "rebuild_variant_keyed",
    "StakesRowFilter", "AdoptionRule", "Verdict", "MIN_BETTER_WINDOWS", "StakesRebuildComparison",
]
