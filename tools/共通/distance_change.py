"""距離の変更（前走からの距離短縮・距離延長）の名前・幅の区切りと、コース・重賞ごとの傾向の数え上げ。

距離の変更は、同じ馬が1つ前に出走したレース（前走。芝ダや障害を問わない）の距離と、今回の距離を比べたもの。
事実表の ``distance_change``（延長・短縮・同じ・前走なし）と同じ決め方である。

- 名前と幅の区切りは、基礎統計のページ（``tools/成績集計/``）・重賞攻略（``tools/重賞攻略/``）・予想モデルの特徴量で同じものを使う。
- 「好走」は、穴馬（``trend_items.LONGSHOT_MIN_POPULARITY`` 番人気以下）が3着以内に入ること。
"""

from __future__ import annotations

from .trend_items import LONGSHOT_MIN_POPULARITY

SHORTER, SAME, LONGER, NO_PREVIOUS = "短縮", "同じ", "延長", "前走なし"
#: 距離の変更の並び（表の行の順）。
CHANGE_ORDER: tuple[str, ...] = (SHORTER, SAME, LONGER, NO_PREVIOUS)
#: 幅で分けるときの境目（m）。これ以上の差を「大きい」とする。
LARGE_GAP_M = 400
#: 幅の名前（短い順。差 = 今回 − 前走）。
GAP_NAMES: tuple[str, ...] = (
    f"{SHORTER} {LARGE_GAP_M}m以上", f"{SHORTER} {LARGE_GAP_M}m未満", SAME,
    f"{LONGER} {LARGE_GAP_M}m未満", f"{LONGER} {LARGE_GAP_M}m以上",
)

__all__ = ["CHANGE_ORDER", "GAP_NAMES", "LARGE_GAP_M", "LONGER", "LONGSHOT_MIN_POPULARITY", "NO_PREVIOUS", "SAME", "SHORTER"]
