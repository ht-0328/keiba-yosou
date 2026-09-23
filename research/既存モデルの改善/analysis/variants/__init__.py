"""比べるモデルの作り方（現行・オッズだけ・変更版 など）。

同じ学習データ（全期間の表）から、使う特徴量の列・基準を使うか・学習データを分けるか を変えて、
「現行の作り方」「オッズだけの基準」「計画どおりに直した作り方」を同じ期間・同じ時点で比べる（既存モデルの修正計画の 3）。
現行の作り方は、直す前の特徴量の列だけを使い、基準を使わず、分けずに学ぶ（直す前のコードと同じ学び方）。

| 名前 | 仕事 |
|---|---|
| ``ModelVariant`` | 1つの作り方（名前・使う列・基準を使うか・分ける列） |
| ``VARIANTS`` | 予想ごとの作り方の並び。``variants_of`` で予想の名前から引く |
"""

from .model_variant import ModelVariant, WHOLE
from .variant_catalog import VARIANTS, variant_named, variants_of

__all__ = ["ModelVariant", "WHOLE", "VARIANTS", "variants_of", "variant_named"]
