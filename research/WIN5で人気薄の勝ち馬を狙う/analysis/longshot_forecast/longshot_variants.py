"""比べる作り方の一覧（docs/03 の 1.2）。"""

from __future__ import annotations

from .longshot_variant import CURRENT_BASELINE, LongshotVariant

#: おすすめ（10番人気以下の行・二値分類）と、比べる2つ（6番人気以下の行・並べ替え）。
VARIANTS: tuple[LongshotVariant, ...] = (
    LongshotVariant("longshot10", "10番人気以下で学ぶ（おすすめ）", 10),
    LongshotVariant("longshot6", "6番人気以下で学ぶ", 6),
    LongshotVariant("rank10", "人気薄が勝ったレースだけで並べ替えを学ぶ", 10, ranker=True),
    LongshotVariant("longshot10_plain", "10番人気以下で学ぶ（重みなし）", 10, weighted=False),
    LongshotVariant("stack10", "10番人気以下で学ぶ（出発点は今のモデル）", 10, baseline=CURRENT_BASELINE, weighted=False),
)


def variant_named(key: str) -> LongshotVariant:
    for variant in VARIANTS:
        if variant.key == key:
            return variant
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(variant.key for variant in VARIANTS)}）")
